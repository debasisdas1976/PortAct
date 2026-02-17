"""Test that api_symbol is used for mutual fund price fetching"""
import sys
sys.path.insert(0, '/Users/debasis/Debasis/personal/Projects/PortAct/backend')

from app.services.price_updater import get_mutual_fund_price

# Test with a known ISIN
isin = "INF204KA1R66"  # ICICI Prudential Bluechip Fund
print(f"Testing mutual fund price fetch with ISIN: {isin}")

price = get_mutual_fund_price(isin)
if price:
    print(f"✓ Successfully fetched NAV: ₹{price}")
else:
    print("✗ Failed to fetch NAV")

# Test with fund name
fund_name = "ICICI PRUDENTIAL BLUECHIP FUND"
print(f"\nTesting mutual fund price fetch with name: {fund_name}")

price2 = get_mutual_fund_price(fund_name)
if price2:
    print(f"✓ Successfully fetched NAV: ₹{price2}")
else:
    print("✗ Failed to fetch NAV")
