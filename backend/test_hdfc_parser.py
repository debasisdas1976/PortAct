import pandas as pd
import sys

# Read the HDFC Bank statement
file_path = "/Users/debasis/Debasis/personal/Projects/PortAct/statements/bank-statements/Acct_Statement_XXXXXXXX0581_17022026.xls"

try:
    # Try reading with xlrd engine
    df = pd.read_excel(file_path, engine='xlrd')
    print("=== HDFC Bank Statement Structure ===")
    print(f"\nShape: {df.shape}")
    print(f"\nColumns: {df.columns.tolist()}")
    print(f"\nFirst 20 rows:")
    print(df.head(20))
    print(f"\nData types:")
    print(df.dtypes)
    print(f"\nSample data:")
    print(df.to_string())
except Exception as e:
    print(f"Error reading file: {e}")
    print("\nTrying to read all sheets...")
    try:
        xls = pd.ExcelFile(file_path, engine='xlrd')
        print(f"Sheet names: {xls.sheet_names}")
        for sheet_name in xls.sheet_names:
            print(f"\n=== Sheet: {sheet_name} ===")
            df = pd.read_excel(xls, sheet_name=sheet_name)
            print(f"Shape: {df.shape}")
            print(f"Columns: {df.columns.tolist()}")
            print(df.head(20))
    except Exception as e2:
        print(f"Error reading sheets: {e2}")

# Made with Bob
