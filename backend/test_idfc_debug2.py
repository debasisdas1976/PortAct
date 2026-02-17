#!/usr/bin/env python3
"""
Debug script for IDFC parser - test the actual parsing logic
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

import pandas as pd

file_path = "/Users/debasis/Debasis/personal/Projects/PortAct/statements/bank-statements/IDFCFIRSTBankstatement_10054824432.xlsx"

print("Reading Excel file...")
engine = 'openpyxl'
excel_file = pd.ExcelFile(file_path, engine=engine)

for sheet_name in excel_file.sheet_names:
    print(f"\n{'='*80}")
    print(f"Sheet: {sheet_name}")
    print(f"{'='*80}")
    
    df = pd.read_excel(file_path, sheet_name=sheet_name, engine=engine, header=None)
    
    # Look for the header row
    header_row = None
    for idx, row in df.iterrows():
        row_str = ' '.join([str(val) for val in row.values if pd.notna(val)])
        if 'Transaction Date' in row_str and 'Particulars' in row_str:
            header_row = idx
            print(f"Found header at row {idx}")
            break
    
    if header_row is None:
        print("No header found, skipping sheet")
        continue
    
    # Re-read with correct header - skip rows before header
    df = pd.read_excel(file_path, sheet_name=sheet_name, engine=engine, skiprows=header_row+1, header=None)
    
    print(f"\nDataFrame shape after skiprows: {df.shape}")
    print(f"\nFirst 10 rows:")
    print(df.head(10))
    
    # Manually set column names
    if len(df.columns) >= 7:
        df.columns = ['Transaction Date', 'Value Date', 'Particulars', 'Cheque No.', 'Debit', 'Credit', 'Balance']
        print(f"\nColumn names set successfully")
        print(f"\nFirst 10 rows with column names:")
        print(df.head(10))
        
        print(f"\nChecking each row:")
        for idx, row in df.head(10).iterrows():
            date_str = str(row.get('Transaction Date', ''))
            description = str(row.get('Particulars', ''))
            print(f"Row {idx}: date='{date_str}', desc='{description}'")
    else:
        print(f"Not enough columns: {len(df.columns)}")

# Made with Bob
