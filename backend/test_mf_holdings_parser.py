#!/usr/bin/env python3
"""
Test script for mutual fund holdings parser
Tests both CSV and Excel parsing functionality
"""
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.mutual_fund_holdings_csv_parser import MutualFundHoldingsCSVParser
from app.services.generic_portfolio_parser import GenericPortfolioParser
import pandas as pd


def test_csv_parser():
    """Test CSV parser with sample file"""
    print("=" * 80)
    print("TESTING CSV PARSER")
    print("=" * 80)
    
    csv_file = "test_mf_holdings.csv"
    
    if not os.path.exists(csv_file):
        print(f"❌ CSV file not found: {csv_file}")
        return False
    
    try:
        # Read file as bytes
        with open(csv_file, 'rb') as f:
            content = f.read()
        
        print(f"\n✓ Reading file: {csv_file}")
        print(f"  File size: {len(content)} bytes")
        
        # Parse CSV
        print("\n📊 Parsing CSV...")
        holdings = MutualFundHoldingsCSVParser.parse_csv(content)
        
        print(f"\n✓ Successfully parsed {len(holdings)} holdings")
        
        # Display holdings
        if holdings:
            print("\n" + "=" * 80)
            print(f"{'Stock Name':<40} {'Symbol':<10} {'ISIN':<15} {'%':<8}")
            print("=" * 80)
            
            for holding in holdings:
                print(f"{holding['stock_name']:<40} "
                      f"{holding.get('stock_symbol', 'N/A'):<10} "
                      f"{holding.get('isin', 'N/A'):<15} "
                      f"{holding['holding_percentage']:>6.2f}%")
            
            print("=" * 80)
            
            # Validate
            is_valid, message = MutualFundHoldingsCSVParser.validate_holdings(holdings)
            print(f"\n{'✓' if is_valid else '❌'} Validation: {message}")
            
            return is_valid
        else:
            print("❌ No holdings found")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_excel_parser():
    """Test Excel parser with MF-Holdings.xlsx"""
    print("\n\n" + "=" * 80)
    print("TESTING EXCEL PARSER")
    print("=" * 80)
    
    excel_file = "../statements/mfs/MF-Holdings.xlsx"
    
    if not os.path.exists(excel_file):
        print(f"❌ Excel file not found: {excel_file}")
        return False
    
    try:
        print(f"\n✓ Reading file: {excel_file}")
        
        # First, let's inspect the Excel file structure
        print("\n📋 Inspecting Excel file structure...")
        
        try:
            xls = pd.ExcelFile(excel_file, engine='openpyxl')
            print(f"  Engine: openpyxl")
        except Exception as e:
            print(f"  openpyxl failed: {e}")
            try:
                xls = pd.ExcelFile(excel_file, engine='xlrd')
                print(f"  Engine: xlrd")
            except Exception as e2:
                print(f"  xlrd also failed: {e2}")
                return False
        
        print(f"  Sheets: {xls.sheet_names}")
        
        # Read first sheet to inspect structure
        df = pd.read_excel(excel_file, sheet_name=0)
        print(f"  Rows: {len(df)}")
        print(f"  Columns: {len(df.columns)}")
        
        print("\n📊 First 20 rows of data:")
        print("=" * 80)
        for idx in range(min(20, len(df))):
            row_data = []
            for val in df.iloc[idx].values:
                if pd.notna(val):
                    row_data.append(str(val)[:30])
            if row_data:
                print(f"Row {idx:2d}: {' | '.join(row_data)}")
        print("=" * 80)
        
        # Now try to parse with generic parser
        print("\n📊 Parsing with GenericPortfolioParser...")
        parser = GenericPortfolioParser(excel_file)
        holdings = parser.parse()
        
        if holdings:
            print(f"\n✓ Successfully parsed {len(holdings)} holdings")
            
            # Display holdings
            print("\n" + "=" * 80)
            print(f"{'Stock Name':<40} {'ISIN':<15} {'Industry':<25} {'%':<8}")
            print("=" * 80)
            
            total_pct = 0
            for holding in holdings[:30]:  # Show first 30
                print(f"{holding['name']:<40} "
                      f"{holding.get('isin', 'N/A'):<15} "
                      f"{holding.get('industry', 'N/A'):<25} "
                      f"{holding['percentage']:>6.2f}%")
                total_pct += holding['percentage']
            
            if len(holdings) > 30:
                print(f"... and {len(holdings) - 30} more holdings")
            
            print("=" * 80)
            print(f"Total percentage: {total_pct:.2f}%")
            
            return True
        else:
            print("❌ No holdings found")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("MUTUAL FUND HOLDINGS PARSER TEST SUITE")
    print("=" * 80)
    
    results = {
        'CSV Parser': test_csv_parser(),
        'Excel Parser': test_excel_parser()
    }
    
    print("\n\n" + "=" * 80)
    print("TEST RESULTS SUMMARY")
    print("=" * 80)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"{test_name:<30} {status}")
    
    print("=" * 80)
    
    all_passed = all(results.values())
    if all_passed:
        print("\n✓ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

# Made with Bob
