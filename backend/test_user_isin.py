"""Test with the ISIN user actually entered"""
import sys
sys.path.insert(0, '/Users/debasis/Debasis/personal/Projects/PortAct/backend')

from app.services.price_updater import get_mutual_fund_price

# Test with the ISIN the user entered
test_cases = [
    ("INF879O01019", "Parag Parikh Flexi Cap - User's ISIN"),
    ("INF174K01DX2", "Kotak Small Cap - Direct Growth (correct ISIN)"),
]

print("Testing with user-provided ISINs:\n")
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
