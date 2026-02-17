"""Test with correct AMFI names"""
import sys
sys.path.insert(0, '/Users/debasis/Debasis/personal/Projects/PortAct/backend')

from app.services.price_updater import get_mutual_fund_price

# Correct names from AMFI
funds = [
    "CANARA ROBECO LARGE AND MID CAP FUND",
    "Parag Parikh Flexi Cap Fund",
    "Kotak-Small Cap Fund"
]

print("Testing with correct AMFI fund names:\n")
for fund in funds:
    print(f"Testing: {fund}")
    price = get_mutual_fund_price(fund)
    if price:
        print(f"  ✓ NAV: ₹{price}\n")
    else:
        print(f"  ✗ Failed to fetch NAV\n")
