from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.bank_account import BankAccount
from app.models.expense import Expense
from app.services.bank_statement_parser import get_parser
from app.services.expense_categorizer import ExpenseCategorizer
from app.schemas.expense import Expense as ExpenseSchema

router = APIRouter()


@router.post("/upload", response_model=dict)
async def upload_bank_statement(
    file: UploadFile = File(...),
    bank_account_id: int = Form(...),
    auto_categorize: bool = Form(True),
    password: Optional[str] = Form(None),
    portfolio_id: Optional[int] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Upload and process a bank statement
    
    Supports:
    - ICICI Bank (PDF, Excel)
    - HDFC Bank (PDF, Excel)
    - IDFC First Bank (PDF, Excel)
    - State Bank of India (PDF, Excel)
    
    The endpoint will:
    1. Validate the bank account belongs to the user
    2. Save the uploaded file
    3. Parse the statement based on bank type
    4. Auto-categorize expenses (if enabled)
    5. Save transactions to database
    6. Return summary of imported transactions
    """
    
    # Verify bank account belongs to user
    bank_account = db.query(BankAccount).filter(
        BankAccount.id == bank_account_id,
        BankAccount.user_id == current_user.id
    ).first()
    
    if not bank_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bank account not found"
        )
    
    # Validate file type
    allowed_extensions = ['.pdf', '.xlsx', '.xls']
    file_extension = os.path.splitext(file.filename)[1].lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Create upload directory if it doesn't exist
    upload_dir = f"backend/uploads/{current_user.id}/bank_statements"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Save uploaded file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(upload_dir, safe_filename)
    
    try:
        # Save file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Get appropriate parser based on bank and account type
        # For credit cards, use specific credit card parsers
        from app.models.bank_account import BankType
        
        if bank_account.account_type == BankType.CREDIT_CARD:
            # Credit card specific parsers
            bank_name_map = {
                'icici_bank': 'ICICI_CC',
                'scapia': 'SCAPIA_CC',
                'idfc_first_bank': 'IDFC_FIRST_CC',
                # Add more credit card parsers as needed
            }

            # For "OTHER" credit cards, try to detect from file content
            if bank_account.bank_name == 'other':
                # Try to detect bank from PDF content
                if file_extension == '.pdf':
                    try:
                        import PyPDF2
                        with open(file_path, 'rb') as f:
                            pdf_reader = PyPDF2.PdfReader(f)
                            if len(pdf_reader.pages) > 0:
                                first_page_text = pdf_reader.pages[0].extract_text().lower()
                                
                                # Detect Scapia
                                if 'scapia' in first_page_text or 'scapiacoins' in first_page_text:
                                    parser_bank_name = 'SCAPIA_CC'
                                # Detect IDFC First Bank
                                elif 'idfc first' in first_page_text or 'idfc first bank' in first_page_text:
                                    parser_bank_name = 'IDFC_FIRST_CC'
                                # Add more detection logic for other banks here
                                else:
                                    raise HTTPException(
                                        status_code=status.HTTP_400_BAD_REQUEST,
                                        detail="Could not detect credit card bank from statement. Please update bank account to specify the correct bank."
                                    )
                    except Exception as e:
                        logger.error(f"Error detecting bank from statement: {e}")
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="The statement format is not recognized. Please check the file."
                        )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Credit card statement parsing for 'Other' bank is only supported for PDF files"
                    )
            else:
                parser_bank_name = bank_name_map.get(bank_account.bank_name)
        else:
            # Regular bank account parsers
            bank_name_map = {
                'icici_bank': 'ICICI',
                'hdfc_bank': 'HDFC',
                'idfc_first_bank': 'IDFC_FIRST',
                'state_bank_of_india': 'SBI',
                'kotak_mahindra_bank': 'KOTAK',
            }
            parser_bank_name = bank_name_map.get(bank_account.bank_name)

        if not parser_bank_name:
            account_type_str = "credit card" if bank_account.account_type == BankType.CREDIT_CARD else "bank account"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{account_type_str.capitalize()} statement parsing not supported for {bank_account.bank_name}"
            )
        
        # Parse the statement (pass password for encrypted files, e.g. SBI)
        parser = get_parser(parser_bank_name, file_path, password=password)
        transactions = parser.parse()
        
        if not transactions:
            # Update balance from opening balance if the parser extracted one
            opening_balance = getattr(parser, 'opening_balance', None)
            if opening_balance is not None:
                bank_account.current_balance = opening_balance
                db.commit()

            return {
                "success": True,
                "message": "Statement processed — no transactions found in the selected period",
                "summary": {
                    "total_transactions": 0,
                    "imported": 0,
                    "duplicates": 0,
                    "errors": 0,
                    "categorized": 0,
                    "uncategorized": 0
                },
                "file_path": file_path,
                "bank_account": {
                    "id": bank_account.id,
                    "bank_name": bank_account.bank_name,
                    "account_number": bank_account.account_number,
                    "updated_balance": bank_account.current_balance
                }
            }

        # Auto-categorize if enabled
        if auto_categorize:
            categorizer = ExpenseCategorizer(db, user_id=current_user.id)
            transactions = categorizer.bulk_categorize(transactions)
        
        # Save transactions to database
        created_expenses = []
        duplicate_count = 0
        error_count = 0
        
        for txn in transactions:
            try:
                # Check for duplicates (same date, amount, and description)
                existing = db.query(Expense).filter(
                    Expense.user_id == current_user.id,
                    Expense.bank_account_id == bank_account_id,
                    Expense.transaction_date == txn['transaction_date'],
                    Expense.amount == txn['amount'],
                    Expense.description == txn['description']
                ).first()
                
                if existing:
                    duplicate_count += 1
                    continue
                
                # Determine portfolio_id: use provided, fall back to bank account's, then user's default
                expense_portfolio_id = portfolio_id or bank_account.portfolio_id
                if not expense_portfolio_id:
                    from app.models.portfolio import Portfolio
                    default_portfolio = db.query(Portfolio).filter(
                        Portfolio.user_id == current_user.id,
                        Portfolio.is_default == True
                    ).first()
                    if default_portfolio:
                        expense_portfolio_id = default_portfolio.id

                # Create new expense
                expense = Expense(
                    user_id=current_user.id,
                    bank_account_id=bank_account_id,
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
                    is_reconciled=True,  # Mark as reconciled since it's from bank statement
                    portfolio_id=expense_portfolio_id,
                )

                db.add(expense)
                created_expenses.append(expense)

            except Exception as e:
                logger.warning(f"Error processing transaction row: {e}")
                error_count += 1
                continue

        # Commit all transactions
        db.commit()
        
        # Update bank account balance if we have the latest balance
        if transactions and transactions[-1].get('balance_after'):
            bank_account.current_balance = transactions[-1]['balance_after']
            db.commit()
        
        return {
            "success": True,
            "message": "Bank statement processed successfully",
            "summary": {
                "total_transactions": len(transactions),
                "imported": len(created_expenses),
                "duplicates": duplicate_count,
                "errors": error_count,
                "categorized": sum(1 for e in created_expenses if e.category_id is not None),
                "uncategorized": sum(1 for e in created_expenses if e.category_id is None)
            },
            "file_path": file_path,
            "bank_account": {
                "id": bank_account.id,
                "bank_name": bank_account.bank_name,
                "account_number": bank_account.account_number,
                "updated_balance": bank_account.current_balance
            }
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        # Parser error
        logger.error(f"Invalid statement format: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The statement format is not recognized. Please check the file."
        )
    except Exception as e:
        # Clean up file on error
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.error(f"Error processing statement: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process the statement. Please check the file format and try again."
        )


@router.get("/history", response_model=List[dict])
async def get_upload_history(
    bank_account_id: int = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get history of uploaded bank statements
    """
    upload_dir = f"backend/uploads/{current_user.id}/bank_statements"
    
    if not os.path.exists(upload_dir):
        return []
    
    files = []
    for filename in os.listdir(upload_dir):
        file_path = os.path.join(upload_dir, filename)
        if os.path.isfile(file_path):
            stat = os.stat(file_path)
            files.append({
                "filename": filename,
                "upload_date": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "file_size": stat.st_size,
                "file_path": file_path
            })
    
    # Sort by upload date (newest first)
    files.sort(key=lambda x: x['upload_date'], reverse=True)
    
    return files


@router.post("/reprocess/{filename}")
async def reprocess_statement(
    filename: str,
    bank_account_id: int = Form(...),
    auto_categorize: bool = Form(True),
    portfolio_id: Optional[int] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Reprocess a previously uploaded bank statement
    Useful for re-categorizing or fixing import issues
    """
    file_path = f"backend/uploads/{current_user.id}/bank_statements/{filename}"
    
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Statement file not found"
        )
    
    # Verify bank account
    bank_account = db.query(BankAccount).filter(
        BankAccount.id == bank_account_id,
        BankAccount.user_id == current_user.id
    ).first()
    
    if not bank_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bank account not found"
        )
    
    try:
        # Get parser
        bank_name_map = {
            'icici_bank': 'ICICI',
            'hdfc_bank': 'HDFC',
            'idfc_first_bank': 'IDFC_FIRST',
            'state_bank_of_india': 'SBI',
            'kotak_mahindra_bank': 'KOTAK',
        }

        parser_bank_name = bank_name_map.get(bank_account.bank_name)
        if not parser_bank_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bank statement parsing not supported for {bank_account.bank_name}"
            )
        
        # Parse
        parser = get_parser(parser_bank_name, file_path)
        transactions = parser.parse()
        
        # Auto-categorize
        if auto_categorize:
            categorizer = ExpenseCategorizer(db)
            transactions = categorizer.bulk_categorize(transactions)
        
        # Update existing transactions or create new ones
        updated_count = 0
        created_count = 0
        
        for txn in transactions:
            existing = db.query(Expense).filter(
                Expense.user_id == current_user.id,
                Expense.bank_account_id == bank_account_id,
                Expense.transaction_date == txn['transaction_date'],
                Expense.amount == txn['amount'],
                Expense.description == txn['description']
            ).first()
            
            if existing:
                # Update categorization if changed
                if auto_categorize and txn.get('category_id'):
                    existing.category_id = txn['category_id']
                    existing.is_categorized = True
                    updated_count += 1
            else:
                # Determine portfolio_id for reprocessed expenses
                reprocess_portfolio_id = portfolio_id or bank_account.portfolio_id
                if not reprocess_portfolio_id:
                    from app.models.portfolio import Portfolio
                    default_portfolio = db.query(Portfolio).filter(
                        Portfolio.user_id == current_user.id,
                        Portfolio.is_default == True
                    ).first()
                    if default_portfolio:
                        reprocess_portfolio_id = default_portfolio.id

                # Create new expense
                expense = Expense(
                    user_id=current_user.id,
                    bank_account_id=bank_account_id,
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
                    portfolio_id=reprocess_portfolio_id,
                )
                db.add(expense)
                created_count += 1
        
        db.commit()
        
        return {
            "success": True,
            "message": "Statement reprocessed successfully",
            "summary": {
                "total_transactions": len(transactions),
                "updated": updated_count,
                "created": created_count
            }
        }
        
    except Exception as e:
        logger.error(f"Error reprocessing statement: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process the statement. Please check the file format and try again."
        )

# Made with Bob