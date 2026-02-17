#!/usr/bin/env python3
"""
Helper script to search for mutual fund names in AMFI database
Usage: python search_mutual_fund.py "search term"
"""
import sys
import requests

def search_mutual_fund(search_term):
    """Search for mutual fund in AMFI database"""
    try:
        url = "https://www.amfiindia.com/spages/NAVAll.txt"
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            print(f"Error: Failed to fetch AMFI data (status code: {response.status_code})")
            return
        
        search_upper = search_term.upper()
        matches = []
        
        for line in response.text.split('\n'):
            if search_upper in line.upper():
                parts = line.split(';')
                if len(parts) >= 6:
                    scheme_code = parts[0]
                    isin1 = parts[1]
                    isin2 = parts[2]
                    scheme_name = parts[3]
                    nav = parts[4]
                    date = parts[5] if len(parts) > 5 else ''
                    
                    matches.append({
                        'name': scheme_name,
                        'nav': nav,
                        'isin1': isin1,
                        'isin2': isin2,
                        'code': scheme_code,
                        'date': date
                    })
        
        if not matches:
            print(f"No mutual funds found matching '{search_term}'")
            print("\nTips:")
            print("- Try searching with just the AMC name (e.g., 'ICICI', 'HDFC', 'SBI')")
            print("- Try searching with fund type (e.g., 'BLUECHIP', 'SMALL CAP', 'FLEXI')")
            print("- Remove plan type and growth/dividend options from search")
            return
        
        print(f"\nFound {len(matches)} matching funds for '{search_term}':\n")
        print("=" * 100)
        
        # Group by base fund name (without plan/option details)
        grouped = {}
        for match in matches:
            # Extract base name (before first hyphen or "Direct"/"Regular")
            base_name = match['name'].split(' - ')[0].strip()
            if base_name not in grouped:
                grouped[base_name] = []
            grouped[base_name].append(match)
        
        for base_name, funds in grouped.items():
            print(f"\n📊 {base_name}")
            print("-" * 100)
            
            # Show Direct Growth first if available
            direct_growth = [f for f in funds if 'DIRECT' in f['name'].upper() and 'GROWTH' in f['name'].upper()]
            regular_growth = [f for f in funds if 'REGULAR' in f['name'].upper() and 'GROWTH' in f['name'].upper()]
            others = [f for f in funds if f not in direct_growth and f not in regular_growth]
            
            for fund_list, label in [(direct_growth, "Direct - Growth"), (regular_growth, "Regular - Growth"), (others, "Other Plans")]:
                if fund_list:
                    if label != "Other Plans" or len(fund_list) <= 3:
                        for fund in fund_list[:3]:  # Show max 3 per category
                            print(f"  • {fund['name']}")
                            print(f"    NAV: ₹{fund['nav']} | ISIN: {fund['isin1'] or fund['isin2']}")
                            print(f"    API Symbol to use: \"{fund['name'].split(' - ')[0].strip()}\"")
                            print()
        
        print("=" * 100)
        print("\n💡 Usage Tips:")
        print("1. Copy the 'API Symbol to use' value (the base fund name)")
        print("2. Paste it in the 'API Symbol' field when editing the asset")
        print("3. The system will automatically match to the appropriate plan (prioritizes Growth plans)")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python search_mutual_fund.py \"search term\"")
        print("\nExamples:")
        print("  python search_mutual_fund.py \"ICICI BLUECHIP\"")
        print("  python search_mutual_fund.py \"PARAG PARIKH\"")
        print("  python search_mutual_fund.py \"KOTAK SMALL CAP\"")
        sys.exit(1)
    
    search_term = " ".join(sys.argv[1:])
    search_mutual_fund(search_term)

# Made with Bob
