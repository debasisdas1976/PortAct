"""Test HDFC Bank parser with actual statement"""
import sys
sys.path.append('/Users/debasis/Debasis/personal/Projects/PortAct/backend')

from app.services.bank_statement_parser import HDFCBankParser
from datetime import datetime

# Test with the actual HDFC Bank statement
file_path = "/Users/debasis/Debasis/personal/Projects/PortAct/statements/bank-statements/Acct_Statement_XXXXXXXX0581_17022026.xls"

print("=" * 80)
print("Testing HDFC Bank Parser")
print("=" * 80)

try:
    parser = HDFCBankParser(file_path)
    transactions = parser.parse()
    
    print(f"\n✓ Successfully parsed {len(transactions)} transactions\n")
    
    if transactions:
        print("Sample Transactions:")
        print("-" * 80)
        for i, txn in enumerate(transactions[:5], 1):
            print(f"\nTransaction {i}:")
            print(f"  Date: {txn['transaction_date'].strftime('%Y-%m-%d')}")
            print(f"  Description: {txn['description'][:60]}...")
            print(f"  Amount: ₹{txn['amount']:,.2f}")
            print(f"  Type: {txn['transaction_type']}")
            print(f"  Payment Method: {txn['payment_method']}")
            print(f"  Merchant: {txn['merchant_name']}")
            print(f"  Reference: {txn['reference_number']}")
            print(f"  Balance After: ₹{txn['balance_after']:,.2f}")
        
        if len(transactions) > 5:
            print(f"\n... and {len(transactions) - 5} more transactions")
        
        # Show all transactions summary
        print("\n" + "=" * 80)
        print("All Transactions Summary:")
        print("=" * 80)
        for i, txn in enumerate(transactions, 1):
            print(f"{i}. {txn['transaction_date'].strftime('%d/%m/%y')} | "
                  f"{txn['description'][:40]:40} | "
                  f"₹{txn['amount']:>10,.2f} | "
                  f"{txn['transaction_type'].value:8}")
        
        # Calculate totals
        total_debit = sum(txn['amount'] for txn in transactions if txn['transaction_type'].value == 'DEBIT')
        total_credit = sum(txn['amount'] for txn in transactions if txn['transaction_type'].value == 'CREDIT')
        
        print("\n" + "=" * 80)
        print("Summary:")
        print(f"  Total Transactions: {len(transactions)}")
        print(f"  Total Debits: ₹{total_debit:,.2f}")
        print(f"  Total Credits: ₹{total_credit:,.2f}")
        print(f"  Net: ₹{total_credit - total_debit:,.2f}")
        print("=" * 80)
        
    else:
        print("⚠ No transactions found!")
        
except Exception as e:
    print(f"\n✗ Error parsing statement: {e}")
    import traceback
    traceback.print_exc()

# Made with Bob
