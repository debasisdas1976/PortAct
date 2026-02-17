#!/usr/bin/env python3
"""
Test script to parse bank statement and debug issues
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.bank_statement_parser import ICICIBankParser, IDFCFirstBankParser
import pandas as pd

def test_parse_statement(file_path, parser_class, bank_name):
    print(f"\n{'='*80}")
    print(f"Testing {bank_name} Parser")
    print(f"File: {file_path}")
    print(f"{'='*80}\n")
    
    try:
        # Initialize parser with file path
        parser = parser_class(file_path)
        
        # Parse the statement
        print("Parsing statement...")
        transactions = parser.parse()
        
        print(f"\n✅ Successfully parsed {len(transactions)} transactions\n")
        
        # Analyze transactions
        debits = [t for t in transactions if t['transaction_type'].value == 'debit']
        credits = [t for t in transactions if t['transaction_type'].value == 'credit']
        
        print(f"Transaction Summary:")
        print(f"  Total Transactions: {len(transactions)}")
        print(f"  Debits: {len(debits)}")
        print(f"  Credits: {len(credits)}")
        
        if debits:
            total_debit = sum(t['amount'] for t in debits)
            print(f"  Total Debit Amount: ₹{total_debit:,.2f}")
        
        if credits:
            total_credit = sum(t['amount'] for t in credits)
            print(f"  Total Credit Amount: ₹{total_credit:,.2f}")
        
        # Show first 5 transactions
        print(f"\nFirst 5 Transactions:")
        print("-" * 80)
        for i, txn in enumerate(transactions[:5], 1):
            print(f"\n{i}. Date: {txn['transaction_date']}")
            print(f"   Type: {txn['transaction_type'].value.upper()}")
            print(f"   Amount: ₹{txn['amount']:,.2f}")
            print(f"   Description: {txn['description'][:60]}...")
            if txn.get('balance_after'):
                print(f"   Balance: ₹{txn['balance_after']:,.2f}")
        
        # Show last 5 transactions
        if len(transactions) > 5:
            print(f"\nLast 5 Transactions:")
            print("-" * 80)
            for i, txn in enumerate(transactions[-5:], len(transactions)-4):
                print(f"\n{i}. Date: {txn['transaction_date']}")
                print(f"   Type: {txn['transaction_type'].value.upper()}")
                print(f"   Amount: ₹{txn['amount']:,.2f}")
                print(f"   Description: {txn['description'][:60]}...")
                if txn.get('balance_after'):
                    print(f"   Balance: ₹{txn['balance_after']:,.2f}")
        
        print(f"\n{'='*80}")
        print(f"✅ {bank_name} Parser Test PASSED")
        print(f"{'='*80}\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error parsing statement: {str(e)}")
        import traceback
        traceback.print_exc()
        print(f"\n{'='*80}")
        print(f"❌ {bank_name} Parser Test FAILED")
        print(f"{'='*80}\n")
        return False

if __name__ == "__main__":
    # Test files
    test_cases = [
        {
            "file": "/Users/debasis/Debasis/personal/Projects/PortAct/statements/bank-statements/IDFCFIRSTBankstatement_10054824432.xlsx",
            "parser": IDFCFirstBankParser,
            "bank": "IDFC First Bank (Account 10054824432)"
        },
        {
            "file": "/Users/debasis/Debasis/personal/Projects/PortAct/statements/bank-statements/IDFCFIRSTBankstatement_10059280790.xlsx",
            "parser": IDFCFirstBankParser,
            "bank": "IDFC First Bank (Account 10059280790)"
        }
    ]
    
    results = []
    for test_case in test_cases:
        result = test_parse_statement(
            test_case["file"],
            test_case["parser"],
            test_case["bank"]
        )
        results.append((test_case["bank"], result))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    for bank, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} - {bank}")
    print("="*80 + "\n")

# Made with Bob
