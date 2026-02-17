"""Test adding HDFC Bank transactions to the database"""
import sys
sys.path.append('/Users/debasis/Debasis/personal/Projects/PortAct/backend')

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from app.models import bank_account, expense, user, crypto_account  # Import all models
from app.models.bank_account import BankAccount, BankName
from app.models.expense import Expense
from app.services.bank_statement_parser import HDFCBankParser
from datetime import datetime

# Test with the actual HDFC Bank statement
file_path = "/Users/debasis/Debasis/personal/Projects/PortAct/statements/bank-statements/Acct_Statement_XXXXXXXX0581_17022026.xls"

print("=" * 80)
print("Testing HDFC Bank Transaction Import")
print("=" * 80)

db = SessionLocal()

try:
    # Extract account number from filename or statement
    # From the test output, we can see the account number is in the statement
    account_number = "01571160000581"  # From the statement
    
    # Check if HDFC Bank account exists
    print(f"\nSearching for HDFC Bank account: {account_number}")
    bank_account = db.query(BankAccount).filter(
        BankAccount.account_number.like(f"%{account_number[-4:]}%"),
        BankAccount.bank_name == BankName.HDFC_BANK
    ).first()
    
    if not bank_account:
        print(f"⚠ HDFC Bank account ending in {account_number[-4:]} not found in database")
        print("\nSearching for any HDFC Bank accounts...")
        hdfc_accounts = db.query(BankAccount).filter(
            BankAccount.bank_name == BankName.HDFC_BANK
        ).all()
        
        if hdfc_accounts:
            print(f"\nFound {len(hdfc_accounts)} HDFC Bank account(s):")
            for acc in hdfc_accounts:
                print(f"  - {acc.bank_name} | Account: {acc.account_number} | ID: {acc.id}")
            
            # Use the first HDFC account
            bank_account = hdfc_accounts[0]
            print(f"\n✓ Using account: {bank_account.account_number}")
        else:
            print("\n✗ No HDFC Bank accounts found in database")
            print("Please create an HDFC Bank account first")
            sys.exit(1)
    else:
        print(f"✓ Found HDFC Bank account: {bank_account.account_number}")
    
    # Parse transactions
    print(f"\nParsing transactions from statement...")
    parser = HDFCBankParser(file_path)
    transactions = parser.parse()
    print(f"✓ Parsed {len(transactions)} transactions")
    
    # Check for existing transactions to avoid duplicates
    print(f"\nChecking for existing transactions...")
    existing_count = db.query(Expense).filter(
        Expense.bank_account_id == bank_account.id
    ).count()
    print(f"  Current transactions in account: {existing_count}")
    
    # Add transactions
    added_count = 0
    skipped_count = 0
    
    print(f"\nAdding transactions to database...")
    for txn in transactions:
        # Check if transaction already exists (by date, amount, and description)
        existing = db.query(Expense).filter(
            Expense.bank_account_id == bank_account.id,
            Expense.transaction_date == txn['transaction_date'],
            Expense.amount == txn['amount'],
            Expense.description == txn['description']
        ).first()
        
        if existing:
            skipped_count += 1
            continue
        
        # Create new expense record
        expense = Expense(
            user_id=bank_account.user_id,
            bank_account_id=bank_account.id,
            transaction_date=txn['transaction_date'],
            description=txn['description'],
            amount=txn['amount'],
            transaction_type=txn['transaction_type'],
            payment_method=txn['payment_method'],
            merchant_name=txn['merchant_name'],
            reference_number=txn['reference_number'],
            balance_after=txn['balance_after']
        )
        db.add(expense)
        added_count += 1
    
    # Commit changes
    db.commit()
    
    print(f"\n✓ Successfully added {added_count} new transactions")
    if skipped_count > 0:
        print(f"  Skipped {skipped_count} duplicate transactions")
    
    # Show final count
    final_count = db.query(Expense).filter(
        Expense.bank_account_id == bank_account.id
    ).count()
    print(f"\n  Total transactions in account: {final_count}")
    
    print("\n" + "=" * 80)
    print("Import Complete!")
    print("=" * 80)
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
    db.rollback()
finally:
    db.close()

# Made with Bob
