"""Test specific mutual fund names"""
import sys
sys.path.insert(0, '/Users/debasis/Debasis/personal/Projects/PortAct/backend')

from app.services.price_updater import get_mutual_fund_price

funds = [
    "Canara Robeco Large And Mid Cap Fund Regular -Growth",
    "Parag Parikh Flexi Cap Fund - Growth",
    "KOTAK SMALL CAP FUND - DIRECT PLAN"
]

print("Testing mutual fund price fetching:\n")
for fund in funds:
    print(f"Testing: {fund}")
    price = get_mutual_fund_price(fund)
    if price:
        print(f"  ✓ NAV: ₹{price}\n")
    else:
        print(f"  ✗ Failed to fetch NAV\n")
        
        # Try with normalized name
        normalized = fund.upper().replace(" - ", " ").replace("- ", " ").replace(" -", " ")
        print(f"  Trying normalized: {normalized}")
        price2 = get_mutual_fund_price(normalized)
        if price2:
            print(f"  ✓ NAV with normalized name: ₹{price2}\n")
        else:
            print(f"  ✗ Still failed\n")
