# Mutual Fund API Symbol Guide

## Problem
Mutual fund prices were not updating because the fund names in your portfolio don't exactly match the names in the AMFI (Association of Mutual Funds in India) database.

## Solution
Use the **API Symbol** field to specify the exact fund name as it appears in the AMFI database.

---

## How to Find the Correct API Symbol

### Method 1: Use the Search Helper Script

We've created a helper script to search for mutual funds:

```bash
cd backend
source ../.venv/bin/activate
python search_mutual_fund.py "SEARCH TERM"
```

**Examples:**
```bash
# Search for ICICI funds
python search_mutual_fund.py "ICICI BLUECHIP"

# Search for Parag Parikh funds
python search_mutual_fund.py "PARAG PARIKH"

# Search for Kotak Small Cap
python search_mutual_fund.py "KOTAK SMALL CAP"
```

The script will show you:
- All matching funds
- Their current NAV
- The exact **API Symbol to use**

### Method 2: Manual Search

1. Visit: https://www.amfiindia.com/spages/NAVAll.txt
2. Search (Ctrl+F) for your fund name
3. Copy the base fund name (before the first hyphen)

---

## Correct API Symbols for Your Funds

Based on the AMFI database, here are the correct API symbols:

### 1. Canara Robeco Large And Mid Cap Fund
**Your current name:** `Canara Robeco Large And Mid Cap Fund Regular -Growth`  
**Correct API Symbol:** `CANARA ROBECO LARGE AND MID CAP FUND`  
**Current NAV:** ₹287.42 (Direct Plan - Growth)

### 2. Parag Parikh Flexi Cap Fund
**Your current name:** `Parag Parikh Flexi Cap Fund - Growth`  
**Correct API Symbol:** `Parag Parikh Flexi Cap Fund`  
**Current NAV:** ₹92.96 (Direct Plan - Growth)

### 3. Kotak Small Cap Fund
**Your current name:** `KOTAK SMALL CAP FUND - DIRECT PLAN`  
**Correct API Symbol:** `Kotak-Small Cap Fund`  
**Current NAV:** ₹289.29 (Direct - Growth)

---

## How to Update API Symbol in the App

1. **Go to Assets page**
2. **Find the mutual fund** that's not updating
3. **Click the Edit button (✏️)** on that asset
4. **In the "API Symbol" field**, enter the correct name from above
5. **Click Save**
6. **Click the Refresh button (🔄)** on that asset to update the price immediately

---

## Important Notes

### Case Sensitivity
- The search is **case-insensitive**
- You can use any case: `CANARA ROBECO` or `Canara Robeco` or `canara robeco`

### Plan Selection
- The system **automatically prioritizes Growth plans** over Dividend/IDCW plans
- If you have a Direct plan, it will match to Direct Growth
- If you have a Regular plan, it will match to Regular Growth

### Name Matching
- Use the **base fund name** without plan details
- ✅ Correct: `CANARA ROBECO LARGE AND MID CAP FUND`
- ❌ Wrong: `CANARA ROBECO LARGE AND MID CAP FUND - DIRECT PLAN - GROWTH OPTION`

### Common Issues
1. **Extra spaces or hyphens**: The system normalizes these, but use the exact base name for best results
2. **Plan type in name**: Remove "Direct Plan", "Regular Plan", "Growth", "IDCW" from the API symbol
3. **Abbreviations**: Use full names as they appear in AMFI (e.g., "AND" not "&")

---

## Testing Your API Symbol

You can test if an API symbol works before updating:

```bash
cd backend
source ../.venv/bin/activate
python test_specific_mf.py
```

Edit the script to include your fund name and run it.

---

## API Details

**Data Source:** AMFI India  
**URL:** https://www.amfiindia.com/spages/NAVAll.txt  
**Update Frequency:** Daily (after market close)  
**Format:** Semicolon-separated text file  

**Data Structure:**
```
Scheme Code;ISIN1;ISIN2;Scheme Name;NAV;Date
```

---

## Quick Reference Table

| Your Fund Name | Correct API Symbol | Current NAV |
|----------------|-------------------|-------------|
| Canara Robeco Large And Mid Cap Fund Regular -Growth | CANARA ROBECO LARGE AND MID CAP FUND | ₹287.42 |
| Parag Parikh Flexi Cap Fund - Growth | Parag Parikh Flexi Cap Fund | ₹92.96 |
| KOTAK SMALL CAP FUND - DIRECT PLAN | Kotak-Small Cap Fund | ₹289.29 |

---

## Need Help?

If you're still having issues:

1. Use the search helper script to find the exact name
2. Check if the fund exists in AMFI database
3. Verify you're using the base fund name (without plan details)
4. Make sure there are no typos

The system will show error messages in the asset's price update status if there are issues.