"""Test with actual ISINs user entered"""
import sys
sys.path.insert(0, '/Users/debasis/Debasis/personal/Projects/PortAct/backend')

from app.services.price_updater import get_mutual_fund_price

# Test with the actual ISINs the user entered
test_cases = [
    ("INF760K01EI4", "Canara Robeco Large And Mid Cap"),
    ("INF879O01019", "Parag Parikh Flexi Cap"),
    ("INF174K01KT2", "Kotak Small Cap"),
]

print("Testing with actual ISINs user entered:\n")
for isin, name in test_cases:
    print(f"Testing: {name}")
    print(f"ISIN: {isin}")
    result = get_mutual_fund_price(isin)
    if result and result[0]:
        nav, fetched_isin = result
        print(f"  ✓ NAV: ₹{nav}")
        print(f"  ✓ ISIN returned: {fetched_isin}\n")
    else:
        print(f"  ✗ Failed to fetch NAV\n")
