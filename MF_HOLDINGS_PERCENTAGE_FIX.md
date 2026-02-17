# Mutual Fund Holdings Percentage Fix

## Problem
Some mutual funds (like Canara Robeco Large and Mid Cap Fund, Kotak Small Cap Fund) have holdings data in Excel sheets where the percentage values don't include the `%` symbol. This causes the parser to misinterpret the values, resulting in total holdings exceeding 100%.

## Root Cause
Different AMCs format their portfolio disclosure files differently:
- **With % symbol**: "8.5%" - clearly indicates 8.5%
- **Without % symbol**: "8.5" - ambiguous, could mean 8.5% or 0.085 (8.5% in decimal)

The previous parser logic didn't distinguish between these formats, leading to incorrect percentage values.

## Solution Implemented

### 1. Enhanced Parser Logic
Both `consolidated_mf_parser.py` and `mutual_fund_holdings_csv_parser.py` now:

**When % symbol is present** (e.g., "8.5%"):
- Treats the value as already in percentage format
- Only converts if in decimal range (0.085% → 8.5%)

**When % symbol is absent** (e.g., "8.5"):
- Intelligently determines the format:
  - `0 < value < 1`: Decimal format (0.085 → 8.5%)
  - `1 ≤ value ≤ 100`: Percentage format (8.5 → 8.5%)
  - `value > 100`: Basis points format (850 → 8.5%)

### 2. Validation
- Final validation ensures all percentages are between 0 and 100
- Invalid values are logged and skipped

## Files Modified

1. **backend/app/services/consolidated_mf_parser.py**
   - Lines 230-275: Enhanced percentage parsing logic

2. **backend/app/services/mutual_fund_holdings_csv_parser.py**
   - Lines 54-100: Enhanced percentage parsing logic

3. **backend/fix_mf_holdings_percentages.py** (NEW)
   - Script to fix existing incorrect data in database

## How to Fix Existing Data

### Option 1: Run the Fix Script (Recommended)
```bash
cd backend
python fix_mf_holdings_percentages.py
```

This script will:
- Check all equity mutual funds in your portfolio
- Identify funds with total holdings > 150%
- Automatically divide all percentages by 100
- Recalculate holding values
- Show before/after totals

### Option 2: Re-import Holdings
1. Go to Mutual Fund Holdings page
2. Delete holdings for affected funds (Canara Robeco, Kotak Small Cap, etc.)
3. Re-upload the Excel file
4. The new parser will handle it correctly

## Testing

To verify the fix works:

1. **Check total percentages**: All funds should have total holdings ≤ 100%
2. **Spot check individual holdings**: Compare with original factsheet
3. **Test new imports**: Upload a new fund's holdings and verify percentages

## Examples

### Before Fix
```
Canara Robeco Large and Mid Cap Fund:
- Stock A: 850% (should be 8.5%)
- Stock B: 720% (should be 7.2%)
- Total: 5000%+ ❌
```

### After Fix
```
Canara Robeco Large and Mid Cap Fund:
- Stock A: 8.5% ✓
- Stock B: 7.2% ✓
- Total: 95.3% ✓
```

## Future Imports

All future imports will automatically handle:
- ✓ Percentages with % symbol (8.5%)
- ✓ Percentages without % symbol (8.5)
- ✓ Decimal format (0.085)
- ✓ Basis points format (850)

No manual intervention needed!

## Affected Funds

Known funds with this issue:
- Canara Robeco Large and Mid Cap Fund
- Kotak Small Cap Fund
- (Any other fund without % symbols in Excel)

The fix is generic and will work for all funds regardless of format.