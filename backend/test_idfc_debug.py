#!/usr/bin/env python3
"""
Debug script for IDFC parser
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

import pandas as pd

file_path = "/Users/debasis/Debasis/personal/Projects/PortAct/statements/bank-statements/IDFCFIRSTBankstatement_10054824432.xlsx"

print("Reading Excel file...")
excel_file = pd.ExcelFile(file_path, engine='openpyxl')

print(f"\nSheet names: {excel_file.sheet_names}")

for sheet_name in excel_file.sheet_names:
    print(f"\n{'='*80}")
    print(f"Sheet: {sheet_name}")
    print(f"{'='*80}")
    
    df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')
    
    print(f"\nDataFrame shape: {df.shape}")
    print(f"\nFirst 20 rows:")
    print(df.head(20))
    
    print(f"\nColumn names:")
    print(df.columns.tolist())
    
    # Look for header row
    print(f"\nSearching for header row...")
    for idx, row in df.iterrows():
        row_str = ' '.join([str(val) for val in row.values if pd.notna(val)])
        if 'Transaction Date' in row_str:
            print(f"Found 'Transaction Date' at row {idx}: {row_str[:100]}")
        if 'Particulars' in row_str:
            print(f"Found 'Particulars' at row {idx}: {row_str[:100]}")

# Made with Bob
