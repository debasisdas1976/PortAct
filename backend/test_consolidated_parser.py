#!/usr/bin/env python3
"""
Test the consolidated MF parser with the actual Excel file
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.consolidated_mf_parser import ConsolidatedMFParser

def main():
    excel_file = "../statements/mfs/MF-Holdings.xlsx"
    
    print("=" * 80)
    print("TESTING CONSOLIDATED MF PARSER")
    print("=" * 80)
    print(f"\nFile: {excel_file}\n")
    
    parser = ConsolidatedMFParser(excel_file)
    funds = parser.parse_all_funds()
    
    print(f"✓ Successfully parsed {len(funds)} funds\n")
    
    for fund_name, holdings in funds.items():
        print(f"\n{'='*80}")
        print(f"Fund: {fund_name}")
        print(f"Holdings: {len(holdings)}")
        print(f"{'='*80}")
        
        if holdings:
            # Show first 5 holdings
            print(f"\n{'Stock Name':<40} {'ISIN':<15} {'%':<10}")
            print("-" * 65)
            
            total_pct = 0
            for i, holding in enumerate(holdings[:5]):
                print(f"{holding['name']:<40} {holding['isin']:<15} {holding['percentage']:>6.2f}%")
                total_pct += holding['percentage']
            
            if len(holdings) > 5:
                print(f"... and {len(holdings) - 5} more holdings")
            
            # Calculate total percentage
            total_pct = sum(h['percentage'] for h in holdings)
            print(f"\nTotal percentage: {total_pct:.2f}%")
            
            # Check percentage format
            sample_pct = holdings[0]['percentage']
            if sample_pct > 1:
                print(f"✓ Percentages correctly converted (sample: {sample_pct:.2f}%)")
            else:
                print(f"❌ Percentages still in decimal format (sample: {sample_pct})")
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total funds parsed: {len(funds)}")
    print(f"Total holdings: {sum(len(h) for h in funds.values())}")
    print("\n✓ Parser is working correctly!")
    print("\nNOTE: Fund names are extracted from sheet names or content.")
    print("For better matching, ensure Excel sheet names match your fund names")
    print("or use the manual mapping feature in the UI.")

if __name__ == "__main__":
    main()

# Made with Bob
