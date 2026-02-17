#!/usr/bin/env python3
"""
Debug script - simulate exact parser logic
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

import pandas as pd
from datetime import datetime

def _parse_date(date_str: str, formats: list) -> datetime:
    """Try to parse date with multiple formats"""
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None

file_path = "/Users/debasis/Debasis/personal/Projects/PortAct/statements/bank-statements/IDFCFIRSTBankstatement_10054824432.xlsx"

print("Simulating parser logic...")
engine = 'openpyxl'
excel_file = pd.ExcelFile(file_path, engine=engine)

for sheet_name in excel_file.sheet_names:
    print(f"\n{'='*80}")
    print(f"Sheet: {sheet_name}")
    
    df = pd.read_excel(file_path, sheet_name=sheet_name, engine=engine, header=None)
    
    # Look for header row
    header_row = None
    for idx, row in df.iterrows():
        row_str = ' '.join([str(val) for val in row.values if pd.notna(val)])
        if 'Transaction Date' in row_str and 'Particulars' in row_str:
            header_row = idx
            print(f"Found header at row {idx}")
            break
    
    if header_row is None:
        print("No header found")
        continue
    
    # Re-read with skiprows
    df = pd.read_excel(file_path, sheet_name=sheet_name, engine=engine, skiprows=header_row+1, header=None)
    
    if len(df.columns) >= 7:
        df.columns = ['Transaction Date', 'Value Date', 'Particulars', 'Cheque No.', 'Debit', 'Credit', 'Balance']
        print(f"Columns set. Processing {len(df)} rows...")
        
        count = 0
        for idx, row in df.iterrows():
            date_str = str(row.get('Transaction Date', ''))
            description = str(row.get('Particulars', ''))
            
            # Check skip conditions
            if not date_str or date_str == 'nan':
                print(f"Row {idx}: Skipped - no date (date_str='{date_str}')")
                continue
            
            if not description or description == 'nan':
                print(f"Row {idx}: Skipped - no description (desc='{description}')")
                continue
            
            if 'Total' in str(description) or 'End of' in str(description) or 'number of' in str(description).lower():
                print(f"Row {idx}: Skipped - summary row (desc='{description}')")
                continue
            
            # Try to parse date
            transaction_date = _parse_date(date_str, ['%d-%b-%Y', '%d-%B-%Y', '%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'])
            
            if transaction_date:
                count += 1
                print(f"Row {idx}: ✅ VALID - date={transaction_date.date()}, desc={description[:50]}")
            else:
                print(f"Row {idx}: ❌ Date parse failed - date_str='{date_str}'")
        
        print(f"\nTotal valid transactions: {count}")

# Made with Bob
