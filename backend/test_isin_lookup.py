"""Test ISIN-based mutual fund lookup"""
import sys
sys.path.insert(0, '/Users/debasis/Debasis/personal/Projects/PortAct/backend')

from app.services.price_updater import get_mutual_fund_price

# Test with ISINs from AMFI
test_cases = [
    ("INF760K01EI4", "Canara Robeco Large And Mid Cap - Direct Growth"),
    ("INF174KA1LR0", "Parag Parikh Flexi Cap - Direct Growth"),
    ("INF174K01328", "Kotak Small Cap - Direct Growth"),
]

print("Testing ISIN-based mutual fund price fetching:\n")
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
