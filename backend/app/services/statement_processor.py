"""
Statement processor service for extracting assets and transactions from uploaded statements
"""
from sqlalchemy.orm import Session
from app.models.statement import Statement, StatementStatus, StatementType
from app.models.asset import Asset, AssetType
from app.models.transaction import Transaction, TransactionType
from app.models.demat_account import DematAccount
from app.models.crypto_account import CryptoAccount
from app.models.portfolio_snapshot import AssetSnapshot
from app.models.alert import Alert
from app.models.mutual_fund_holding import MutualFundHolding
from datetime import datetime
import PyPDF2
import pandas as pd
import re
import hashlib
import logging
from typing import List, Dict, Any, Optional
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

# Import US broker parsers
from app.services.vested_parser import VestedParser
from app.services.indmoney_parser import INDMoneyParser
from app.services.currency_converter import convert_usd_to_inr, get_usd_to_inr_rate
from app.services.isin_lookup import lookup_isin_for_asset
from app.api.dependencies import get_default_portfolio_id

logger = logging.getLogger(__name__)

# Canonical broker display-name -> master-table key mapping
BROKER_MAPPING = {
    'zerodha': 'zerodha',
    'groww': 'groww',
    'upstox': 'upstox',
    'angel one': 'angel_one',
    'angel': 'angel_one',
    'icici direct': 'icici_direct',
    'icici': 'icici_direct',
    'hdfc securities': 'hdfc_securities',
    'hdfc': 'hdfc_securities',
    'kotak securities': 'kotak_securities',
    'kotak': 'kotak_securities',
    'axis direct': 'axis_direct',
    'axis': 'axis_direct',
    'sharekhan': 'sharekhan',
    'motilal oswal': 'motilal_oswal',
    'iifl securities': 'iifl_securities',
    'iifl': 'iifl_securities',
    'indmoney': 'indmoney',
    'vested': 'vested',
    'mf_central': 'mf_central',
    'mf central': 'mf_central',
    'nsdl cas': 'nsdl_cas',
    'nsdl_cas': 'nsdl_cas',
    'cdsl cas': 'cdsl_cas',
    'cdsl_cas': 'cdsl_cas',
    'direct mf': 'direct_mf',
    'direct_mf': 'direct_mf',
}

# Asset types that belong in demat accounts
DEMAT_ASSET_TYPES = {AssetType.STOCK, AssetType.US_STOCK, AssetType.EQUITY_MUTUAL_FUND,
                     AssetType.DEBT_MUTUAL_FUND, AssetType.COMMODITY, AssetType.SOVEREIGN_GOLD_BOND}

# Asset types that belong in crypto accounts
CRYPTO_ASSET_TYPES = {AssetType.CRYPTO}


def get_or_create_demat_account(
    user_id: int,
    broker_name: str,
    account_id: str,
    account_holder_name: Optional[str],
    db: Session,
    cash_balance_usd: Optional[float] = None,
    portfolio_id: Optional[int] = None
) -> Optional[DematAccount]:
    """
    Get existing demat account or create a new one
    """
    from app.services.currency_converter import get_usd_to_inr_rate

    # Ensure portfolio_id is always resolved
    if not portfolio_id:
        portfolio_id = get_default_portfolio_id(user_id, db)

    broker_name_lower = broker_name.lower() if broker_name else ''
    broker_enum = BROKER_MAPPING.get(broker_name_lower, 'other')

    # Generate a placeholder account_id if not provided
    if not account_id:
        account_id = f"{broker_enum.upper()}-AUTO-{user_id}"
    
    # Check if demat account exists for this portfolio
    demat_account = db.query(DematAccount).filter(
        DematAccount.user_id == user_id,
        DematAccount.broker_name == broker_enum,
        DematAccount.account_id == account_id,
        DematAccount.portfolio_id == portfolio_id
    ).first()
    
    # Determine currency based on broker
    is_us_broker = broker_enum in ['vested', 'indmoney']
    currency = 'USD' if is_us_broker else 'INR'
    
    if not demat_account:
        # Create new demat account
        cash_balance = 0.0
        cash_balance_usd_val = None
        
        if is_us_broker and cash_balance_usd is not None:
            usd_to_inr = get_usd_to_inr_rate()
            cash_balance = cash_balance_usd * usd_to_inr
            cash_balance_usd_val = cash_balance_usd
        
        demat_account = DematAccount(
            user_id=user_id,
            broker_name=broker_enum,
            account_id=account_id,
            account_holder_name=account_holder_name,
            currency=currency,
            cash_balance=cash_balance,
            cash_balance_usd=cash_balance_usd_val,
            is_active=True,
            portfolio_id=portfolio_id,
        )
        db.add(demat_account)
        db.flush()  # Get the ID
    else:
        # Update last statement date and cash balance if provided
        demat_account.last_statement_date = datetime.utcnow()
        if account_holder_name and not demat_account.account_holder_name:
            demat_account.account_holder_name = account_holder_name

        # Assign portfolio if the account doesn't have one yet
        if portfolio_id and not demat_account.portfolio_id:
            demat_account.portfolio_id = portfolio_id

        # Ensure currency is correct for US brokers (may be wrong for old accounts)
        if is_us_broker and demat_account.currency != 'USD':
            demat_account.currency = 'USD'

        # Only update cash balance when the parser found a positive value.
        # If the parser returns 0.0 (either genuinely $0 or because it failed to
        # locate the cash row in the file), we preserve the previously stored balance
        # to avoid silently zeroing it out on every re-upload.
        if is_us_broker and cash_balance_usd is not None and cash_balance_usd > 0:
            usd_to_inr = get_usd_to_inr_rate()
            demat_account.cash_balance = cash_balance_usd * usd_to_inr
            demat_account.cash_balance_usd = cash_balance_usd
    
    return demat_account


def get_or_create_crypto_account(
    user_id: int,
    exchange_name: str,
    account_id: str,
    db: Session,
    portfolio_id: Optional[int] = None
) -> Optional[CryptoAccount]:
    """
    Get existing crypto account or create a new one.
    """
    if not exchange_name:
        exchange_name = 'unknown'
    exchange_lower = exchange_name.lower()

    if not account_id:
        account_id = f"{exchange_lower.upper()}-AUTO-{user_id}"

    # Check if crypto account exists
    crypto_account = db.query(CryptoAccount).filter(
        CryptoAccount.user_id == user_id,
        CryptoAccount.exchange_name == exchange_lower,
        CryptoAccount.account_id == account_id
    ).first()

    if not crypto_account:
        crypto_account = CryptoAccount(
            user_id=user_id,
            exchange_name=exchange_lower,
            account_id=account_id,
            is_active=True,
        )
        db.add(crypto_account)
        db.flush()

    return crypto_account


def _process_bank_statement_via_parser(statement: Statement, db: Session, portfolio_id: int = None) -> dict:
    """
    Process a bank statement using the dedicated bank statement parser.
    Creates Expense records from the parsed transactions.
    Auto-creates the bank account if it doesn't exist, using header info from the PDF.
    Returns a dict with: total_found, imported, duplicates.
    """
    from app.services.bank_statement_parser import get_parser
    from app.models.bank_account import BankAccount, BankType
    from app.models.expense import Expense
    from app.services.expense_categorizer import ExpenseCategorizer

    # Map institution_name to parser key
    bank_name_map = {
        'icici_bank': 'ICICI',
        'hdfc_bank': 'HDFC',
        'idfc_first_bank': 'IDFC_FIRST',
        'state_bank_of_india': 'SBI',
        'kotak_mahindra_bank': 'KOTAK',
        'axis_bank': 'AXIS',
    }

    institution = (statement.institution_name or '').lower().strip()
    parser_key = bank_name_map.get(institution)
    if not parser_key:
        raise Exception(
            f"Bank statement parsing is not yet supported for '{statement.institution_name}'. "
            f"Supported banks: ICICI, HDFC, IDFC First, SBI, Kotak, Axis."
        )

    parser = get_parser(parser_key, statement.file_path, password=statement.password)
    transactions = parser.parse()

    if not transactions:
        raise Exception(
            f"Statement was parsed but no transactions were found in this "
            f"{statement.institution_name} bank statement."
        )

    # Get account info extracted by the parser (if available)
    account_info = getattr(parser, 'account_info', {}) or {}
    acct_number = account_info.get('account_number', '')

    # Try to find existing bank account — match on account number first, then bank name
    bank_account = None
    if acct_number:
        bank_account = db.query(BankAccount).filter(
            BankAccount.user_id == statement.user_id,
            BankAccount.bank_name == institution,
            BankAccount.account_number == acct_number
        ).first()

    if not bank_account:
        # Fallback: match by bank name only (user may have created it manually)
        bank_account = db.query(BankAccount).filter(
            BankAccount.user_id == statement.user_id,
            BankAccount.bank_name == institution
        ).first()

    # Auto-create bank account if none exists
    if not bank_account:
        # Determine account type from parser info
        acct_type_str = account_info.get('account_type', 'savings')
        acct_type_map = {
            'savings': BankType.SAVINGS,
            'current': BankType.CURRENT,
        }
        acct_type = acct_type_map.get(acct_type_str, BankType.SAVINGS)

        # Mask account number for display (show last 4 digits)
        masked_number = acct_number
        if acct_number and len(acct_number) > 4:
            masked_number = 'X' * (len(acct_number) - 4) + acct_number[-4:]

        # Resolve portfolio for the new account
        if not portfolio_id:
            portfolio_id = get_default_portfolio_id(statement.user_id, db)

        opening_balance = getattr(parser, 'opening_balance', None) or 0.0

        bank_account = BankAccount(
            user_id=statement.user_id,
            bank_name=institution,
            account_type=acct_type,
            account_number=masked_number or f'{institution.upper()}_{statement.user_id}',
            account_holder_name=account_info.get('account_holder_name'),
            ifsc_code=account_info.get('ifsc_code'),
            current_balance=opening_balance,
            is_active=True,
            portfolio_id=portfolio_id,
        )
        db.add(bank_account)
        db.flush()
        logger.info(
            f"Auto-created {acct_type.value} bank account for {institution} "
            f"(account: {masked_number}) from statement upload"
        )

    # Resolve portfolio
    if not portfolio_id:
        portfolio_id = get_default_portfolio_id(statement.user_id, db)

    # Auto-categorize
    categorizer = ExpenseCategorizer(db, user_id=statement.user_id)
    transactions = categorizer.bulk_categorize(transactions)

    # Save transactions, skipping duplicates
    created_count = 0
    duplicate_count = 0
    last_error = None
    for txn in transactions:
        try:
            # Check for duplicates
            dup_query = db.query(Expense).filter(
                Expense.user_id == statement.user_id,
                Expense.bank_account_id == bank_account.id,
                Expense.transaction_date == txn['transaction_date'],
                Expense.amount == txn['amount'],
                Expense.description == txn['description']
            )
            if dup_query.first():
                duplicate_count += 1
                continue

            expense_portfolio_id = portfolio_id or bank_account.portfolio_id

            expense = Expense(
                user_id=statement.user_id,
                bank_account_id=bank_account.id,
                statement_id=statement.id,
                transaction_date=txn['transaction_date'],
                description=txn['description'],
                amount=txn['amount'],
                transaction_type=txn['transaction_type'],
                payment_method=txn.get('payment_method'),
                merchant_name=txn.get('merchant_name'),
                category_id=txn.get('category_id'),
                reference_number=txn.get('reference_number'),
                balance_after=txn.get('balance_after'),
                is_categorized=txn.get('category_id') is not None,
                is_reconciled=True,
                portfolio_id=expense_portfolio_id,
            )
            db.add(expense)
            created_count += 1
        except Exception as e:
            import traceback
            logger.error(
                f"Error saving bank transaction: {e}\n"
                f"Transaction data: {txn}\n"
                f"Traceback: {traceback.format_exc()}"
            )
            last_error = e
            continue

    db.flush()

    # If no transactions were created and none were duplicates, something went wrong
    if created_count == 0 and duplicate_count == 0 and transactions:
        error_msg = f"Failed to save any of the {len(transactions)} parsed transactions."
        if last_error:
            error_msg += f" Last error: {last_error}"
        raise Exception(error_msg)

    # Update bank account balance from the last transaction
    if transactions and transactions[-1].get('balance_after'):
        bank_account.current_balance = transactions[-1]['balance_after']
    bank_account.last_statement_date = datetime.utcnow()

    logger.info(
        f"Bank statement processed: {len(transactions)} parsed, "
        f"{created_count} imported, {duplicate_count} duplicates"
    )

    return {
        'total_found': len(transactions),
        'imported': created_count,
        'duplicates': duplicate_count,
    }


def process_statement(statement_id: int, db: Session, portfolio_id: int = None, expected_institution: str = None):
    """
    Main function to process an uploaded statement.
    If portfolio_id is provided, all created assets will be assigned to that portfolio.
    Otherwise, they will be assigned to the user's default portfolio.
    If expected_institution is provided, the extracted broker/institution from the
    parsed statement will be validated against it. A mismatch causes the statement
    to be marked as FAILED.
    """
    statement = db.query(Statement).filter(Statement.id == statement_id).first()
    if not statement:
        return

    # Resolve portfolio_id: use provided value or fall back to user's default
    if not portfolio_id:
        portfolio_id = get_default_portfolio_id(statement.user_id, db)
    
    statement.status = StatementStatus.PROCESSING
    statement.processing_started_at = datetime.utcnow()
    db.commit()
    
    try:
        # Handle bank statements via dedicated bank statement parser
        if statement.statement_type == StatementType.BANK_STATEMENT:
            result = _process_bank_statement_via_parser(statement, db, portfolio_id)
            statement.assets_found = 0
            statement.transactions_found = result['total_found']
            statement.status = StatementStatus.PROCESSED
            statement.processing_completed_at = datetime.utcnow()
            # Store import details for the endpoint to use
            if result['duplicates'] > 0:
                statement.error_message = (
                    f"{result['imported']} new, {result['duplicates']} duplicate(s) skipped"
                )
            db.commit()
            return

        # Check for US broker statements (Vested, INDMoney)
        cash_balance_usd = None
        if statement.statement_type == StatementType.VESTED_STATEMENT:
            assets, transactions, cash_balance_usd = process_vested_statement(statement)
        elif statement.statement_type == StatementType.INDMONEY_STATEMENT:
            assets, transactions, cash_balance_usd = process_indmoney_statement(statement)
        # Check if it's an NSDL CAS PDF (password-protected)
        elif 'pdf' in statement.file_type.lower() and statement.password:
            # PDF with password - likely NSDL CAS or similar
            assets, transactions = parse_nsdl_cas_pdf(statement.file_path, statement, statement.password)
        # Check for MF Central CAS PDF (non-password-protected)
        elif 'pdf' in statement.file_type.lower() and is_mf_central_cas_pdf(statement.file_path):
            assets, transactions = parse_mf_central_cas_pdf(statement.file_path, statement)
        else:
            # Extract data from file
            data = extract_text_from_file(statement.file_path, statement.file_type)
            
            assets = []
            transactions = []
            
            # Check if it's a CSV file with DataFrame
            if isinstance(data, pd.DataFrame):
                # Check for ICICI Direct formats
                if is_icici_direct_stock_format(data):
                    logger.info("Detected ICICI Direct Stock CSV format")
                    assets, transactions = parse_icici_direct_stock_csv(data, statement)
                elif is_icici_direct_mf_format(data):
                    logger.info("Detected ICICI Direct Mutual Fund CSV format")
                    assets, transactions = parse_icici_direct_mf_csv(data, statement)
                # Check if it's Groww MF format
                elif is_groww_mf_format(data):
                    logger.info("Detected Groww MF Holdings format")
                    assets, transactions = parse_groww_mf_holdings(data, statement)
                # Check if it's Groww stock format
                elif is_groww_format(data):
                    logger.info("Detected Groww Stock Holdings format")
                    assets, transactions = parse_groww_holdings(data, statement)
                # Check if it's Zerodha format
                elif is_zerodha_format(data, statement):
                    assets, transactions = parse_zerodha_holdings(data, statement, None, {})
                else:
                    # Try generic parsing
                    text = data.to_string()
                    if statement.statement_type in (StatementType.BANK_STATEMENT, StatementType.BROKER_STATEMENT):
                        assets, transactions = parse_financial_statement(text, statement)
                    elif statement.statement_type == StatementType.MUTUAL_FUND_STATEMENT:
                        assets, transactions = parse_mutual_fund_statement(text, statement)
                    else:
                        assets, transactions = parse_generic_statement(text, statement)
            # Check if it's a multi-sheet file
            elif isinstance(data, list):
                logger.info(f"Processing {len(data)} sheets")
                for item in data:
                    sheet_name, df, account_info = item
                    logger.info(f"Processing sheet: {sheet_name}")
                    if is_groww_mf_format(df, account_info):
                        logger.info(f"Detected Groww MF format in sheet '{sheet_name}'")
                        sheet_assets, sheet_transactions = parse_groww_mf_holdings(df, statement, account_info)
                        assets.extend(sheet_assets)
                        transactions.extend(sheet_transactions)
                    elif is_groww_format(df, account_info):
                        logger.info(f"Detected Groww format in sheet '{sheet_name}'")
                        sheet_assets, sheet_transactions = parse_groww_holdings(df, statement, account_info)
                        assets.extend(sheet_assets)
                        transactions.extend(sheet_transactions)
                    elif is_zerodha_format(df, statement):
                        sheet_assets, sheet_transactions = parse_zerodha_holdings(df, statement, sheet_name, account_info)
                        assets.extend(sheet_assets)
                        transactions.extend(sheet_transactions)
            # Check if it's a single DataFrame file with account info
            elif isinstance(data, tuple) and len(data) == 2:
                df, account_info = data
                if isinstance(df, pd.DataFrame):
                    # Check for ICICI Direct formats first
                    if is_icici_direct_stock_format(df):
                        logger.info("Detected ICICI Direct Stock CSV format")
                        assets, transactions = parse_icici_direct_stock_csv(df, statement, account_info)
                    elif is_icici_direct_mf_format(df):
                        logger.info("Detected ICICI Direct Mutual Fund CSV format")
                        assets, transactions = parse_icici_direct_mf_csv(df, statement, account_info)
                    elif is_groww_mf_format(df, account_info):
                        logger.info("Detected Groww MF Holdings format")
                        assets, transactions = parse_groww_mf_holdings(df, statement, account_info)
                    elif is_groww_format(df, account_info):
                        logger.info("Detected Groww Stock Holdings format")
                        assets, transactions = parse_groww_holdings(df, statement, account_info)
                    elif is_zerodha_format(df, statement):
                        assets, transactions = parse_zerodha_holdings(df, statement, None, account_info)
            # Parse based on statement type
            elif statement.statement_type in (StatementType.BANK_STATEMENT, StatementType.BROKER_STATEMENT):
                text = data if isinstance(data, str) else str(data)
                assets, transactions = parse_financial_statement(text, statement)
            elif statement.statement_type == StatementType.MUTUAL_FUND_STATEMENT:
                text = data if isinstance(data, str) else str(data)
                assets, transactions = parse_mutual_fund_statement(text, statement)
            else:
                text = data if isinstance(data, str) else str(data)
                assets, transactions = parse_generic_statement(text, statement)
        
        # Validate extracted institution against expected (if provided)
        if expected_institution and assets and len(assets) > 0:
            extracted_broker = assets[0].get('broker_name', '')
            if extracted_broker:
                # Normalize both names using the module-level BROKER_MAPPING
                normalized_expected = BROKER_MAPPING.get(expected_institution.lower(), expected_institution.lower())
                normalized_extracted = BROKER_MAPPING.get(extracted_broker.lower(), extracted_broker.lower())
                if normalized_expected != normalized_extracted:
                    statement.status = StatementStatus.FAILED
                    statement.error_message = (
                        f"Statement mismatch: this statement is from '{extracted_broker}', "
                        f"but was uploaded for '{expected_institution}'. "
                        f"Please use 'Add New Account' if this is a different account."
                    )
                    statement.processing_completed_at = datetime.utcnow()
                    db.commit()
                    return

        # Save assets and transactions
        assets_count = 0
        transactions_count = 0

        # Create or get accounts for all assets.
        # Every demat-type asset (stock, MF, commodity, etc.) gets a DematAccount.
        # Every crypto asset gets a CryptoAccount.
        # Assets are grouped by (broker_name, account_id) since a single statement
        # (e.g. NSDL CAS) can produce assets with different broker_names.

        demat_account_map = {}  # (broker_name, account_id) -> DematAccount
        crypto_account = None

        if assets and len(assets) > 0:
            # Group assets by account
            demat_groups = {}   # (broker_name, account_id) -> list of asset indices
            crypto_indices = []

            for idx, ad in enumerate(assets):
                at = ad.get('asset_type')
                if at in DEMAT_ASSET_TYPES:
                    bn = ad.get('broker_name') or (statement.institution_name if statement.institution_name else 'unknown')
                    aid = ad.get('account_id') or f"{bn.upper().replace(' ', '-')}-AUTO-{statement.user_id}"
                    demat_groups.setdefault((bn, aid), []).append(idx)
                elif at in CRYPTO_ASSET_TYPES:
                    crypto_indices.append(idx)

            # Create demat account for each (broker, account_id) group
            for (bn, aid), indices in demat_groups.items():
                first_asset = assets[indices[0]]
                da = get_or_create_demat_account(
                    statement.user_id,
                    bn,
                    aid,
                    first_asset.get('account_holder_name'),
                    db,
                    cash_balance_usd,
                    portfolio_id=portfolio_id,
                )
                if da:
                    # Delete existing assets for this demat account to refresh holdings.
                    # Clear FK references first (same pattern as asset delete endpoints).
                    existing_asset_ids = [a.id for a in db.query(Asset.id).filter(
                        Asset.demat_account_id == da.id
                    ).all()]
                    if existing_asset_ids:
                        db.query(Alert).filter(Alert.asset_id.in_(existing_asset_ids)).update(
                            {Alert.asset_id: None}, synchronize_session=False
                        )
                        db.query(AssetSnapshot).filter(AssetSnapshot.asset_id.in_(existing_asset_ids)).update(
                            {AssetSnapshot.asset_id: None}, synchronize_session=False
                        )
                        db.query(MutualFundHolding).filter(MutualFundHolding.asset_id.in_(existing_asset_ids)).delete(
                            synchronize_session=False
                        )
                        db.query(Transaction).filter(Transaction.asset_id.in_(existing_asset_ids)).delete(
                            synchronize_session=False
                        )
                        db.query(Asset).filter(Asset.id.in_(existing_asset_ids)).delete(
                            synchronize_session=False
                        )
                        db.flush()
                    demat_account_map[(bn, aid)] = da

            # Create crypto account if there are crypto assets
            if crypto_indices:
                first_crypto = assets[crypto_indices[0]]
                exchange_name = (statement.institution_name
                                 or first_crypto.get('broker_name')
                                 or 'unknown')
                crypto_aid = (first_crypto.get('account_id')
                              or f"{exchange_name.upper().replace(' ', '-')}-AUTO-{statement.user_id}")
                crypto_account = get_or_create_crypto_account(
                    statement.user_id,
                    exchange_name,
                    crypto_aid,
                    db,
                )

        for asset_data in assets:
            # Link asset to the appropriate account
            at = asset_data.get('asset_type')
            if at in DEMAT_ASSET_TYPES:
                bn = asset_data.get('broker_name') or (statement.institution_name if statement.institution_name else 'unknown')
                aid = asset_data.get('account_id') or f"{bn.upper().replace(' ', '-')}-AUTO-{statement.user_id}"
                da = demat_account_map.get((bn, aid))
                if da:
                    asset_data['demat_account_id'] = da.id
            elif at in CRYPTO_ASSET_TYPES and crypto_account:
                asset_data['crypto_account_id'] = crypto_account.id

            # Assign portfolio_id to each asset
            if portfolio_id:
                asset_data['portfolio_id'] = portfolio_id

            # Lookup ISIN if not provided in statement
            if not asset_data.get('isin'):
                try:
                    isin, api_symbol = lookup_isin_for_asset(
                        asset_type=asset_data.get('asset_type', '').value if hasattr(asset_data.get('asset_type'), 'value') else str(asset_data.get('asset_type', '')),
                        symbol=asset_data.get('symbol', ''),
                        name=asset_data.get('name', '')
                    )
                    if isin:
                        asset_data['isin'] = isin
                        logger.info(f"Auto-populated ISIN for {asset_data.get('symbol')}: {isin}")
                        if api_symbol and not asset_data.get('api_symbol'):
                            asset_data['api_symbol'] = api_symbol
                            logger.info(f"Auto-populated API Symbol for {asset_data.get('symbol')}: {api_symbol}")
                except Exception as e:
                    logger.warning(f"Could not lookup ISIN for {asset_data.get('symbol')}: {str(e)}")
            
            # Create new asset (we deleted old ones above for demat accounts)
            new_asset = Asset(
                user_id=statement.user_id,
                **asset_data
            )
            new_asset.calculate_metrics()
            db.add(new_asset)
            assets_count += 1
        
        db.flush()  # Flush to get asset IDs
        
        for transaction_data in transactions:
            # Find corresponding asset
            asset = db.query(Asset).filter(
                Asset.user_id == statement.user_id,
                Asset.symbol == transaction_data.get('asset_symbol')
            ).first()
            
            if asset:
                new_transaction = Transaction(
                    asset_id=asset.id,
                    statement_id=statement.id,
                    transaction_type=transaction_data.get('transaction_type'),
                    transaction_date=transaction_data.get('transaction_date'),
                    quantity=transaction_data.get('quantity', 0),
                    price_per_unit=transaction_data.get('price_per_unit', 0),
                    total_amount=transaction_data.get('total_amount'),
                    fees=transaction_data.get('fees', 0),
                    taxes=transaction_data.get('taxes', 0),
                    description=transaction_data.get('description'),
                    reference_number=transaction_data.get('reference_number')
                )
                db.add(new_transaction)
                transactions_count += 1
        
        statement.assets_found = assets_count
        statement.transactions_found = transactions_count
        statement.status = StatementStatus.PROCESSED
        statement.processing_completed_at = datetime.utcnow()
        
    except Exception as e:
        statement.status = StatementStatus.FAILED
        statement.error_message = str(e)
    
    db.commit()


def extract_text_from_file(file_path: str, file_type: str):
    """
    Extract text/data from various file formats
    Returns string for text files, DataFrame for Excel/CSV
    """
    if 'pdf' in file_type.lower():
        return extract_text_from_pdf(file_path)
    elif 'csv' in file_type.lower():
        return extract_text_from_csv(file_path)
    elif 'excel' in file_type.lower() or 'spreadsheet' in file_type.lower() or file_path.endswith(('.xlsx', '.xls')):
        return extract_text_from_excel(file_path)
    else:
        # Try to read as text
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()


def extract_text_from_pdf(file_path: str, password: str = None) -> str:
    """Extract text from PDF file, with optional password support"""
    text = ""
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            # Decrypt if password provided
            if password and pdf_reader.is_encrypted:
                pdf_reader.decrypt(password)
            
            for page in pdf_reader.pages:
                text += page.extract_text()
    except Exception as e:
        raise Exception(f"Failed to extract text from PDF: {str(e)}")
    return text


def clean_pdf_text(text: str) -> str:
    """Remove doubled characters from PDF text extraction"""
    if not text:
        return ""
    result = []
    i = 0
    while i < len(text):
        result.append(text[i])
        if i + 1 < len(text) and text[i] == text[i + 1]:
            i += 2  # Skip the duplicate
        else:
            i += 1
    return ''.join(result)


def parse_nsdl_cas_pdf(file_path: str, statement: Statement, password: str = None) -> tuple:
    """
    Parse NSDL Consolidated Account Statement (CAS) PDF
    Returns (assets, transactions) tuple
    """
    if not PDFPLUMBER_AVAILABLE:
        raise Exception("pdfplumber library is required for NSDL CAS parsing. Install with: pip install pdfplumber")
    
    assets = []
    transactions = []
    
    try:
        with pdfplumber.open(file_path, password=password) as pdf:
            logger.info(f"Processing NSDL CAS PDF with {len(pdf.pages)} pages")
            
            # Process each page individually
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                cleaned = clean_pdf_text(text)
                
                logger.debug(f"Processing Page {page_num}")
                
                # Look for ISIN patterns (assets) on each page
                # NSDL/CDSL Mutual Funds: INF followed by alphanumeric
                mf_pattern = r'(INF\w+)\s+(.*?)\s+([\d,]+(?:\.[\d]+)?)\s+([\d,]+(?:\.[\d]+)?)\s+([\d,]+(?:\.[\d]+)?)'
                for match in re.finditer(mf_pattern, cleaned):
                    try:
                        isin = match.group(1)
                        description = match.group(2).strip()
                        units_str = match.group(3).replace(',', '')
                        nav_str = match.group(4).replace(',', '')
                        value_str = match.group(5).replace(',', '')
                        
                        units = float(units_str)
                        nav = float(nav_str)
                        value = float(value_str)
                        
                        # Skip if values don't make sense
                        if units == 0 or value == 0:
                            continue
                        
                        # Determine asset type
                        asset_type = AssetType.COMMODITY if 'GOLD' in description.upper() or 'SILVER' in description.upper() else AssetType.EQUITY_MUTUAL_FUND
                        
                        asset_data = {
                            'asset_type': asset_type.value,
                            'name': description[:100],
                            'symbol': isin,
                            'quantity': units,
                            'purchase_price': nav,
                            'current_price': nav,
                            'current_value': value,
                            'total_invested': units * nav,
                            'account_id': 'NSDL-CAS',
                            'broker_name': 'NSDL CAS',
                            'statement_id': statement.id
                        }
                        assets.append(asset_data)
                        logger.debug(f"  Added MF: {description[:40]} - {units} units @ ₹{nav}")
                    except (ValueError, IndexError) as e:
                        continue
                
                # Equities: INE followed by alphanumeric
                equity_pattern = r'(INE\w+)\s+(.*?)\s+([\d,]+(?:\.[\d]+)?)\s+[\d,]+(?:\.[\d]+)?\s+[\d,]+(?:\.[\d]+)?\s+([\d,]+(?:\.[\d]+)?)\s+([\d,]+(?:\.[\d]+)?)'
                for match in re.finditer(equity_pattern, cleaned):
                    try:
                        isin = match.group(1)
                        security_name = match.group(2).strip()
                        quantity_str = match.group(3).replace(',', '')
                        price_str = match.group(4).replace(',', '')
                        value_str = match.group(5).replace(',', '')
                        
                        quantity = float(quantity_str)
                        price = float(price_str)
                        value = float(value_str)
                        
                        # Skip if zero quantity
                        if quantity == 0 or value == 0:
                            continue
                        
                        # Extract symbol
                        symbol_match = re.search(r'^([A-Z][A-Z\s]+?)(?:\s+|#|LIMITED)', security_name)
                        symbol = symbol_match.group(1).strip() if symbol_match else security_name.split()[0]
                        
                        asset_data = {
                            'asset_type': AssetType.STOCK.value,
                            'name': security_name[:100],
                            'symbol': symbol,
                            'quantity': quantity,
                            'purchase_price': price,
                            'current_price': price,
                            'current_value': value,
                            'total_invested': quantity * price,
                            'account_id': 'CDSL-CAS',
                            'broker_name': 'CDSL CAS',
                            'statement_id': statement.id
                        }
                        assets.append(asset_data)
                        logger.debug(f"  Added Equity: {symbol} - {quantity} shares @ ₹{price}")
                    except (ValueError, IndexError) as e:
                        continue
                
                # Sovereign Gold Bonds: IN followed by 10 digits
                sgb_pattern = r'(IN\d{10})\s+Government of India.*?\s+([\d,]+(?:\.[\d]+)?)\s+([\d,]+(?:\.[\d]+)?)\s+([\d,]+(?:\.[\d]+)?)\s+([\d,]+(?:\.[\d]+)?)'
                for match in re.finditer(sgb_pattern, cleaned):
                    try:
                        isin = match.group(1)
                        units_str = match.group(2).replace(',', '')
                        face_value_str = match.group(3).replace(',', '')
                        market_price_str = match.group(4).replace(',', '')
                        value_str = match.group(5).replace(',', '')
                        
                        units = float(units_str)
                        face_value = float(face_value_str)
                        market_price = float(market_price_str)
                        value = float(value_str)
                        
                        asset_data = {
                            'asset_type': AssetType.COMMODITY.value,
                            'name': f"Sovereign Gold Bond {isin[-4:]}",
                            'symbol': isin,
                            'quantity': units,
                            'purchase_price': face_value,
                            'current_price': market_price,
                            'current_value': value,
                            'total_invested': units * face_value,
                            'account_id': 'NSDL-SGB',
                            'broker_name': 'NSDL CAS',
                            'statement_id': statement.id
                        }
                        assets.append(asset_data)
                        logger.debug(f"  Added SGB: {isin} - {units} units @ ₹{market_price}")
                    except (ValueError, IndexError) as e:
                        continue
            
            logger.info(f"Total assets extracted: {len(assets)}")
            
    except Exception as e:
        logger.error(f"Error parsing NSDL CAS PDF: {str(e)}", exc_info=True)
        raise Exception(f"Failed to parse NSDL CAS PDF: {str(e)}")
    
    return assets, transactions


def _classify_mf_scheme(scheme_name: str, category: str = '', sub_category: str = '') -> str:
    """Classify a mutual fund scheme as equity, debt, or commodity based on its name.

    When a structured category field is available (e.g. from Groww), it takes
    precedence over keyword-based heuristics from the scheme name.
    """
    upper = scheme_name.upper()
    # Gold/Silver ETFs and commodity funds
    if any(kw in upper for kw in ['GOLD', 'SILVER', 'COMMODITY']):
        return AssetType.COMMODITY.value
    # Use structured category when available (Groww provides Equity/Debt/Hybrid)
    if category:
        upper_cat = category.upper()
        if upper_cat == 'DEBT':
            return AssetType.DEBT_MUTUAL_FUND.value
        if upper_cat in ('EQUITY', 'HYBRID'):
            return AssetType.EQUITY_MUTUAL_FUND.value
    # Fallback: debt fund keywords from scheme name
    if any(kw in upper for kw in [
        'GILT', 'LIQUID', 'OVERNIGHT', 'MONEY MARKET', 'FLOATING RATE',
        'FLEXI DEBT', 'DYNAMIC BOND', 'DEBT', 'SHORT DURATION',
        'MEDIUM DURATION', 'LONG DURATION', 'ULTRA SHORT', 'LOW DURATION',
        'CORPORATE BOND', 'BANKING & PSU', 'CREDIT RISK', 'SHORT TERM DEBT',
    ]):
        return AssetType.DEBT_MUTUAL_FUND.value
    return AssetType.EQUITY_MUTUAL_FUND.value


def parse_mf_central_cas_pdf(file_path: str, statement: Statement, password: str = None) -> tuple:
    """
    Parse MF Central Consolidated Account Summary (CAS) PDF.
    Handles both SoA Holdings and Demat Holdings sections using table extraction.
    Returns (assets, transactions) tuple.
    """
    if not PDFPLUMBER_AVAILABLE:
        raise Exception("pdfplumber library is required for MF Central CAS parsing. Install with: pip install pdfplumber")

    assets = []
    transactions = []

    try:
        open_kwargs = {"password": password} if password else {}
        with pdfplumber.open(file_path, **open_kwargs) as pdf:
            logger.info(f"Processing MF Central CAS PDF with {len(pdf.pages)} pages")

            for page_num, page in enumerate(pdf.pages, 1):
                tables = page.extract_tables()
                if not tables:
                    continue

                for table in tables:
                    if not table or len(table) < 2:
                        continue

                    header = table[0]
                    if not header:
                        continue

                    # Normalise header strings for matching
                    norm_header = [str(h).replace('\n', ' ').strip().lower() if h else '' for h in header]

                    # Identify the table type by header keywords
                    has_scheme = any('scheme' in h for h in norm_header)
                    has_units = any('unit' in h for h in norm_header)
                    if not (has_scheme and has_units):
                        continue

                    # Determine column indices
                    id_col = 0  # Folio No. or Client Id
                    scheme_col = next((i for i, h in enumerate(norm_header) if 'scheme' in h), 1)
                    invested_col = next((i for i, h in enumerate(norm_header) if 'invested' in h), 2)
                    units_col = next((i for i, h in enumerate(norm_header) if 'unit' in h), 3)
                    nav_date_col = next((i for i, h in enumerate(norm_header) if 'nav date' in h), 4)
                    nav_col = next((i for i, h in enumerate(norm_header) if h == 'nav'), 5)
                    market_val_col = next((i for i, h in enumerate(norm_header) if 'market' in h), 6)

                    is_soa = 'folio' in norm_header[0]

                    for row in table[1:]:
                        try:
                            if not row or len(row) <= market_val_col:
                                continue

                            folio_or_client = str(row[id_col] or '').strip()
                            scheme = str(row[scheme_col] or '').replace('\n', ' ').strip()
                            if not scheme:
                                continue

                            def parse_indian_number(s: str) -> float:
                                return float(str(s).replace(',', '').strip()) if s and str(s).strip() else 0.0

                            invested = parse_indian_number(row[invested_col])
                            units = parse_indian_number(row[units_col])
                            nav = parse_indian_number(row[nav_col])
                            market_value = parse_indian_number(row[market_val_col])

                            if units == 0 and market_value == 0:
                                continue

                            # Calculate NAV from market value if NAV is 0
                            if nav == 0 and units > 0 and market_value > 0:
                                nav = market_value / units

                            # If invested value is 0 (Demat section), use market value as fallback
                            if invested == 0:
                                invested = market_value

                            asset_type = _classify_mf_scheme(scheme)

                            # Use a single consistent account_id for the whole
                            # MF Central CAS so all holdings end up in one demat
                            # account regardless of folio/client-id ordering.
                            account_id = 'MFCentral-CAS'

                            # The symbol must be unique per fund for correct
                            # frontend grouping.  SoA folios are already unique
                            # per fund, but Demat client IDs are shared across
                            # all holdings in the same demat account.
                            if is_soa:
                                unique_symbol = folio_or_client
                            else:
                                scheme_hash = hashlib.md5(scheme.encode()).hexdigest()[:8]
                                unique_symbol = f"{folio_or_client}-{scheme_hash}"

                            asset_data = {
                                'asset_type': asset_type,
                                'name': scheme[:100],
                                'symbol': unique_symbol,
                                'quantity': units,
                                'purchase_price': nav,
                                'current_price': nav,
                                'current_value': market_value,
                                'total_invested': invested,
                                'account_id': account_id,
                                'broker_name': 'mf_central',
                                'statement_id': statement.id,
                            }
                            assets.append(asset_data)
                            logger.info(f"  [{'SoA' if is_soa else 'Demat'}] {scheme[:50]} — {units} units, ₹{market_value:,.2f}")

                        except (ValueError, IndexError):
                            continue

            logger.info(f"MF Central CAS: extracted {len(assets)} holdings")

    except Exception as e:
        import traceback
        logger.error(f"Error parsing MF Central CAS PDF: {e}")
        traceback.print_exc()
        raise Exception(f"Failed to parse MF Central CAS PDF: {e}")

    return assets, transactions


def is_mf_central_cas_pdf(file_path: str, password: str = None) -> bool:
    """Check if a PDF is an MF Central Consolidated Account Summary."""
    if not PDFPLUMBER_AVAILABLE:
        return False
    try:
        open_kwargs = {"password": password} if password else {}
        with pdfplumber.open(file_path, **open_kwargs) as pdf:
            if pdf.pages:
                text = pdf.pages[0].extract_text() or ''
                return 'MFCentral' in text or 'Consolidated Account Summary' in text
    except Exception:
        pass
    return False


def parse_nsdl_demat_holdings(text: str, statement: Statement, broker_name: str) -> List[Dict]:
    """Parse NSDL Demat Account holdings from CAS text"""
    assets = []
    
    # Find NSDL account info (note: typo "Acount" in PDF)
    # Pattern: ICICI BANK LIMITED followed by NSDL Demat Acount and DP/Client IDs
    nsdl_pattern = r'ICICI BANK LIMITED\s+NSDL Demat Acount.*?DP ID:(\w+)\s+Client ID:(\w+)'
    nsdl_match = re.search(nsdl_pattern, text, re.DOTALL)
    
    if not nsdl_match:
        logger.debug("NSDL account info not found")
        return assets
    
    dp_id = nsdl_match.group(1)
    client_id = nsdl_match.group(2)
    account_id = f"{dp_id}-{client_id}"
    logger.info(f"Found NSDL account: {account_id}")
    
    # The NSDL holdings appear before CDSL section
    # Extract text between account info and CDSL section
    nsdl_holdings_pattern = r'NSDL Demat Acount.*?DP ID:\w+\s+Client ID:\w+(.*?)CDSL Demat Acount'
    holdings_match = re.search(nsdl_holdings_pattern, text, re.DOTALL)
    
    if not holdings_match:
        logger.debug("NSDL holdings section not found")
        return assets

    holdings_text = holdings_match.group(1)

    # Parse Mutual Funds from NSDL account
    # Pattern: INF... followed by description, units, NAV, value
    # Example: INF109KC1NT3 ICICI PRUDENTIAL MUTUAL FUND GOLD 2,30 140.31 3,2,706.79
    mf_pattern = r'(INF\w+)\s+(.*?)\s+([\d,]+(?:\.[\d]+)?)\s+([\d,]+(?:\.[\d]+)?)\s+([\d,]+(?:\.[\d]+)?)'
    
    for match in re.finditer(mf_pattern, holdings_text):
        isin = match.group(1)
        description = match.group(2).strip()
        units_str = match.group(3).replace(',', '')
        nav_str = match.group(4).replace(',', '')
        value_str = match.group(5).replace(',', '')
        
        try:
            units = float(units_str)
            nav = float(nav_str)
            value = float(value_str)
            
            # Extract fund name (first part before hyphen or full description)
            fund_name = description.split('-')[0].strip() if '-' in description else description[:50]
            
            # Classify as commodity if it's a gold/silver ETF
            asset_type = AssetType.COMMODITY if 'GOLD' in description.upper() or 'SILVER' in description.upper() else AssetType.EQUITY_MUTUAL_FUND
            
            asset_data = {
                'asset_type': asset_type,
                'name': fund_name,
                'symbol': isin,
                'isin': isin,
                'quantity': units,
                'purchase_price': nav,
                'current_price': nav,
                'current_value': value,
                'account_id': account_id,
                'broker_name': 'ICICI Bank (NSDL)',
                'statement_id': statement.id
            }
            assets.append(asset_data)
            logger.debug(f"  Added NSDL MF: {fund_name[:30]} - {units} units")
        except ValueError as e:
            logger.debug(f"  Skipped invalid MF entry: {e}")
            continue
    
    # Parse Sovereign Gold Bonds
    sgb_pattern = r'(IN\d{10})\s+Government of India.*?\s+([\d,]+(?:\.[\d]+)?)\s+([\d,]+(?:\.[\d]+)?)\s+([\d,]+(?:\.[\d]+)?)\s+([\d,]+(?:\.[\d]+)?)'
    
    for match in re.finditer(sgb_pattern, holdings_text):
        isin = match.group(1)
        units_str = match.group(2).replace(',', '')
        face_value_str = match.group(3).replace(',', '')
        market_price_str = match.group(4).replace(',', '')
        value_str = match.group(5).replace(',', '')
        
        try:
            units = float(units_str)
            face_value = float(face_value_str)
            market_price = float(market_price_str)
            value = float(value_str)
            
            asset_data = {
                'asset_type': AssetType.COMMODITY,
                'name': f"Sovereign Gold Bond {isin[-4:]}",
                'symbol': isin,
                'isin': isin,
                'quantity': units,
                'purchase_price': face_value,
                'current_price': market_price,
                'current_value': value,
                'account_id': account_id,
                'broker_name': 'ICICI Bank (NSDL)',
                'statement_id': statement.id
            }
            assets.append(asset_data)
            logger.debug(f"  Added SGB: {isin} - {units} units")
        except ValueError as e:
            logger.debug(f"  Skipped invalid SGB entry: {e}")
            continue
    
    return assets


def parse_cdsl_demat_holdings(text: str, statement: Statement, broker_name: str) -> List[Dict]:
    """Parse CDSL Demat Account holdings from CAS text"""
    assets = []
    
    # Find CDSL account info (note: typo "Acount" in PDF)
    cdsl_pattern = r'CDSL Demat Acount.*?DP ID:\s*(\w+)\s+Client ID:\s*(\w+)'
    cdsl_match = re.search(cdsl_pattern, text, re.DOTALL)
    
    if not cdsl_match:
        logger.debug("CDSL account info not found")
        return assets
    
    dp_id = cdsl_match.group(1)
    client_id = cdsl_match.group(2)
    account_id = f"{dp_id}-{client_id}"
    logger.info(f"Found CDSL account: {account_id}")
    
    # Extract CDSL holdings section (from CDSL account to end or next major section)
    cdsl_holdings_pattern = r'CDSL Demat Acount.*?DP ID:\w+\s+Client ID:\w+(.*?)(?:Mutual Fund Folios|Transactions|Notes:)'
    holdings_match = re.search(cdsl_holdings_pattern, text, re.DOTALL)
    
    if not holdings_match:
        logger.debug("CDSL holdings section not found")
        return assets
    
    holdings_text = holdings_match.group(1)
    
    # Parse Equities
    # Pattern: INE... SECURITY_NAME quantity1 quantity2 quantity3 market_price value
    # The pattern has 3 quantity columns (Current Bal, Safekeep Bal, Pledged Bal) then price and value
    equity_pattern = r'(INE\w+)\s+(.*?)\s+([\d,]+(?:\.[\d]+)?)\s+[\d,]+(?:\.[\d]+)?\s+[\d,]+(?:\.[\d]+)?\s+([\d,]+(?:\.[\d]+)?)\s+([\d,]+(?:\.[\d]+)?)'
    
    for match in re.finditer(equity_pattern, holdings_text):
        isin = match.group(1)
        security_name = match.group(2).strip()
        quantity_str = match.group(3).replace(',', '')
        market_price_str = match.group(4).replace(',', '')
        value_str = match.group(5).replace(',', '')
        
        try:
            quantity = float(quantity_str)
            market_price = float(market_price_str)
            value = float(value_str)
            
            # Skip if quantity is 0
            if quantity == 0:
                continue
            
            # Extract symbol from security name (first word or two)
            symbol_match = re.search(r'^([A-Z][A-Z\s]+?)(?:\s+|#|LIMITED)', security_name)
            symbol = symbol_match.group(1).strip() if symbol_match else security_name.split()[0]
            
            asset_data = {
                'asset_type': AssetType.STOCK,
                'name': security_name[:100],
                'symbol': symbol,
                'isin': isin,
                'quantity': quantity,
                'purchase_price': market_price,
                'current_price': market_price,
                'current_value': value,
                'account_id': account_id,
                'broker_name': 'Zerodha (CDSL)',
                'statement_id': statement.id
            }
            assets.append(asset_data)
            logger.debug(f"  Added CDSL Equity: {symbol} - {quantity} units")
        except ValueError as e:
            logger.debug(f"  Skipped invalid equity entry: {e}")
            continue
    
    # Parse Mutual Funds from CDSL
    mf_pattern = r'(INF\w+)\s+(.*?)\s+([\d,]+(?:\.[\d]+)?)\s+[\d,]+(?:\.[\d]+)?\s+[\d,]+(?:\.[\d]+)?\s+([\d,]+(?:\.[\d]+)?)\s+([\d,]+(?:\.[\d]+)?)'
    
    for match in re.finditer(mf_pattern, holdings_text):
        isin = match.group(1)
        fund_name = match.group(2).strip()
        units_str = match.group(3).replace(',', '')
        nav_str = match.group(4).replace(',', '')
        value_str = match.group(5).replace(',', '')
        
        try:
            units = float(units_str)
            nav = float(nav_str)
            value = float(value_str)
            
            # Skip if units is 0
            if units == 0:
                continue
            
            asset_data = {
                'asset_type': AssetType.EQUITY_MUTUAL_FUND,
                'name': fund_name[:100],
                'symbol': isin,
                'isin': isin,
                'quantity': units,
                'purchase_price': nav,
                'current_price': nav,
                'current_value': value,
                'account_id': account_id,
                'broker_name': 'Zerodha (CDSL)',
                'statement_id': statement.id
            }
            assets.append(asset_data)
            logger.debug(f"  Added CDSL MF: {fund_name[:30]} - {units} units")
        except ValueError as e:
            logger.debug(f"  Skipped invalid MF entry: {e}")
            continue
    
    return assets


def parse_mutual_fund_folios(text: str, statement: Statement) -> List[Dict]:
    """Parse Mutual Fund Folios section from CAS text"""
    assets = []
    
    # Find Mutual Fund Folios section
    folio_section_pattern = r'Mutual Fund Folios \(F\)(.*?)(?:Notes:|Transactions)'
    folio_match = re.search(folio_section_pattern, text, re.DOTALL)
    
    if not folio_match:
        return assets
    
    folio_text = folio_match.group(1)
    
    # Pattern: ISIN, Description, Folio No, Units, Avg Cost, Total Cost, Current NAV, Current Value
    folio_pattern = r'(INF\w+)\s+(.*?)\s+(\d+)\s+([\d,\.]+)\s+([\d,\.]+)\s+([\d,\.]+)\s+([\d,\.]+)\s+([\d,\.]+)'
    
    for match in re.finditer(folio_pattern, folio_text):
        isin = match.group(1)
        description = match.group(2).strip()
        folio_no = match.group(3)
        units = float(match.group(4).replace(',', ''))
        avg_cost = float(match.group(5).replace(',', ''))
        total_cost = float(match.group(6).replace(',', ''))
        current_nav = float(match.group(7).replace(',', ''))
        current_value = float(match.group(8).replace(',', ''))
        
        # Extract fund name from description
        fund_name = description.split('-')[0].strip() if '-' in description else description
        
        asset_data = {
            'asset_type': AssetType.EQUITY_MUTUAL_FUND,
            'name': fund_name,
            'symbol': isin,
            'isin': isin,
            'quantity': units,
            'purchase_price': avg_cost,
            'current_price': current_nav,
            'current_value': current_value,
            'account_id': folio_no,
            'broker_name': 'Direct MF',
            'statement_id': statement.id
        }
        assets.append(asset_data)
    
    return assets


def extract_text_from_csv(file_path: str):
    """
    Extract data from CSV file
    Returns DataFrame for structured CSV files
    """
    try:
        df = pd.read_csv(file_path)
        return df
    except Exception as e:
        raise Exception(f"Failed to read CSV: {str(e)}")


def is_icici_direct_stock_format(df: pd.DataFrame) -> bool:
    """Check if CSV is ICICI Direct stock portfolio format"""
    try:
        required_columns = ['Stock Symbol', 'Company Name', 'ISIN Code', 'Qty']
        df_columns = [col.strip() for col in df.columns]
        return all(col in df_columns for col in required_columns)
    except Exception:
        return False


def is_icici_direct_mf_format(df: pd.DataFrame) -> bool:
    """Check if CSV is ICICI Direct mutual fund format"""
    try:
        required_columns = ['Fund', 'Scheme', 'Folio', 'Units']
        df_columns = [col.strip() for col in df.columns]
        return all(col in df_columns for col in required_columns)
    except Exception:
        return False


def parse_icici_direct_stock_csv(df: pd.DataFrame, statement: Statement, account_info: dict = None) -> tuple:
    """
    Parse ICICI Direct stock portfolio CSV
    Format: Stock Symbol,Company Name,ISIN Code,Qty,Average Cost Price,Current Market Price,...
    """
    assets = []
    transactions = []
    
    if account_info is None:
        account_info = {}
    
    logger.info("Parsing ICICI Direct Stock Portfolio")
    logger.debug(f"DataFrame shape: {df.shape}")
    
    # Clean column names
    df.columns = df.columns.str.strip()
    
    for index, row in df.iterrows():
        try:
            symbol = str(row.get('Stock Symbol', '')).strip()
            if not symbol or symbol.lower() in ['total', 'grand total']:
                continue
            
            company_name = str(row.get('Company Name', symbol)).strip()
            isin = str(row.get('ISIN Code', '')).strip()
            
            # Extract quantity
            qty = row.get('Qty', 0)
            if pd.isna(qty):
                qty = 0
            qty = float(str(qty).replace(',', ''))
            
            if qty <= 0:
                logger.debug(f"Skipping {symbol} - zero quantity")
                continue

            # Extract prices
            avg_cost = row.get('Average Cost Price', 0)
            if pd.isna(avg_cost):
                avg_cost = 0
            avg_cost = float(str(avg_cost).replace(',', ''))
            
            current_price = row.get('Current Market Price', avg_cost)
            if pd.isna(current_price):
                current_price = avg_cost
            current_price = float(str(current_price).replace(',', ''))
            
            # Extract values
            value_at_cost = row.get('Value At Cost', qty * avg_cost)
            if pd.isna(value_at_cost):
                value_at_cost = qty * avg_cost
            else:
                value_at_cost = float(str(value_at_cost).replace(',', ''))
            
            current_value = row.get('Value At Market Price', qty * current_price)
            if pd.isna(current_value):
                current_value = qty * current_price
            else:
                current_value = float(str(current_value).replace(',', ''))
            
            # Determine asset type - check if it's a commodity ETF
            asset_type = AssetType.STOCK
            if any(keyword in symbol.upper() for keyword in ['GOLD', 'SILVER', 'ICIGOL', 'NIPSIL', 'SBIGOL']):
                asset_type = AssetType.COMMODITY
            
            logger.debug(f"Processing: {symbol} - {qty} units @ ₹{current_price}")

            # Create asset
            asset_data = {
                'asset_type': asset_type,
                'name': company_name[:100],
                'symbol': symbol,
                'quantity': qty,
                'purchase_price': avg_cost,
                'current_price': current_price,
                'total_invested': value_at_cost,
                'current_value': current_value,
                'account_id': account_info.get('account_id', 'ICICI-Direct'),
                'broker_name': 'ICICI Direct',
                'statement_id': statement.id,
                'details': {
                    'source': 'icici_direct_import',
                    'isin': isin,
                    'import_date': datetime.utcnow().isoformat()
                }
            }
            
            assets.append(asset_data)
            
            # Create transaction
            transaction_data = {
                'asset_symbol': symbol,
                'transaction_type': TransactionType.BUY,
                'transaction_date': statement.uploaded_at,
                'quantity': qty,
                'price_per_unit': avg_cost,
                'total_amount': value_at_cost,
                'description': f'Imported from ICICI Direct - {statement.filename}'
            }
            
            transactions.append(transaction_data)
            
        except Exception as e:
            logger.debug(f"Error processing row {index}: {str(e)}", exc_info=True)
            continue

    logger.info(f"Parsed {len(assets)} assets from ICICI Direct stock CSV")
    return assets, transactions


def parse_icici_direct_mf_csv(df: pd.DataFrame, statement: Statement, account_info: dict = None) -> tuple:
    """
    Parse ICICI Direct mutual fund holdings CSV
    Format: Fund,Scheme,Folio,Units,Last recorded NAV-Date,Last recorded NAV-Rs,Total value at NAV(₹),...
    """
    assets = []
    transactions = []
    
    if account_info is None:
        account_info = {}
    
    logger.info("Parsing ICICI Direct Mutual Fund Holdings")
    logger.debug(f"DataFrame shape: {df.shape}")
    
    # Clean column names
    df.columns = df.columns.str.strip()
    
    for index, row in df.iterrows():
        try:
            fund_house = str(row.get('Fund', '')).strip()
            scheme_name = str(row.get('Scheme', '')).strip()
            folio = str(row.get('Folio', '')).strip()
            
            if not scheme_name or scheme_name.lower() in ['total', 'grand total']:
                continue
            
            # Extract units
            units = row.get('Units', 0)
            if pd.isna(units):
                units = 0
            units = float(str(units).replace(',', ''))
            
            if units <= 0:
                logger.debug(f"Skipping {scheme_name} - zero units")
                continue
            
            # Extract NAV
            nav = row.get('Last recorded NAV-Rs', 0)
            if pd.isna(nav):
                nav = 0
            nav = float(str(nav).replace(',', ''))
            
            # Extract total value
            total_value = row.get('Total value at NAV(₹)', units * nav)
            if pd.isna(total_value):
                total_value = units * nav
            else:
                # Remove commas and handle Indian number format
                total_value_str = str(total_value).replace(',', '')
                total_value = float(total_value_str)
            
            # Extract cost
            value_at_cost = row.get('Value At Cost', total_value)
            if pd.isna(value_at_cost):
                value_at_cost = total_value
            else:
                value_at_cost = float(str(value_at_cost).replace(',', ''))
            
            # Calculate average cost
            avg_cost = value_at_cost / units if units > 0 else nav
            
            # Determine asset type based on scheme name
            asset_type = AssetType.EQUITY_MUTUAL_FUND  # Default
            scheme_lower = scheme_name.lower()
            
            # Check for debt/bond funds
            debt_keywords = ['debt', 'bond', 'gilt', 'liquid', 'money market', 'floating rate', 'dynamic bond']
            if any(keyword in scheme_lower for keyword in debt_keywords):
                asset_type = AssetType.DEBT_MUTUAL_FUND
            
            # Check for commodity ETFs
            if any(keyword in scheme_lower for keyword in ['gold', 'silver']):
                asset_type = AssetType.COMMODITY
            
            logger.debug(f"Processing: {scheme_name[:40]} - {units} units @ ₹{nav}")
            
            # Create asset
            asset_data = {
                'asset_type': asset_type,
                'name': scheme_name[:100],
                'symbol': scheme_name,  # Use scheme name as symbol
                'quantity': units,
                'purchase_price': avg_cost,
                'current_price': nav,
                'total_invested': value_at_cost,
                'current_value': total_value,
                'account_id': folio,
                'broker_name': 'ICICI Direct',
                'statement_id': statement.id,
                'details': {
                    'source': 'icici_direct_mf_import',
                    'fund_house': fund_house,
                    'folio': folio,
                    'import_date': datetime.utcnow().isoformat()
                }
            }
            
            assets.append(asset_data)
            
            # Create transaction
            transaction_data = {
                'asset_symbol': scheme_name,
                'transaction_type': TransactionType.BUY,
                'transaction_date': statement.uploaded_at,
                'quantity': units,
                'price_per_unit': avg_cost,
                'total_amount': value_at_cost,
                'description': f'Imported from ICICI Direct MF - {statement.filename}'
            }
            
            transactions.append(transaction_data)
            
        except Exception as e:
            logger.debug(f"Error processing row {index}: {str(e)}", exc_info=True)
            continue

    logger.info(f"Parsed {len(assets)} mutual funds from ICICI Direct CSV")
    return assets, transactions


def extract_account_info_from_excel(file_path: str) -> dict:
    """
    Extract account information from broker Excel file header
    Returns dict with account_id, account_holder_name, broker_name
    """
    account_info = {
        'account_id': None,
        'account_holder_name': None,
        'broker_name': 'Zerodha'  # Default for Zerodha files
    }

    try:
        # Read first few rows to extract account info
        df_header = pd.read_excel(file_path, sheet_name=0, header=None, nrows=20, engine='openpyxl')

        # Check for Groww MF format (has "HOLDING SUMMARY" and "HOLDINGS AS ON")
        is_groww_mf = False
        is_groww_stock = False
        for i in range(min(20, len(df_header))):
            row_vals = [str(val).strip() for val in df_header.iloc[i].values if pd.notna(val)]
            row_str = ' '.join(row_vals).lower()
            if 'holding summary' in row_str or 'holdings as on' in row_str:
                is_groww_mf = True
            if 'unique client code' in row_str or 'holdings statement for stocks' in row_str:
                is_groww_stock = True

        if is_groww_mf:
            account_info['broker_name'] = 'Groww'
            account_info['is_groww_mf'] = True
            for i in range(min(20, len(df_header))):
                row_vals = [str(val).strip() for val in df_header.iloc[i].values if pd.notna(val)]
                if len(row_vals) >= 2:
                    label = row_vals[0].lower()
                    value = row_vals[1]
                    if label == 'name':
                        account_info['account_holder_name'] = value
                    elif label == 'pan':
                        account_info['account_id'] = value
            logger.info(f"Detected Groww MF statement. Account info: {account_info}")
            return account_info

        # Check for Groww stock format (specific structure)
        # Row 0: "Name" | <name>
        # Row 1: "Unique Client Code" | <code>
        # Row 3: "Holdings statement for stocks as on ..."
        if is_groww_stock:
            account_info['broker_name'] = 'Groww'
            for i in range(min(5, len(df_header))):
                row_vals = [str(val).strip() for val in df_header.iloc[i].values if pd.notna(val)]
                if len(row_vals) >= 2:
                    label = row_vals[0].lower()
                    value = row_vals[1]
                    if label == 'name':
                        account_info['account_holder_name'] = value
                    elif 'unique client code' in label or 'client code' in label:
                        account_info['account_id'] = value
            logger.info(f"Detected Groww statement. Account info: {account_info}")
            return account_info

        # Generic extraction for other brokers (Zerodha etc.)
        for i in range(min(20, len(df_header))):
            row_str = ' '.join([str(val) for val in df_header.iloc[i].values if pd.notna(val)])
            row_str_lower = row_str.lower()

            # Look for client ID / Account ID
            if 'client' in row_str_lower or 'account' in row_str_lower or 'id' in row_str_lower:
                # Try to extract ID (usually alphanumeric)
                import re
                id_match = re.search(r'[A-Z0-9]{6,}', row_str)
                if id_match and not account_info['account_id']:
                    account_info['account_id'] = id_match.group()

            # Look for name
            if 'name' in row_str_lower and not account_info['account_holder_name']:
                # Extract name after 'name:' or similar
                parts = row_str.split(':')
                if len(parts) > 1:
                    name = parts[1].strip()
                    if name and len(name) > 2:
                        account_info['account_holder_name'] = name

        logger.debug(f"Extracted account info: {account_info}")
    except Exception as e:
        logger.debug(f"Could not extract account info: {str(e)}")

    return account_info


def extract_text_from_excel(file_path: str):
    """
    Extract data from Excel file and return as DataFrame or list of DataFrames
    For multi-sheet Zerodha files, returns a list of (sheet_name, dataframe) tuples
    Also extracts account information from file header
    """
    try:
        # Extract account information first
        account_info = extract_account_info_from_excel(file_path)
        
        # Check if file has multiple sheets
        xl_file = pd.ExcelFile(file_path, engine='openpyxl')
        
        # If it's a Zerodha file with multiple sheets, process all relevant sheets
        if len(xl_file.sheet_names) > 1:
            logger.info(f"Found {len(xl_file.sheet_names)} sheets: {xl_file.sheet_names}")
            sheets_data = []
            
            for sheet_name in xl_file.sheet_names:
                # Skip 'Combined' sheet to avoid duplicates
                if sheet_name.lower() == 'combined':
                    continue
                    
                df_raw = pd.read_excel(file_path, sheet_name=sheet_name, header=None, engine='openpyxl')
                
                # Find header row
                header_row = None
                for i in range(min(30, len(df_raw))):
                    row_values = df_raw.iloc[i].values
                    if any(str(val).strip().lower() in ('symbol', 'stock name', 'scheme name') for val in row_values if pd.notna(val)):
                        header_row = i
                        break

                if header_row is not None:
                    # Extract column names
                    headers = []
                    for val in df_raw.iloc[header_row].values:
                        if pd.notna(val):
                            headers.append(str(val).strip())
                        else:
                            headers.append(f'Unnamed_{len(headers)}')

                    # Create dataframe
                    df = pd.DataFrame(df_raw.iloc[header_row + 1:].values, columns=headers)
                    df = df.loc[:, (df != '').any(axis=0)]

                    logger.debug(f"Sheet '{sheet_name}': Extracted {len(df)} rows")
                    sheets_data.append((sheet_name, df, account_info))
            
            return sheets_data if sheets_data else None
        else:
            # Single sheet file - process as before
            df_raw = pd.read_excel(file_path, engine='openpyxl', header=None)

            header_row = None
            for i in range(min(30, len(df_raw))):
                row_values = df_raw.iloc[i].values
                if any(str(val).strip().lower() in ('symbol', 'stock name', 'scheme name') for val in row_values if pd.notna(val)):
                    header_row = i
                    break

            if header_row is not None:
                headers = []
                for val in df_raw.iloc[header_row].values:
                    if pd.notna(val):
                        headers.append(str(val).strip())
                    else:
                        headers.append(f'Unnamed_{len(headers)}')

                df = pd.DataFrame(df_raw.iloc[header_row + 1:].values, columns=headers)
                df = df.loc[:, (df != '').any(axis=0)]

                logger.debug(f"Extracted {len(df)} rows with columns: {list(df.columns)}")
                return (df, account_info)
            else:
                return pd.read_excel(file_path, engine='openpyxl')
            
    except Exception as e:
        raise Exception(f"Failed to read Excel: {str(e)}")


def parse_financial_statement(text: str, statement: Statement) -> tuple:
    """
    Parse bank or broker statement
    This is a simplified parser - in production, use more sophisticated parsing
    """
    assets = []
    transactions = []
    
    # Example parsing logic (customize based on actual statement formats)
    # Look for common patterns in financial statements
    
    # Pattern for stock transactions: DATE SYMBOL QTY PRICE AMOUNT
    stock_pattern = r'(\d{2}/\d{2}/\d{4})\s+([A-Z]{2,5})\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)'
    matches = re.findall(stock_pattern, text)
    
    for match in matches:
        date_str, symbol, qty, price, amount = match
        
        # Create or update asset
        assets.append({
            'asset_type': AssetType.STOCK,
            'name': symbol,
            'symbol': symbol,
            'quantity': float(qty),
            'purchase_price': float(price),
            'current_price': float(price),
            'total_invested': float(amount),
            'details': {'source': 'statement_import'}
        })
        
        # Create transaction
        transactions.append({
            'asset_symbol': symbol,
            'transaction_type': TransactionType.BUY,
            'transaction_date': datetime.strptime(date_str, '%d/%m/%Y'),
            'quantity': float(qty),
            'price_per_unit': float(price),
            'total_amount': float(amount),
            'description': f'Imported from {statement.filename}'
        })
    
    return assets, transactions


def parse_mutual_fund_statement(text: str, statement: Statement) -> tuple:
    """Parse mutual fund statement"""
    assets = []
    transactions = []
    
    # Simplified parsing - customize based on actual formats
    # Look for fund names, NAV, units, etc.
    
    return assets, transactions


def parse_generic_statement(text: str, statement: Statement) -> tuple:
    """Parse generic statement format"""
    assets = []
    transactions = []
    
    # Basic parsing logic
    # In production, consider using ML/NLP for better extraction
    
    return assets, transactions

# Made with Bob



def is_zerodha_format(df: pd.DataFrame, statement: Statement) -> bool:
    """
    Check if the DataFrame is in Zerodha consolidated holdings format
    """
    try:
        # Check for common Zerodha column names
        zerodha_columns = ['instrument', 'qty', 'avg. cost', 'ltp', 'cur. val', 'p&l', 'net chg.']
        zerodha_columns_alt = ['symbol', 'quantity', 'average price', 'last price', 'current value']
        
        df_columns_lower = [col.lower().strip() for col in df.columns]
        
        logger.debug(f"DataFrame columns: {df_columns_lower}")
        
        # Check if at least 4 of the Zerodha columns are present
        matches = sum(1 for col in zerodha_columns if col in df_columns_lower)
        matches_alt = sum(1 for col in zerodha_columns_alt if col in df_columns_lower)
        
        logger.debug(f"Zerodha format matches: {matches}, alt matches: {matches_alt}")
        
        return matches >= 3 or matches_alt >= 2  # Lowered threshold
    except Exception as e:
        logger.debug(f"Error checking Zerodha format: {str(e)}")
        return False


def parse_zerodha_holdings(df: pd.DataFrame, statement: Statement, sheet_name: str = None, account_info: dict = None) -> tuple:
    """
    Parse Zerodha consolidated holdings Excel file
    Handles both Equity and Mutual Fund holdings
    
    Args:
        df: DataFrame containing holdings data
        statement: Statement object
        sheet_name: Optional sheet name to determine asset type (Equity/Mutual Funds)
        account_info: Optional dict with account_id, broker_name, account_holder_name
    """
    assets = []
    transactions = []
    
    if account_info is None:
        account_info = {}
    
    logger.info(f"Parsing Zerodha Holdings (Sheet: {sheet_name or 'Unknown'})")
    logger.debug(f"Account Info: {account_info}")
    logger.debug(f"Starting to parse Zerodha holdings. DataFrame shape: {df.shape}")
    
    # Clean column names
    df.columns = df.columns.str.strip()
    
    # Skip empty rows
    df = df.dropna(how='all')
    
    logger.debug(f"After cleaning, DataFrame shape: {df.shape}")
    logger.debug(f"Columns: {list(df.columns)}")
    
    # Determine default asset type from sheet name
    default_asset_type = AssetType.STOCK
    if sheet_name:
        sheet_lower = sheet_name.lower()
        if 'mutual' in sheet_lower or 'mf' in sheet_lower:
            # Default to equity mutual fund, user can reclassify later
            default_asset_type = AssetType.EQUITY_MUTUAL_FUND
            logger.info(f"Sheet '{sheet_name}' detected as Mutual Fund sheet (defaulting to Equity MF)")
        elif 'equity' in sheet_lower or 'stock' in sheet_lower:
            default_asset_type = AssetType.STOCK
            logger.info(f"Sheet '{sheet_name}' detected as Equity sheet")
    
    # Detect asset type based on content
    for index, row in df.iterrows():
        try:
            # Get symbol
            symbol = row.get('Symbol', row.get('symbol', ''))
            if pd.isna(symbol) or not symbol:
                continue
            
            symbol = str(symbol).strip()
            if not symbol or symbol.lower() in ['total', 'grand total', 'symbol']:
                continue
            
            logger.debug(f"Processing symbol: {symbol}")
            
            # Determine asset type - use sheet name as primary indicator
            asset_type = default_asset_type
            
            # Reclassify SILVERBEES and GOLDBEES as commodities
            if symbol.upper() in ['SILVERBEES', 'GOLDBEES', 'GOLDSHARE', 'SILVERSHARE']:
                asset_type = AssetType.COMMODITY
            # Override based on sector if available
            elif sector := str(row.get('Sector', row.get('sector', ''))).strip():
                if 'etf' in sector.lower():
                    asset_type = AssetType.EQUITY_MUTUAL_FUND
            elif 'mutual' in symbol.lower():
                asset_type = AssetType.EQUITY_MUTUAL_FUND
            
            # Extract quantity - use "Quantity Available"
            qty = row.get('Quantity Available', row.get('quantity available', 0))
            if pd.isna(qty):
                qty = 0
            qty = float(str(qty).replace(',', ''))
            
            if qty <= 0:
                logger.debug(f"Skipping {symbol} - zero quantity")
                continue

            # Extract average price
            avg_price = row.get('Average Price', row.get('average price', 0))
            if pd.isna(avg_price):
                avg_price = 0
            avg_price = float(str(avg_price).replace(',', '').replace('₹', '').strip())
            
            # Extract current price (Previous Closing Price)
            current_price = row.get('Previous Closing Price', row.get('previous closing price', avg_price))
            if pd.isna(current_price):
                current_price = avg_price
            current_price = float(str(current_price).replace(',', '').replace('₹', '').strip())
            
            # Calculate values
            total_invested = qty * avg_price
            current_value = qty * current_price
            
            # Extract P&L
            pnl = row.get('Unrealized P&L', row.get('unrealized p&l', 0))
            if pd.isna(pnl):
                pnl = current_value - total_invested
            else:
                pnl = float(str(pnl).replace(',', '').replace('₹', '').strip())
            
            logger.debug(f"  Qty: {qty}, Avg Price: {avg_price}, Current Price: {current_price}")
            
            # Create asset with account information
            asset_data = {
                'asset_type': asset_type,
                'name': symbol,
                'symbol': symbol,
                'quantity': qty,
                'purchase_price': avg_price,
                'current_price': current_price,
                'total_invested': total_invested,
                'current_value': current_value,
                'account_id': account_info.get('account_id'),
                'broker_name': account_info.get('broker_name', 'Zerodha'),
                'account_holder_name': account_info.get('account_holder_name'),
                'statement_id': statement.id,
                'details': {
                    'source': 'zerodha_import',
                    'broker': 'zerodha',
                    'sector': sector,
                    'import_date': datetime.utcnow().isoformat()
                }
            }
            
            assets.append(asset_data)
            
            # Create a transaction record for the holding
            transaction_data = {
                'asset_symbol': symbol,
                'transaction_type': TransactionType.BUY,
                'transaction_date': statement.uploaded_at,
                'quantity': qty,
                'price_per_unit': avg_price,
                'total_amount': total_invested,
                'description': f'Imported from Zerodha holdings - {statement.filename}'
            }
            
            transactions.append(transaction_data)
            
        except Exception as e:
            # Log error but continue processing other rows
            logger.debug(f"Error processing row {index}: {str(e)}", exc_info=True)
            continue

    logger.info(f"Parsed {len(assets)} assets and {len(transactions)} transactions")
    return assets, transactions


def is_groww_format(df: pd.DataFrame, account_info: dict = None) -> bool:
    """
    Check if the DataFrame is in Groww stock holdings format.
    Groww headers: Stock Name, ISIN, Quantity, Average buy price, Buy value,
                   Closing price, Closing value, Unrealised P&L
    """
    try:
        df_columns_lower = [col.lower().strip() for col in df.columns]
        groww_columns = ['stock name', 'isin', 'quantity', 'average buy price', 'closing price']
        matches = sum(1 for col in groww_columns if col in df_columns_lower)
        # Also check account_info broker_name
        if account_info and account_info.get('broker_name', '').lower() == 'groww':
            return matches >= 2
        return matches >= 3
    except Exception:
        return False


def parse_groww_holdings(df: pd.DataFrame, statement: Statement, account_info: dict = None) -> tuple:
    """
    Parse Groww stock holdings Excel file.
    Columns: Stock Name, ISIN, Quantity, Average buy price, Buy value,
             Closing price, Closing value, Unrealised P&L
    """
    assets = []
    transactions = []

    if account_info is None:
        account_info = {}

    logger.info("Parsing Groww Holdings")
    logger.debug(f"Account Info: {account_info}")
    logger.debug(f"DataFrame shape: {df.shape}")

    # Clean column names
    df.columns = df.columns.str.strip()

    # Drop empty rows
    df = df.dropna(how='all')

    # Normalize column lookup (case-insensitive)
    col_map = {col.lower(): col for col in df.columns}

    def get_col(name):
        return col_map.get(name.lower())

    stock_name_col = get_col('Stock Name')
    isin_col = get_col('ISIN')
    qty_col = get_col('Quantity')
    avg_price_col = get_col('Average buy price')
    buy_value_col = get_col('Buy value')
    closing_price_col = get_col('Closing price')
    closing_value_col = get_col('Closing value')
    pnl_col = get_col('Unrealised P&L')

    if not stock_name_col or not qty_col:
        logger.debug("Required columns not found in Groww statement")
        return assets, transactions

    logger.debug(f"Columns mapped: {list(df.columns)}")

    for index, row in df.iterrows():
        try:
            name = row.get(stock_name_col, '') if stock_name_col else ''
            if pd.isna(name) or not str(name).strip():
                continue
            name = str(name).strip()

            # Skip summary/total rows
            if name.lower() in ('total', 'grand total', ''):
                continue

            isin = str(row.get(isin_col, '')).strip() if isin_col else ''
            if pd.isna(isin) or isin == 'nan':
                isin = ''

            # Quantity
            qty = row.get(qty_col, 0) if qty_col else 0
            if pd.isna(qty):
                qty = 0
            qty = float(str(qty).replace(',', ''))
            if qty <= 0:
                logger.debug(f"Skipping {name} - zero quantity")
                continue

            # Average buy price
            avg_price = row.get(avg_price_col, 0) if avg_price_col else 0
            if pd.isna(avg_price):
                avg_price = 0
            avg_price = float(str(avg_price).replace(',', ''))

            # Buy value (total invested)
            buy_value = row.get(buy_value_col, qty * avg_price) if buy_value_col else qty * avg_price
            if pd.isna(buy_value):
                buy_value = qty * avg_price
            else:
                buy_value = float(str(buy_value).replace(',', ''))

            # Closing price
            closing_price = row.get(closing_price_col, avg_price) if closing_price_col else avg_price
            if pd.isna(closing_price):
                closing_price = avg_price
            closing_price = float(str(closing_price).replace(',', ''))

            # Closing value (current value)
            closing_value = row.get(closing_value_col, qty * closing_price) if closing_value_col else qty * closing_price
            if pd.isna(closing_value):
                closing_value = qty * closing_price
            else:
                closing_value = float(str(closing_value).replace(',', ''))

            # Derive symbol from name (uppercase, first word or abbreviation)
            # Use ISIN as fallback symbol if available
            symbol = name.upper().replace(' LIMITED', '').replace(' LTD', '').strip()
            # Truncate long names to a reasonable symbol
            if len(symbol) > 20:
                symbol = symbol.split()[0]

            # Determine asset type
            asset_type = AssetType.STOCK
            name_upper = name.upper()
            if any(kw in name_upper for kw in ['GOLD', 'SILVER', 'GOLDBEES', 'SILVERBEES']):
                asset_type = AssetType.COMMODITY

            logger.debug(f"Processing: {name} ({symbol}) - {qty} units @ avg {avg_price}, closing {closing_price}")

            asset_data = {
                'asset_type': asset_type,
                'name': name[:100],
                'symbol': symbol,
                'isin': isin if isin else None,
                'quantity': qty,
                'purchase_price': avg_price,
                'current_price': closing_price,
                'total_invested': buy_value,
                'current_value': closing_value,
                'account_id': account_info.get('account_id', f'GROWW_{statement.user_id}'),
                'broker_name': 'Groww',
                'account_holder_name': account_info.get('account_holder_name'),
                'statement_id': statement.id,
                'details': {
                    'source': 'groww_import',
                    'broker': 'groww',
                    'isin': isin,
                    'import_date': datetime.utcnow().isoformat()
                }
            }
            assets.append(asset_data)

            # Create transaction record
            transaction_data = {
                'asset_symbol': symbol,
                'transaction_type': TransactionType.BUY,
                'transaction_date': statement.uploaded_at,
                'quantity': qty,
                'price_per_unit': avg_price,
                'total_amount': buy_value,
                'description': f'Imported from Groww holdings - {statement.filename}'
            }
            transactions.append(transaction_data)

        except Exception as e:
            logger.debug(f"Error processing row {index}: {str(e)}", exc_info=True)
            continue

    logger.info(f"Parsed {len(assets)} assets and {len(transactions)} transactions from Groww")
    return assets, transactions


def is_groww_mf_format(df: pd.DataFrame, account_info: dict = None) -> bool:
    """
    Check if the DataFrame is in Groww MF holdings format.
    Groww MF headers: Scheme Name, AMC, Category, Sub-category, Folio No.,
                      Source, Units, Invested Value, Current Value, Returns, XIRR
    """
    try:
        df_columns_lower = [str(col).lower().strip() for col in df.columns]
        groww_mf_columns = ['scheme name', 'amc', 'folio no.', 'units', 'invested value', 'current value']
        matches = sum(1 for col in groww_mf_columns if col in df_columns_lower)
        if account_info and account_info.get('broker_name', '').lower() == 'groww':
            return matches >= 3
        return matches >= 4
    except Exception:
        return False


def parse_groww_mf_holdings(df: pd.DataFrame, statement: Statement, account_info: dict = None) -> tuple:
    """
    Parse Groww MF holdings Excel file.
    Columns: Scheme Name, AMC, Category, Sub-category, Folio No., Source,
             Units, Invested Value, Current Value, Returns, XIRR

    Uses the shared _classify_mf_scheme() for asset type classification and
    relies on the central AMFI lookup in process_statement() for ISIN resolution.
    """
    assets = []
    transactions = []

    if account_info is None:
        account_info = {}

    logger.info("Parsing Groww MF Holdings")
    logger.debug(f"Account Info: {account_info}")
    logger.debug(f"DataFrame shape: {df.shape}")

    # Clean column names
    df.columns = df.columns.str.strip()

    # Case-insensitive column lookup
    col_map = {col.lower(): col for col in df.columns}

    def get_col(name):
        return col_map.get(name.lower())

    scheme_name_col = get_col('Scheme Name')
    amc_col = get_col('AMC')
    category_col = get_col('Category')
    sub_category_col = get_col('Sub-category') or get_col('Sub-Category') or get_col('Subcategory')
    folio_col = get_col('Folio No.') or get_col('Folio No') or get_col('Folio')
    source_col = get_col('Source')
    units_col = get_col('Units')
    invested_value_col = get_col('Invested Value')
    current_value_col = get_col('Current Value')
    returns_col = get_col('Returns')
    xirr_col = get_col('XIRR')

    if not scheme_name_col or not units_col:
        logger.debug("Required columns not found in Groww MF statement")
        return assets, transactions

    logger.debug(f"Columns mapped: {list(df.columns)}")

    for index, row in df.iterrows():
        try:
            scheme_name = row.get(scheme_name_col)
            if pd.isna(scheme_name) or not str(scheme_name).strip():
                continue

            scheme_name = str(scheme_name).strip()

            # Skip summary/header rows
            if scheme_name.lower() in ['scheme name', 'total', 'grand total', '']:
                continue

            # Parse units
            units = row.get(units_col)
            if pd.isna(units):
                continue
            units = float(str(units).replace(',', ''))
            if units <= 0:
                continue

            # Parse invested value
            invested_value = 0.0
            if invested_value_col:
                val = row.get(invested_value_col)
                if pd.notna(val):
                    invested_value = float(str(val).replace(',', ''))

            # Parse current value
            current_value = 0.0
            if current_value_col:
                val = row.get(current_value_col)
                if pd.notna(val):
                    current_value = float(str(val).replace(',', ''))

            # Calculate prices
            avg_cost = invested_value / units if units > 0 else 0.0
            current_nav = current_value / units if units > 0 else 0.0

            # Parse returns
            returns = 0.0
            if returns_col:
                val = row.get(returns_col)
                if pd.notna(val):
                    returns = float(str(val).replace(',', ''))

            # Parse XIRR
            xirr_value = None
            if xirr_col:
                val = row.get(xirr_col)
                if pd.notna(val):
                    xirr_str = str(val).replace('%', '').strip()
                    try:
                        xirr_value = float(xirr_str)
                    except ValueError:
                        pass

            # Get category info
            category = ''
            if category_col:
                val = row.get(category_col)
                if pd.notna(val):
                    category = str(val).strip()

            sub_category = ''
            if sub_category_col:
                val = row.get(sub_category_col)
                if pd.notna(val):
                    sub_category = str(val).strip()

            # Get AMC
            amc = ''
            if amc_col:
                val = row.get(amc_col)
                if pd.notna(val):
                    amc = str(val).strip()

            # Get folio number
            folio_no = ''
            if folio_col:
                val = row.get(folio_col)
                if pd.notna(val):
                    folio_no = str(val).strip()

            # Get source
            source = ''
            if source_col:
                val = row.get(source_col)
                if pd.notna(val):
                    source = str(val).strip()

            # Classify using the shared function (with Groww's category field)
            asset_type = _classify_mf_scheme(scheme_name, category, sub_category)

            logger.debug(
                f"Processing MF: {scheme_name[:40]} - {units} units, "
                f"invested={invested_value}, current={current_value}, type={asset_type}"
            )

            asset_data = {
                'asset_type': asset_type,
                'name': scheme_name[:100],
                'symbol': scheme_name[:50],
                'quantity': units,
                'purchase_price': avg_cost,
                'current_price': current_nav,
                'total_invested': invested_value,
                'current_value': current_value,
                'account_id': account_info.get('account_id', f'GROWW_MF_{statement.user_id}'),
                'broker_name': 'Groww',
                'account_holder_name': account_info.get('account_holder_name'),
                'statement_id': statement.id,
                'details': {
                    'source': 'groww_mf_import',
                    'broker': 'groww',
                    'amc': amc,
                    'category': category,
                    'sub_category': sub_category,
                    'folio_no': folio_no,
                    'holding_source': source,
                    'xirr': xirr_value,
                    'returns': returns,
                    'import_date': datetime.utcnow().isoformat()
                }
            }
            assets.append(asset_data)

            # Create a buy transaction record
            transaction_data = {
                'asset_symbol': scheme_name[:50],
                'transaction_type': TransactionType.BUY,
                'transaction_date': statement.uploaded_at,
                'quantity': units,
                'price_per_unit': avg_cost,
                'total_amount': invested_value,
                'description': f'Imported from Groww MF holdings - {statement.filename}'
            }
            transactions.append(transaction_data)

        except Exception as e:
            logger.debug(f"Error processing MF row {index}: {str(e)}", exc_info=True)
            continue

    logger.info(f"Parsed {len(assets)} mutual funds and {len(transactions)} transactions from Groww MF")
    return assets, transactions


def process_vested_statement(statement: Statement) -> tuple:
    """
    Process Vested broker statement
    
    Returns:
        Tuple of (assets, transactions)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    assets = []
    transactions = []
    
    try:
        # Parse the Vested statement
        holdings, cash_balance_usd = VestedParser.parse_statement(statement.file_path)
        
        # Get current USD to INR rate
        usd_to_inr = get_usd_to_inr_rate()
        logger.info(f"Using USD to INR rate: {usd_to_inr}")
        
        # Use a default account ID for Vested (user can update it later)
        # Format: VESTED_<user_id>
        vested_account_id = f"VESTED_{statement.user_id}"
        
        # Process each holding
        for holding in holdings:
            # Convert USD values to INR
            current_price_inr = holding['current_price_usd'] * usd_to_inr
            average_cost_inr = holding['average_cost_usd'] * usd_to_inr
            market_value_inr = holding['market_value_usd'] * usd_to_inr
            total_invested_inr = holding['total_invested_usd'] * usd_to_inr
            
            asset_data = {
                'statement_id': statement.id,
                'asset_type': AssetType.US_STOCK,
                'name': holding['name'],
                'symbol': holding['symbol'],
                'broker_name': 'Vested',
                'account_id': vested_account_id,
                'quantity': holding['quantity'],
                'purchase_price': average_cost_inr,
                'current_price': current_price_inr,
                'total_invested': total_invested_inr,
                'current_value': market_value_inr,
                'details': {
                    'exchange': 'US',
                    'currency': 'USD',
                    'usd_to_inr_rate': usd_to_inr,
                    'price_usd': holding['current_price_usd'],
                    'avg_cost_usd': holding['average_cost_usd'],
                    'market_value_usd': holding['market_value_usd']
                }
            }
            
            assets.append(asset_data)
        
        # Add cash balance as a separate asset if present
        if cash_balance_usd > 0:
            cash_balance_inr = cash_balance_usd * usd_to_inr
            cash_asset = {
                'statement_id': statement.id,
                'asset_type': AssetType.CASH,
                'name': 'Vested Cash Balance',
                'symbol': 'CASH_USD',
                'broker_name': 'Vested',
                'account_id': vested_account_id,
                'quantity': cash_balance_usd,
                'purchase_price': usd_to_inr,
                'current_price': usd_to_inr,
                'total_invested': cash_balance_inr,
                'current_value': cash_balance_inr,
                'details': {
                    'currency': 'USD',
                    'usd_to_inr_rate': usd_to_inr,
                    'balance_usd': cash_balance_usd
                }
            }
            assets.append(cash_asset)
            logger.info(f"Added Vested cash balance: ${cash_balance_usd} (₹{cash_balance_inr:.2f})")
        
        logger.info(f"Processed {len(holdings)} Vested holdings")
        
    except Exception as e:
        logger.error(f"Error processing Vested statement: {str(e)}")
        raise
    
    return assets, transactions, cash_balance_usd


def process_indmoney_statement(statement: Statement) -> tuple:
    """
    Process INDMoney broker statement
    
    Returns:
        Tuple of (assets, transactions)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    assets = []
    transactions = []
    
    try:
        # Parse the INDMoney statement
        holdings, cash_balance_usd = INDMoneyParser.parse_statement(statement.file_path)
        
        # Get current USD to INR rate
        usd_to_inr = get_usd_to_inr_rate()
        logger.info(f"Using USD to INR rate: {usd_to_inr}")
        
        # Use a default account ID for INDMoney (user can update it later)
        # Format: INDMONEY_<user_id>
        indmoney_account_id = f"INDMONEY_{statement.user_id}"
        
        # Process each holding
        for holding in holdings:
            # Convert USD values to INR
            current_price_inr = holding['current_price_usd'] * usd_to_inr
            average_cost_inr = holding['average_cost_usd'] * usd_to_inr
            market_value_inr = holding['market_value_usd'] * usd_to_inr
            total_invested_inr = holding['total_invested_usd'] * usd_to_inr
            
            asset_data = {
                'statement_id': statement.id,
                'asset_type': AssetType.US_STOCK,
                'name': holding['name'],
                'symbol': holding['symbol'],
                'broker_name': 'INDMoney',
                'account_id': indmoney_account_id,
                'quantity': holding['quantity'],
                'purchase_price': average_cost_inr,
                'current_price': current_price_inr,
                'total_invested': total_invested_inr,
                'current_value': market_value_inr,
                'details': {
                    'exchange': 'US',
                    'currency': 'USD',
                    'usd_to_inr_rate': usd_to_inr,
                    'price_usd': holding['current_price_usd'],
                    'avg_cost_usd': holding['average_cost_usd'],
                    'market_value_usd': holding['market_value_usd']
                }
            }
            
            assets.append(asset_data)
        
        # Add cash balance as a separate asset if present
        if cash_balance_usd > 0:
            cash_balance_inr = cash_balance_usd * usd_to_inr
            cash_asset = {
                'statement_id': statement.id,
                'asset_type': AssetType.CASH,
                'name': 'INDMoney Cash Balance',
                'symbol': 'CASH_USD',
                'broker_name': 'INDMoney',
                'account_id': indmoney_account_id,
                'quantity': cash_balance_usd,
                'purchase_price': usd_to_inr,
                'current_price': usd_to_inr,
                'total_invested': cash_balance_inr,
                'current_value': cash_balance_inr,
                'details': {
                    'currency': 'USD',
                    'usd_to_inr_rate': usd_to_inr,
                    'balance_usd': cash_balance_usd
                }
            }
            assets.append(cash_asset)
            logger.info(f"Added INDMoney cash balance: ${cash_balance_usd} (₹{cash_balance_inr:.2f})")
        
        logger.info(f"Processed {len(holdings)} INDMoney holdings")
        
    except Exception as e:
        logger.error(f"Error processing INDMoney statement: {str(e)}")
        raise
    
    return assets, transactions, cash_balance_usd


# Made with Bob
