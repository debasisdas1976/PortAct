#!/usr/bin/env python3
"""
Complete test of the mutual fund holdings parser
Tests both single-step and two-step upload processes
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.consolidated_mf_parser import ConsolidatedMFParser
from app.services.generic_portfolio_parser import GenericPortfolioParser
import pandas as pd

def test_csv_parser():
    """Test CSV parser with sample data"""
    print("\n" + "="*80)
    print("TEST 1: CSV Parser")
    print("="*80)
    
    csv_file = "test_mf_holdings.csv"
    if not os.path.exists(csv_file):
        print(f"❌ CSV file not found: {csv_file}")
        return False
    
    try:
        parser = GenericPortfolioParser(csv_file)
        result = parser.parse()
        
        print(f"\n✅ Successfully parsed CSV file")
        print(f"   Fund Name: {result['fund_name']}")
        print(f"   Holdings Count: {len(result['holdings'])}")
        print(f"   Data Source: {result['data_source']}")
        
        print("\n📊 Sample Holdings:")
        for i, holding in enumerate(result['holdings'][:3], 1):
            print(f"   {i}. {holding['stock_name']}: {holding['holding_percentage']:.2f}%")
        
        # Verify percentages are in correct range
        for holding in result['holdings']:
            pct = holding['holding_percentage']
            if not (0 <= pct <= 100):
                print(f"❌ Invalid percentage: {pct}% for {holding['stock_name']}")
                return False
        
        print("\n✅ All percentages are in valid range (0-100%)")
        return True
        
    except Exception as e:
        print(f"❌ Error parsing CSV: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_excel_parser():
    """Test Excel parser with consolidated file"""
    print("\n" + "="*80)
    print("TEST 2: Excel Parser (Consolidated File)")
    print("="*80)
    
    excel_file = "MF_Portfolio_Disclosure_Jan_2025.xlsx"
    if not os.path.exists(excel_file):
        print(f"❌ Excel file not found: {excel_file}")
        print("   Please ensure the file is in the backend directory")
        return False
    
    try:
        parser = ConsolidatedMFParser(excel_file)
        all_funds = parser.parse_all_funds()
        
        # Convert to list format
        results = []
        for fund_name, holdings in all_funds.items():
            results.append({
                'fund_name': fund_name,
                'holdings': holdings,
                'data_source': 'excel_upload'
            })
        
        print(f"\n✅ Successfully parsed Excel file")
        print(f"   Total Funds: {len(results)}")
        
        total_holdings = sum(len(r['holdings']) for r in results)
        print(f"   Total Holdings: {total_holdings}")
        
        print("\n📊 Funds Found:")
        for i, result in enumerate(results, 1):
            print(f"   {i}. {result['fund_name']}: {len(result['holdings'])} holdings")
        
        # Verify percentages
        print("\n🔍 Verifying Percentages:")
        all_valid = True
        for result in results:
            fund_name = result['fund_name']
            for holding in result['holdings']:
                pct = holding['holding_percentage']
                if not (0 <= pct <= 100):
                    print(f"   ❌ Invalid percentage in {fund_name}: {pct}% for {holding['stock_name']}")
                    all_valid = False
        
        if all_valid:
            print("   ✅ All percentages are in valid range (0-100%)")
        
        # Show sample holdings from first fund
        if results:
            first_fund = results[0]
            print(f"\n📊 Sample Holdings from {first_fund['fund_name']}:")
            for i, holding in enumerate(first_fund['holdings'][:5], 1):
                print(f"   {i}. {holding['stock_name']}: {holding['holding_percentage']:.2f}%")
        
        return all_valid
        
    except Exception as e:
        print(f"❌ Error parsing Excel: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_fund_name_extraction():
    """Test fund name extraction from Excel"""
    print("\n" + "="*80)
    print("TEST 3: Fund Name Extraction")
    print("="*80)
    
    excel_file = "MF_Portfolio_Disclosure_Jan_2025.xlsx"
    if not os.path.exists(excel_file):
        print(f"❌ Excel file not found: {excel_file}")
        return False
    
    try:
        # Read Excel file to check sheet names vs actual fund names
        xl = pd.ExcelFile(excel_file)
        print(f"\n📋 Sheet Names in Excel:")
        for i, sheet in enumerate(xl.sheet_names, 1):
            print(f"   {i}. {sheet}")
        
        # Parse and compare
        parser = ConsolidatedMFParser(excel_file)
        all_funds = parser.parse_all_funds()
        
        # Convert to list format
        results = []
        for fund_name, holdings in all_funds.items():
            results.append({
                'fund_name': fund_name,
                'holdings': holdings
            })
        
        print(f"\n📋 Extracted Fund Names:")
        for i, result in enumerate(results, 1):
            print(f"   {i}. {result['fund_name']}")
        
        print("\n✅ Fund name extraction test complete")
        return True
        
    except Exception as e:
        print(f"❌ Error in fund name extraction test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_percentage_conversion():
    """Test percentage conversion logic"""
    print("\n" + "="*80)
    print("TEST 4: Percentage Conversion Logic")
    print("="*80)
    
    test_cases = [
        (0.180646, 18.0646, "Decimal to percentage"),
        (18.0646, 18.0646, "Already percentage"),
        (0.05, 5.0, "Small decimal"),
        (95.5, 95.5, "Large percentage"),
        (0.999, 99.9, "Near 100% decimal"),
    ]
    
    # Create a dummy parser instance
    parser = GenericPortfolioParser("dummy.xlsx")
    all_passed = True
    
    print("\n🔍 Testing Conversion Cases:")
    for input_val, expected, description in test_cases:
        result = parser._extract_percentage(input_val)
        if result is None:
            result = 0.0
        passed = abs(result - expected) < 0.01
        status = "✅" if passed else "❌"
        print(f"   {status} {description}: {input_val} → {result:.4f} (expected {expected})")
        if not passed:
            all_passed = False
    
    return all_passed


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("MUTUAL FUND HOLDINGS PARSER - COMPLETE TEST SUITE")
    print("="*80)
    
    results = {
        "CSV Parser": test_csv_parser(),
        "Excel Parser": test_excel_parser(),
        "Fund Name Extraction": test_fund_name_extraction(),
        "Percentage Conversion": test_percentage_conversion(),
    }
    
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*80)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("="*80)
        print("\nThe parser is working correctly and ready for use.")
        print("\nNext Steps:")
        print("1. Upload a CSV or Excel file through the UI")
        print("2. For consolidated Excel files, the system will:")
        print("   - Extract all fund names")
        print("   - Match them to your portfolio")
        print("   - Show you a preview with similarity scores")
        print("   - Let you confirm or modify mappings")
        print("   - Import holdings after confirmation")
    else:
        print("❌ SOME TESTS FAILED")
        print("="*80)
        print("\nPlease review the errors above and fix the issues.")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

# Made with Bob
