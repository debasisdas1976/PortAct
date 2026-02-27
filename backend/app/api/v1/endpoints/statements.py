from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from sqlalchemy import func as sqla_func
from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.statement import Statement, StatementStatus, StatementType
from app.models.asset import Asset, AssetType
from app.models.bank_account import BankAccount
from app.models.demat_account import DematAccount
from app.models.crypto_account import CryptoAccount
from app.schemas.statement import (
    Statement as StatementSchema,
    StatementUploadResponse,
    PortfolioAccountsResponse,
    AccountGroup,
    AccountItem,
    UploadConfig,
    UnmatchedMF,
    UnmatchedMFSuggestion,
    UnmatchedMFsResponse,
    ResolveMFsRequest,
    ResolveMFsResponse,
)
from app.models.portfolio_snapshot import AssetSnapshot
from app.models.alert import Alert
from app.models.mutual_fund_holding import MutualFundHolding
from app.services.statement_processor import process_statement
import os
import shutil
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[StatementSchema])
async def get_statements(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all statements for the current user
    """
    statements = db.query(Statement).filter(
        Statement.user_id == current_user.id
    ).order_by(Statement.uploaded_at.desc()).all()
    
    return statements


@router.get("/accounts", response_model=PortfolioAccountsResponse)
async def get_portfolio_accounts(
    portfolio_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all accounts for a portfolio grouped by type.
    Each account includes upload configuration for statement uploads.
    """
    groups: List[AccountGroup] = []

    # --- Demat Accounts ---
    demat_query = db.query(DematAccount).filter(
        DematAccount.user_id == current_user.id,
        DematAccount.is_active == True
    )
    if portfolio_id is not None:
        demat_query = demat_query.filter(DematAccount.portfolio_id == portfolio_id)
    demat_accounts = demat_query.order_by(DematAccount.broker_name).all()

    if demat_accounts:
        demat_items = []
        for da in demat_accounts:
            asset_count = db.query(sqla_func.count(Asset.id)).filter(
                Asset.demat_account_id == da.id, Asset.is_active == True
            ).scalar() or 0
            total_value = db.query(sqla_func.coalesce(sqla_func.sum(Asset.current_value), 0)).filter(
                Asset.demat_account_id == da.id, Asset.is_active == True
            ).scalar()

            # Determine statement type based on broker
            broker_lower = (da.broker_name or "").lower()
            if broker_lower == "vested":
                stmt_type = StatementType.VESTED_STATEMENT.value
            elif broker_lower == "indmoney":
                stmt_type = StatementType.INDMONEY_STATEMENT.value
            else:
                stmt_type = StatementType.BROKER_STATEMENT.value

            display = da.nickname or da.broker_name or "Demat Account"
            if da.account_id:
                display += f" ({da.account_id})"
            if da.account_holder_name:
                display += f" — {da.account_holder_name}"

            currency = da.currency or "INR"
            if currency == "USD":
                sub = f"{asset_count} holdings | Value: ${total_value:,.0f}"
            else:
                sub = f"{asset_count} holdings | Value: \u20b9{total_value:,.0f}"

            demat_items.append(AccountItem(
                account_source="demat_account",
                account_id=da.id,
                display_name=display,
                institution_name=da.broker_name,
                sub_info=sub,
                last_statement_date=da.last_statement_date,
                upload_config=UploadConfig(
                    endpoint="/statements/upload",
                    pre_filled={
                        "statement_type": stmt_type,
                        "institution_name": da.broker_name,
                        **({"portfolio_id": da.portfolio_id} if da.portfolio_id else {}),
                    },
                    fields_needed=["file", "password"],
                    accepts=".pdf,.csv,.xlsx,.xls",
                ),
            ))
        groups.append(AccountGroup(
            group_type="demat_accounts",
            display_name="Demat Accounts",
            accounts=demat_items,
        ))

    # --- Bank Accounts ---
    bank_query = db.query(BankAccount).filter(
        BankAccount.user_id == current_user.id,
        BankAccount.is_active == True
    )
    if portfolio_id is not None:
        bank_query = bank_query.filter(BankAccount.portfolio_id == portfolio_id)
    bank_accounts = bank_query.order_by(BankAccount.bank_name).all()

    if bank_accounts:
        bank_items = []
        for ba in bank_accounts:
            acct_type_label = (ba.account_type.value if ba.account_type else "account").replace("_", " ").title()
            display = ba.nickname or f"{ba.bank_name} - {acct_type_label}"
            if ba.account_number:
                display += f" ({ba.account_number})"

            sub = f"Balance: \u20b9{ba.current_balance:,.0f}"

            bank_items.append(AccountItem(
                account_source="bank_account",
                account_id=ba.id,
                display_name=display,
                institution_name=ba.bank_name,
                sub_info=sub,
                last_statement_date=ba.last_statement_date,
                upload_config=UploadConfig(
                    endpoint="/bank-statements/upload",
                    pre_filled={"bank_account_id": ba.id},
                    fields_needed=["file", "password"],
                    accepts=".pdf,.xlsx,.xls",
                ),
            ))
        groups.append(AccountGroup(
            group_type="bank_accounts",
            display_name="Bank Accounts",
            accounts=bank_items,
        ))

    # --- Crypto Accounts (no portfolio filter) ---
    crypto_accounts = db.query(CryptoAccount).filter(
        CryptoAccount.user_id == current_user.id,
        CryptoAccount.is_active == True
    ).order_by(CryptoAccount.exchange_name).all()

    if crypto_accounts:
        crypto_items = []
        for ca in crypto_accounts:
            asset_count = db.query(sqla_func.count(Asset.id)).filter(
                Asset.crypto_account_id == ca.id, Asset.is_active == True
            ).scalar() or 0

            display = ca.nickname or ca.exchange_name or "Crypto Account"
            if ca.account_id:
                display += f" ({ca.account_id})"

            sub = f"{asset_count} assets | Value: ${ca.total_value_usd:,.0f}"

            crypto_items.append(AccountItem(
                account_source="crypto_account",
                account_id=ca.id,
                display_name=display,
                institution_name=ca.exchange_name,
                sub_info=sub,
                last_statement_date=ca.last_sync_date,
                upload_config=UploadConfig(
                    endpoint="/statements/upload",
                    pre_filled={
                        "statement_type": StatementType.CRYPTO_STATEMENT.value,
                        "institution_name": ca.exchange_name,
                    },
                    fields_needed=["file"],
                    accepts=".pdf,.csv,.xlsx,.xls",
                ),
            ))
        groups.append(AccountGroup(
            group_type="crypto_accounts",
            display_name="Crypto Accounts",
            accounts=crypto_items,
        ))

    # --- Asset-based account types (PPF, NPS, PF, SSY, Insurance, Mutual Funds) ---
    asset_type_configs = [
        {
            "asset_type": AssetType.PPF,
            "group_type": "ppf",
            "display_name": "PPF Accounts",
            "endpoint_template": "/ppf/{id}/upload",
            "per_account": True,
            "fields_needed": ["file", "password"],
            "accepts": ".pdf",
        },
        {
            "asset_type": AssetType.NPS,
            "group_type": "nps",
            "display_name": "NPS Accounts",
            "endpoint_template": "/nps/{id}/upload",
            "per_account": True,
            "fields_needed": ["file", "password"],
            "accepts": ".pdf",
        },
        {
            "asset_type": AssetType.PF,
            "group_type": "pf",
            "display_name": "PF/EPF Accounts",
            "endpoint_template": "/pf/upload",
            "per_account": False,
            "fields_needed": ["file", "password"],
            "accepts": ".pdf",
        },
        {
            "asset_type": AssetType.SSY,
            "group_type": "ssy",
            "display_name": "SSY Accounts",
            "endpoint_template": "/ssy/upload",
            "per_account": False,
            "fields_needed": ["file", "password"],
            "accepts": ".pdf",
        },
        {
            "asset_type": AssetType.INSURANCE_POLICY,
            "group_type": "insurance",
            "display_name": "Insurance Policies",
            "endpoint_template": "/statements/upload",
            "per_account": False,
            "statement_type": StatementType.INSURANCE_STATEMENT.value,
            "fields_needed": ["file", "password"],
            "accepts": ".pdf,.xlsx,.xls,.csv",
        },
    ]

    for config in asset_type_configs:
        query = db.query(Asset).filter(
            Asset.user_id == current_user.id,
            Asset.asset_type == config["asset_type"],
            Asset.is_active == True
        )
        if portfolio_id is not None:
            query = query.filter(Asset.portfolio_id == portfolio_id)
        assets = query.order_by(Asset.name).all()

        if not assets:
            continue

        items = []
        for asset in assets:
            display = asset.name or f"{config['display_name']}"
            if asset.broker_name and asset.broker_name.lower() not in display.lower():
                display += f" — {asset.broker_name}"

            sub = f"Value: \u20b9{asset.current_value:,.0f}"

            # Build upload config
            if config["per_account"]:
                endpoint = config["endpoint_template"].replace("{id}", str(asset.id))
                pre_filled = {}
            else:
                endpoint = config["endpoint_template"]
                pre_filled = {}
                if config.get("statement_type"):
                    pre_filled["statement_type"] = config["statement_type"]
                    if asset.broker_name:
                        pre_filled["institution_name"] = asset.broker_name

            items.append(AccountItem(
                account_source="asset",
                account_id=asset.id,
                asset_type=config["asset_type"].value,
                display_name=display,
                institution_name=asset.broker_name,
                sub_info=sub,
                last_statement_date=asset.last_updated,
                upload_config=UploadConfig(
                    endpoint=endpoint,
                    pre_filled=pre_filled,
                    fields_needed=config["fields_needed"],
                    accepts=config["accepts"],
                ),
            ))

        groups.append(AccountGroup(
            group_type=config["group_type"],
            display_name=config["display_name"],
            accounts=items,
        ))

    # --- Mutual Fund Holdings (group by demat account) ---
    mf_query = db.query(Asset).filter(
        Asset.user_id == current_user.id,
        Asset.asset_type.in_([AssetType.EQUITY_MUTUAL_FUND, AssetType.DEBT_MUTUAL_FUND]),
        Asset.is_active == True
    )
    if portfolio_id is not None:
        mf_query = mf_query.filter(Asset.portfolio_id == portfolio_id)
    mf_assets = mf_query.all()

    if mf_assets:
        # Group by broker/demat account for display
        mf_by_source = {}
        for asset in mf_assets:
            key = asset.broker_name or "Unknown"
            if key not in mf_by_source:
                mf_by_source[key] = {"count": 0, "total_value": 0.0, "broker": key}
            mf_by_source[key]["count"] += 1
            mf_by_source[key]["total_value"] += asset.current_value or 0

        mf_items = []
        for key, info in sorted(mf_by_source.items()):
            mf_items.append(AccountItem(
                account_source="mutual_fund",
                account_id=0,
                asset_type="mutual_fund",
                display_name=f"Mutual Funds — {info['broker']}",
                institution_name=info["broker"],
                sub_info=f"{info['count']} funds | Value: \u20b9{info['total_value']:,.0f}",
                upload_config=UploadConfig(
                    endpoint="/statements/upload",
                    pre_filled={
                        "statement_type": StatementType.MUTUAL_FUND_STATEMENT.value,
                        "institution_name": info["broker"],
                    },
                    fields_needed=["file", "password"],
                    accepts=".pdf,.csv,.xlsx,.xls",
                ),
            ))

        if mf_items:
            groups.append(AccountGroup(
                group_type="mutual_funds",
                display_name="Mutual Funds",
                accounts=mf_items,
            ))

    return PortfolioAccountsResponse(groups=groups)


@router.get("/{statement_id}", response_model=StatementSchema)
async def get_statement(
    statement_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific statement by ID
    """
    statement = db.query(Statement).filter(
        Statement.id == statement_id,
        Statement.user_id == current_user.id
    ).first()
    
    if not statement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Statement not found"
        )
    
    return statement


@router.post("/upload", response_model=StatementUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_statement(
    file: UploadFile = File(...),
    statement_type: StatementType = Form(...),
    institution_name: str = Form(None),
    password: str = Form(None),
    portfolio_id: int = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Upload a financial statement for processing
    Optional password parameter for encrypted PDFs (e.g., NSDL CAS)
    """
    from app.core.config import settings
    
    # Validate file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    allowed_extensions = settings.ALLOWED_EXTENSIONS.split(',')
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {settings.ALLOWED_EXTENSIONS}"
        )
    
    # Validate file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    if file_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE / 1024 / 1024}MB"
        )
    
    # Create upload directory if it doesn't exist
    upload_dir = os.path.join(settings.UPLOAD_DIR, str(current_user.id))
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(upload_dir, safe_filename)
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save the uploaded file. Please try again."
        )
    
    # Create statement record
    new_statement = Statement(
        user_id=current_user.id,
        filename=file.filename,
        file_path=file_path,
        file_size=file_size,
        file_type=file.content_type,
        statement_type=statement_type,
        institution_name=institution_name,
        password=password,
        status=StatementStatus.UPLOADED
    )
    
    db.add(new_statement)
    db.commit()
    db.refresh(new_statement)
    
    # Process statement asynchronously (in a real app, use Celery or similar)
    try:
        process_statement(new_statement.id, db, portfolio_id=portfolio_id,
                          expected_institution=institution_name)
    except Exception as e:
        logger.error(f"Error processing statement {new_statement.id}: {e}")
        new_statement.status = StatementStatus.FAILED
        new_statement.error_message = str(e)
        db.commit()
    
    # Refresh to get updated status after processing
    db.refresh(new_statement)

    # Build response message based on processing outcome
    if new_statement.status == StatementStatus.FAILED:
        message = f"Statement uploaded but processing failed: {new_statement.error_message or 'Unknown error'}"
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=message
        )

    # Bank statements produce transactions (not assets)
    is_bank_stmt = statement_type == StatementType.BANK_STATEMENT
    records_found = new_statement.transactions_found if is_bank_stmt else new_statement.assets_found

    if records_found and records_found > 0:
        record_label = "transaction(s)" if is_bank_stmt else "asset(s)"
        # Include import details (e.g. "3 new, 0 duplicate(s) skipped") if available
        import_details = new_statement.error_message if (
            is_bank_stmt and new_statement.status == StatementStatus.PROCESSED
            and new_statement.error_message
        ) else None
        if import_details:
            message = f"Statement processed successfully. {records_found} {record_label} found ({import_details})."
            # Clear the error_message since this isn't actually an error
            new_statement.error_message = None
            db.commit()
            db.refresh(new_statement)
        else:
            message = f"Statement processed successfully. {records_found} {record_label} extracted."
    else:
        message = (
            f"Statement uploaded but no records could be extracted from this {institution_name or ''} "
            f"{statement_type.value.replace('_', ' ')}. "
            "This format may not be supported yet. Please check the file and try again."
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=message
        )

    # Check for orphaned assets (demat/crypto types without an account link)
    SELF_ACCOUNT_TYPES = [
        AssetType.PPF, AssetType.NPS, AssetType.PF, AssetType.SSY,
        AssetType.INSURANCE_POLICY, AssetType.SAVINGS_ACCOUNT,
        AssetType.FIXED_DEPOSIT, AssetType.RECURRING_DEPOSIT,
        AssetType.LAND, AssetType.FARM_LAND, AssetType.HOUSE,
        AssetType.GRATUITY, AssetType.CASH,
    ]
    orphan_count = db.query(Asset).filter(
        Asset.statement_id == new_statement.id,
        Asset.demat_account_id.is_(None),
        Asset.crypto_account_id.is_(None),
        Asset.asset_type.notin_(SELF_ACCOUNT_TYPES),
    ).count()

    # Count MF assets without ISIN (unmatched in AMFI)
    unmatched_mf_count = db.query(Asset).filter(
        Asset.statement_id == new_statement.id,
        Asset.isin.is_(None),
        Asset.asset_type.in_([AssetType.EQUITY_MUTUAL_FUND, AssetType.DEBT_MUTUAL_FUND]),
    ).count()

    return StatementUploadResponse(
        statement_id=new_statement.id,
        filename=file.filename,
        status=new_statement.status.value,
        message=message,
        needs_account_link=orphan_count > 0,
        unmatched_mf_count=unmatched_mf_count,
    )


@router.delete("/{statement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_statement(
    statement_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a statement, its associated file, transactions, and assets
    
    This will:
    1. Delete all assets directly linked to this statement (via statement_id)
    2. Delete all transactions linked to this statement
    3. Delete the statement file from disk
    4. Delete the statement record
    
    Note: Assets are deleted based on their statement_id field, regardless of
    whether they have been reclassified or modified after import.
    """
    from app.models.asset import Asset
    from app.models.transaction import Transaction
    
    statement = db.query(Statement).filter(
        Statement.id == statement_id,
        Statement.user_id == current_user.id
    ).first()
    
    if not statement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Statement not found"
        )
    
    # Collect asset IDs that will be deleted
    asset_ids = [a.id for a in db.query(Asset.id).filter(
        Asset.statement_id == statement_id
    ).all()]

    if asset_ids:
        # Clear FK references that lack ON DELETE CASCADE/SET NULL in the DB
        db.query(Alert).filter(Alert.asset_id.in_(asset_ids)).update(
            {Alert.asset_id: None}, synchronize_session=False
        )
        db.query(AssetSnapshot).filter(AssetSnapshot.asset_id.in_(asset_ids)).update(
            {AssetSnapshot.asset_id: None}, synchronize_session=False
        )
        db.query(MutualFundHolding).filter(MutualFundHolding.asset_id.in_(asset_ids)).delete(
            synchronize_session=False
        )
        db.query(Transaction).filter(Transaction.asset_id.in_(asset_ids)).delete(
            synchronize_session=False
        )
        db.query(Asset).filter(Asset.id.in_(asset_ids)).delete(
            synchronize_session=False
        )

    # Delete all transactions linked to this statement
    db.query(Transaction).filter(
        Transaction.statement_id == statement_id
    ).delete(synchronize_session=False)
    
    # Delete file if it exists
    if os.path.exists(statement.file_path):
        try:
            os.remove(statement.file_path)
        except Exception:
            pass  # Continue even if file deletion fails
    
    # Delete the statement record
    db.delete(statement)
    db.commit()

    return None


@router.get("/{statement_id}/unmatched-mfs", response_model=UnmatchedMFsResponse)
async def get_unmatched_mfs(
    statement_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get unmatched mutual funds for a statement with fuzzy match suggestions.
    Unmatched = MF assets from this statement with isin IS NULL.
    """
    statement = db.query(Statement).filter(
        Statement.id == statement_id,
        Statement.user_id == current_user.id,
    ).first()
    if not statement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Statement not found",
        )

    # Find unmatched MF assets from this statement
    unmatched_assets = db.query(Asset).filter(
        Asset.statement_id == statement_id,
        Asset.user_id == current_user.id,
        Asset.isin.is_(None),
        Asset.asset_type.in_([AssetType.EQUITY_MUTUAL_FUND, AssetType.DEBT_MUTUAL_FUND]),
    ).all()

    from app.services.amfi_fuzzy_match import fuzzy_search_amfi

    results = []
    for asset in unmatched_assets:
        # Use asset name as the primary search query
        suggestions = fuzzy_search_amfi(asset.name, top_n=5)
        results.append(UnmatchedMF(
            asset_id=asset.id,
            asset_name=asset.name,
            asset_symbol=asset.symbol or '',
            asset_type=asset.asset_type.value,
            suggestions=[UnmatchedMFSuggestion(**s) for s in suggestions],
        ))

    return UnmatchedMFsResponse(
        statement_id=statement_id,
        unmatched_count=len(results),
        unmatched_mfs=results,
    )


@router.post("/{statement_id}/resolve-mfs", response_model=ResolveMFsResponse)
async def resolve_unmatched_mfs(
    statement_id: int,
    body: ResolveMFsRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Apply user-selected AMFI scheme matches to unmatched MF assets.
    Updates isin and api_symbol on each asset.
    """
    statement = db.query(Statement).filter(
        Statement.id == statement_id,
        Statement.user_id == current_user.id,
    ).first()
    if not statement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Statement not found",
        )

    resolved = 0
    failed = 0
    errors = []

    for resolution in body.resolutions:
        asset = db.query(Asset).filter(
            Asset.id == resolution.asset_id,
            Asset.user_id == current_user.id,
            Asset.statement_id == statement_id,
        ).first()
        if not asset:
            errors.append(f"Asset {resolution.asset_id} not found")
            failed += 1
            continue

        asset.isin = resolution.selected_isin
        # Extract base fund name for api_symbol (before first " - ")
        api_symbol = resolution.selected_scheme_name.split(' - ')[0].strip()
        asset.api_symbol = api_symbol
        resolved += 1

    db.commit()
    return ResolveMFsResponse(
        resolved_count=resolved,
        failed_count=failed,
        errors=errors,
    )

# Made with Bob
