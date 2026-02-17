"""
Statement processor service for extracting assets and transactions from uploaded statements
"""
from sqlalchemy.orm import Session
from app.models.statement import Statement, StatementStatus, StatementType
from app.models.asset import Asset, AssetType
from app.models.transaction import Transaction, TransactionType
from app.models.demat_account import DematAccount, BrokerName
from datetime import datetime
import PyPDF2
import pandas as pd
import re
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

logger = logging.getLogger(__name__)


def get_or_create_demat_account(
    user_id: int,
    broker_name: str,
    account_id: str,
    account_holder_name: Optional[str],
    db: Session,
    cash_balance_usd: Optional[float] = None
) -> Optional[DematAccount]:
    """
    Get existing demat account or create a new one
    """
    from app.services.currency_converter import get_usd_to_inr_rate
    
    # Map broker names to BrokerName enum
    broker_mapping = {
        'zerodha': BrokerName.ZERODHA,
        'groww': BrokerName.GROWW,
        'upstox': BrokerName.UPSTOX,
        'angel one': BrokerName.ANGEL_ONE,
        'angel': BrokerName.ANGEL_ONE,
        'icici direct': BrokerName.ICICI_DIRECT,
        'icici': BrokerName.ICICI_DIRECT,
        'hdfc securities': BrokerName.HDFC_SECURITIES,
        'hdfc': BrokerName.HDFC_SECURITIES,
        'kotak securities': BrokerName.KOTAK_SECURITIES,
        'kotak': BrokerName.KOTAK_SECURITIES,
        'axis direct': BrokerName.AXIS_DIRECT,
        'axis': BrokerName.AXIS_DIRECT,
        'sharekhan': BrokerName.SHAREKHAN,
        'motilal oswal': BrokerName.MOTILAL_OSWAL,
        'iifl securities': BrokerName.IIFL_SECURITIES,
        'iifl': BrokerName.IIFL_SECURITIES,
        'indmoney': BrokerName.INDMONEY,
        'vested': BrokerName.VESTED,
    }
    
    broker_name_lower = broker_name.lower() if broker_name else ''
    broker_enum = broker_mapping.get(broker_name_lower, BrokerName.OTHER)
    
    if not account_id:
        return None
    
    # Check if demat account exists
    demat_account = db.query(DematAccount).filter(
        DematAccount.user_id == user_id,
        DematAccount.broker_name == broker_enum,
        DematAccount.account_id == account_id
    ).first()
    
    # Determine currency based on broker
    is_us_broker = broker_enum in [BrokerName.VESTED, BrokerName.INDMONEY]
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
            is_active=True
        )
        db.add(demat_account)
        db.flush()  # Get the ID
    else:
        # Update last statement date and cash balance if provided
        demat_account.last_statement_date = datetime.utcnow()
        if account_holder_name and not demat_account.account_holder_name:
            demat_account.account_holder_name = account_holder_name
        
        if is_us_broker and cash_balance_usd is not None:
            usd_to_inr = get_usd_to_inr_rate()
            demat_account.cash_balance = cash_balance_usd * usd_to_inr
            demat_account.cash_balance_usd = cash_balance_usd
    
    return demat_account


def process_statement(statement_id: int, db: Session):
    """
    Main function to process an uploaded statement
    """
    statement = db.query(Statement).filter(Statement.id == statement_id).first()
    if not statement:
        return
    
    statement.status = StatementStatus.PROCESSING
    statement.processing_started_at = datetime.utcnow()
    db.commit()
    
    try:
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
        else:
            # Extract data from file
            data = extract_text_from_file(statement.file_path, statement.file_type)
            
            assets = []
            transactions = []
            
            # Check if it's a CSV file with DataFrame
            if isinstance(data, pd.DataFrame):
                # Check for ICICI Direct formats
                if is_icici_direct_stock_format(data):
                    print("Detected ICICI Direct Stock CSV format")
                    assets, transactions = parse_icici_direct_stock_csv(data, statement)
                elif is_icici_direct_mf_format(data):
                    print("Detected ICICI Direct Mutual Fund CSV format")
                    assets, transactions = parse_icici_direct_mf_csv(data, statement)
                # Check if it's Zerodha format
                elif is_zerodha_format(data, statement):
                    assets, transactions = parse_zerodha_holdings(data, statement, None, {})
                else:
                    # Try generic parsing
                    text = data.to_string()
                    if statement.statement_type.value in ['bank_statement', 'broker_statement']:
                        assets, transactions = parse_financial_statement(text, statement)
                    elif statement.statement_type.value == 'mutual_fund_statement':
                        assets, transactions = parse_mutual_fund_statement(text, statement)
                    else:
                        assets, transactions = parse_generic_statement(text, statement)
            # Check if it's a multi-sheet Zerodha file
            elif isinstance(data, list):
                print(f"Processing {len(data)} sheets")
                for item in data:
                    sheet_name, df, account_info = item
                    print(f"\nProcessing sheet: {sheet_name}")
                    if is_zerodha_format(df, statement):
                        sheet_assets, sheet_transactions = parse_zerodha_holdings(df, statement, sheet_name, account_info)
                        assets.extend(sheet_assets)
                        transactions.extend(sheet_transactions)
            # Check if it's a single DataFrame Zerodha file with account info
            elif isinstance(data, tuple) and len(data) == 2:
                df, account_info = data
                if isinstance(df, pd.DataFrame):
                    # Check for ICICI Direct formats first
                    if is_icici_direct_stock_format(df):
                        print("Detected ICICI Direct Stock CSV format")
                        assets, transactions = parse_icici_direct_stock_csv(df, statement, account_info)
                    elif is_icici_direct_mf_format(df):
                        print("Detected ICICI Direct Mutual Fund CSV format")
                        assets, transactions = parse_icici_direct_mf_csv(df, statement, account_info)
                    elif is_zerodha_format(df, statement):
                        assets, transactions = parse_zerodha_holdings(df, statement, None, account_info)
            # Parse based on statement type
            elif statement.statement_type.value in ['bank_statement', 'broker_statement']:
                text = data if isinstance(data, str) else str(data)
                assets, transactions = parse_financial_statement(text, statement)
            elif statement.statement_type.value == 'mutual_fund_statement':
                text = data if isinstance(data, str) else str(data)
                assets, transactions = parse_mutual_fund_statement(text, statement)
            else:
                text = data if isinstance(data, str) else str(data)
                assets, transactions = parse_generic_statement(text, statement)
        
        # Save assets and transactions
        assets_count = 0
        transactions_count = 0
        
        # Create or get demat account if this is a stock/demat statement
        demat_account = None
        if assets and len(assets) > 0:
            first_asset = assets[0]
            broker_name = first_asset.get('broker_name')
            account_id = first_asset.get('account_id')
            account_holder_name = first_asset.get('account_holder_name')
            
            # Only create demat account for stock/mutual fund assets
            asset_type = first_asset.get('asset_type')
            if asset_type in [AssetType.STOCK, AssetType.US_STOCK, AssetType.EQUITY_MUTUAL_FUND,
                             AssetType.DEBT_MUTUAL_FUND, AssetType.COMMODITY]:
                if broker_name and account_id:
                    demat_account = get_or_create_demat_account(
                        statement.user_id,
                        broker_name,
                        account_id,
                        account_holder_name,
                        db,
                        cash_balance_usd
                    )
                    
                    # Delete existing assets for this demat account to refresh holdings
                    if demat_account:
                        db.query(Asset).filter(
                            Asset.demat_account_id == demat_account.id
                        ).delete()
                        db.flush()
        
        for asset_data in assets:
            # Add demat_account_id to asset_data if available
            if demat_account:
                asset_data['demat_account_id'] = demat_account.id
            
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
            print(f"Processing NSDL CAS PDF with {len(pdf.pages)} pages")
            
            # Process each page individually
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                cleaned = clean_pdf_text(text)
                
                print(f"\n=== Processing Page {page_num} ===")
                
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
                        print(f"  Added MF: {description[:40]} - {units} units @ ₹{nav}")
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
                        print(f"  Added Equity: {symbol} - {quantity} shares @ ₹{price}")
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
                        print(f"  Added SGB: {isin} - {units} units @ ₹{market_price}")
                    except (ValueError, IndexError) as e:
                        continue
            
            print(f"\nTotal assets extracted: {len(assets)}")
            
    except Exception as e:
        import traceback
        print(f"Error parsing NSDL CAS PDF: {str(e)}")
        traceback.print_exc()
        raise Exception(f"Failed to parse NSDL CAS PDF: {str(e)}")
    
    return assets, transactions


def parse_nsdl_demat_holdings(text: str, statement: Statement, broker_name: str) -> List[Dict]:
    """Parse NSDL Demat Account holdings from CAS text"""
    assets = []
    
    # Find NSDL account info (note: typo "Acount" in PDF)
    # Pattern: ICICI BANK LIMITED followed by NSDL Demat Acount and DP/Client IDs
    nsdl_pattern = r'ICICI BANK LIMITED\s+NSDL Demat Acount.*?DP ID:(\w+)\s+Client ID:(\w+)'
    nsdl_match = re.search(nsdl_pattern, text, re.DOTALL)
    
    if not nsdl_match:
        print("NSDL account info not found")
        return assets
    
    dp_id = nsdl_match.group(1)
    client_id = nsdl_match.group(2)
    account_id = f"{dp_id}-{client_id}"
    print(f"Found NSDL account: {account_id}")
    
    # The NSDL holdings appear before CDSL section
    # Extract text between account info and CDSL section
    nsdl_holdings_pattern = r'NSDL Demat Acount.*?DP ID:\w+\s+Client ID:\w+(.*?)CDSL Demat Acount'
    holdings_match = re.search(nsdl_holdings_pattern, text, re.DOTALL)
    
    if not holdings_match:
        print("NSDL holdings section not found")
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
            print(f"  Added NSDL MF: {fund_name[:30]} - {units} units")
        except ValueError as e:
            print(f"  Skipped invalid MF entry: {e}")
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
            print(f"  Added SGB: {isin} - {units} units")
        except ValueError as e:
            print(f"  Skipped invalid SGB entry: {e}")
            continue
    
    return assets


def parse_cdsl_demat_holdings(text: str, statement: Statement, broker_name: str) -> List[Dict]:
    """Parse CDSL Demat Account holdings from CAS text"""
    assets = []
    
    # Find CDSL account info (note: typo "Acount" in PDF)
    cdsl_pattern = r'CDSL Demat Acount.*?DP ID:\s*(\w+)\s+Client ID:\s*(\w+)'
    cdsl_match = re.search(cdsl_pattern, text, re.DOTALL)
    
    if not cdsl_match:
        print("CDSL account info not found")
        return assets
    
    dp_id = cdsl_match.group(1)
    client_id = cdsl_match.group(2)
    account_id = f"{dp_id}-{client_id}"
    print(f"Found CDSL account: {account_id}")
    
    # Extract CDSL holdings section (from CDSL account to end or next major section)
    cdsl_holdings_pattern = r'CDSL Demat Acount.*?DP ID:\w+\s+Client ID:\w+(.*?)(?:Mutual Fund Folios|Transactions|Notes:)'
    holdings_match = re.search(cdsl_holdings_pattern, text, re.DOTALL)
    
    if not holdings_match:
        print("CDSL holdings section not found")
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
            print(f"  Added CDSL Equity: {symbol} - {quantity} units")
        except ValueError as e:
            print(f"  Skipped invalid equity entry: {e}")
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
            print(f"  Added CDSL MF: {fund_name[:30]} - {units} units")
        except ValueError as e:
            print(f"  Skipped invalid MF entry: {e}")
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
    except:
        return False


def is_icici_direct_mf_format(df: pd.DataFrame) -> bool:
    """Check if CSV is ICICI Direct mutual fund format"""
    try:
        required_columns = ['Fund', 'Scheme', 'Folio', 'Units']
        df_columns = [col.strip() for col in df.columns]
        return all(col in df_columns for col in required_columns)
    except:
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
    
    print(f"\n=== Parsing ICICI Direct Stock Portfolio ===")
    print(f"DataFrame shape: {df.shape}")
    
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
                print(f"Skipping {symbol} - zero quantity")
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
            
            print(f"Processing: {symbol} - {qty} units @ ₹{current_price}")
            
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
            print(f"Error processing row {index}: {str(e)}")
            import traceback
            traceback.print_exc()
            continue
    
    print(f"Parsed {len(assets)} assets from ICICI Direct stock CSV")
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
    
    print(f"\n=== Parsing ICICI Direct Mutual Fund Holdings ===")
    print(f"DataFrame shape: {df.shape}")
    
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
                print(f"Skipping {scheme_name} - zero units")
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
            
            print(f"Processing: {scheme_name[:40]} - {units} units @ ₹{nav}")
            
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
            print(f"Error processing row {index}: {str(e)}")
            import traceback
            traceback.print_exc()
            continue
    
    print(f"Parsed {len(assets)} mutual funds from ICICI Direct CSV")
    return assets, transactions


def extract_account_info_from_excel(file_path: str) -> dict:
    """
    Extract account information from Zerodha Excel file header
    Returns dict with account_id, account_holder_name, etc.
    """
    account_info = {
        'account_id': None,
        'account_holder_name': None,
        'broker_name': 'Zerodha'  # Default for Zerodha files
    }
    
    try:
        # Read first few rows to extract account info
        df_header = pd.read_excel(file_path, sheet_name=0, header=None, nrows=20, engine='openpyxl')
        
        # Look for account ID and name in first rows
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
        
        print(f"Extracted account info: {account_info}")
    except Exception as e:
        print(f"Could not extract account info: {str(e)}")
    
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
            print(f"Found {len(xl_file.sheet_names)} sheets: {xl_file.sheet_names}")
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
                    if any(str(val).strip().lower() == 'symbol' for val in row_values if pd.notna(val)):
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
                    
                    print(f"Sheet '{sheet_name}': Extracted {len(df)} rows")
                    sheets_data.append((sheet_name, df, account_info))
            
            return sheets_data if sheets_data else None
        else:
            # Single sheet file - process as before
            df_raw = pd.read_excel(file_path, engine='openpyxl', header=None)
            
            header_row = None
            for i in range(min(30, len(df_raw))):
                row_values = df_raw.iloc[i].values
                if any(str(val).strip().lower() == 'symbol' for val in row_values if pd.notna(val)):
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
                
                print(f"Extracted {len(df)} rows with columns: {list(df.columns)}")
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
        
        print(f"DataFrame columns: {df_columns_lower}")  # Debug
        
        # Check if at least 4 of the Zerodha columns are present
        matches = sum(1 for col in zerodha_columns if col in df_columns_lower)
        matches_alt = sum(1 for col in zerodha_columns_alt if col in df_columns_lower)
        
        print(f"Zerodha format matches: {matches}, alt matches: {matches_alt}")  # Debug
        
        return matches >= 3 or matches_alt >= 2  # Lowered threshold
    except Exception as e:
        print(f"Error checking Zerodha format: {str(e)}")
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
    
    print(f"\n=== Parsing Zerodha Holdings (Sheet: {sheet_name or 'Unknown'}) ===")
    print(f"Account Info: {account_info}")
    print(f"Starting to parse Zerodha holdings. DataFrame shape: {df.shape}")  # Debug
    
    # Clean column names
    df.columns = df.columns.str.strip()
    
    # Skip empty rows
    df = df.dropna(how='all')
    
    print(f"After cleaning, DataFrame shape: {df.shape}")  # Debug
    print(f"Columns: {list(df.columns)}")  # Debug
    
    # Determine default asset type from sheet name
    default_asset_type = AssetType.STOCK
    if sheet_name:
        sheet_lower = sheet_name.lower()
        if 'mutual' in sheet_lower or 'mf' in sheet_lower:
            # Default to equity mutual fund, user can reclassify later
            default_asset_type = AssetType.EQUITY_MUTUAL_FUND
            print(f"Sheet '{sheet_name}' detected as Mutual Fund sheet (defaulting to Equity MF)")
        elif 'equity' in sheet_lower or 'stock' in sheet_lower:
            default_asset_type = AssetType.STOCK
            print(f"Sheet '{sheet_name}' detected as Equity sheet")
    
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
            
            print(f"Processing symbol: {symbol}")  # Debug
            
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
                print(f"Skipping {symbol} - zero quantity")
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
            
            print(f"  Qty: {qty}, Avg Price: {avg_price}, Current Price: {current_price}")  # Debug
            
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
            print(f"Error processing row {index}: {str(e)}")
            import traceback
            traceback.print_exc()
            continue
    
    print(f"Parsed {len(assets)} assets and {len(transactions)} transactions")  # Debug
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
