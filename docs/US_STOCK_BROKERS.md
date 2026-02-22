# US Stock Brokers Integration

This document describes the integration of US stock brokers (Vested and INDMoney) into the PortAct portfolio management system.

## Overview

The system now supports importing US stock holdings from:
- **Vested** - US stock trading platform
- **INDMoney** - Multi-asset investment platform with US stocks

All US stock prices are automatically converted from USD to INR using real-time exchange rates.

## Features

### 1. US Stock Asset Type
- New asset type: `US_STOCK`
- Stores both USD and INR values
- Tracks exchange rate used for conversion
- Displays holdings in INR for portfolio aggregation

### 2. Cash Balance Tracking
- New asset type: `CASH`
- Tracks cash balances in trading accounts
- Converts USD cash to INR
- Separate tracking per broker

### 3. Currency Conversion
- Real-time USD to INR exchange rates
- Fetches from free APIs (exchangerate-api.com, open.er-api.com)
- 1-hour caching to reduce API calls
- Fallback to default rate (₹83/USD) if APIs fail

### 4. Automatic Price Updates
- Exchange rates cached for 1 hour
- Can be manually refreshed if needed
- Historical exchange rate stored with each import

## Supported File Formats

### Vested
- **CSV Format**: Holdings export from Vested platform
- **Excel Format**: .xlsx or .xls files

**Expected Columns:**
- Symbol/Ticker
- Name/Company Name
- Quantity/Shares
- Average Cost/Purchase Price
- Current Price/Market Price
- Market Value/Current Value
- Cash Balance (optional, in separate row)

### INDMoney
- **CSV Format**: US stocks holdings export
- **Excel Format**: .xlsx or .xls files

**Expected Columns:**
- Symbol/Stock Symbol
- Name/Company Name
- Quantity/Units
- Average Price/Buy Price
- Current Price/LTP
- Market Value/Total Value
- Cash Balance (optional, in separate row)

## How to Import

### Step 1: Export Statement from Broker

**Vested:**
1. Log in to Vested app/website
2. Go to Portfolio → Holdings
3. Export as CSV or Excel

**INDMoney:**
1. Log in to INDMoney app/website
2. Go to US Stocks → Portfolio
3. Export holdings

### Step 2: Upload to PortAct

1. Navigate to Statements page
2. Click "Upload Statement"
3. Select statement type:
   - "Vested Statement" for Vested exports
   - "INDMoney Statement" for INDMoney exports
4. Choose your file
5. Click Upload

### Step 3: View Holdings

- Holdings appear in Assets page
- US stocks shown with USD and INR values
- Cash balances shown separately
- All values aggregated in dashboard

## Data Storage

### Asset Details JSON
Each US stock asset stores additional details:

```json
{
  "exchange": "US",
  "currency": "USD",
  "usd_to_inr_rate": 83.25,
  "price_usd": 150.50,
  "avg_cost_usd": 145.00,
  "market_value_usd": 1505.00
}
```

### Cash Balance Details
Cash balances store:

```json
{
  "currency": "USD",
  "usd_to_inr_rate": 83.25,
  "balance_usd": 500.00
}
```

## Currency Conversion Service

### API Sources
1. **Primary**: exchangerate-api.com (free tier)
2. **Fallback**: open.er-api.com
3. **Default**: ₹83/USD if both APIs fail

### Usage in Code

```python
from app.services.currency_converter import get_usd_to_inr_rate, convert_usd_to_inr

# Get current rate
rate = get_usd_to_inr_rate()  # Returns float, e.g., 83.25

# Convert amount
inr_amount = convert_usd_to_inr(100.0)  # Converts $100 to INR
```

### Cache Management
- Rates cached for 1 hour
- Automatic refresh after expiry
- Manual cache clear:

```python
from app.services.currency_converter import CurrencyConverter

CurrencyConverter.clear_cache()
```

## Database Schema

### New Asset Types
```sql
-- Added to AssetType enum
'us_stock'  -- US stocks
'cash'      -- Cash balances
```

### New Statement Types
```sql
-- Added to StatementType enum
'vested_statement'    -- Vested broker statements
'indmoney_statement'  -- INDMoney broker statements
```

## API Endpoints

All existing endpoints support the new asset types:

### Get Assets
```
GET /api/v1/assets/
```
Returns all assets including US stocks and cash balances.

### Upload Statement
```
POST /api/v1/statements/upload
```
**Parameters:**
- `file`: Statement file (CSV/Excel)
- `statement_type`: "vested_statement" or "indmoney_statement"
- `institution_name`: (optional) Broker name

### Get Dashboard
```
GET /api/v1/dashboard/
```
Includes US stocks in portfolio aggregation with INR values.

## Portfolio Aggregation

US stocks are included in:
- **Total Portfolio Value**: Converted to INR
- **Asset Allocation**: Shown as separate category
- **Performance Tracking**: P&L calculated in INR
- **Cash Balances**: Tracked separately

## Example Statement Formats

### Vested CSV Example
```csv
Symbol,Name,Quantity,Average Cost,Current Price,Market Value
AAPL,Apple Inc.,10,145.50,150.25,1502.50
GOOGL,Alphabet Inc.,5,2800.00,2850.00,14250.00
MSFT,Microsoft Corporation,8,380.00,395.50,3164.00
Cash Balance,,,,,500.00
```

### INDMoney CSV Example
```csv
Stock Symbol,Company Name,Quantity,Buy Price,LTP,Total Value
TSLA,Tesla Inc.,3,245.00,255.50,766.50
AMZN,Amazon.com Inc.,2,3200.00,3350.00,6700.00
NVDA,NVIDIA Corporation,15,450.00,485.00,7275.00
Available Cash,,,,,750.00
```

## Troubleshooting

### Issue: Exchange rate not updating
**Solution:** Clear cache and retry:
```python
from app.services.currency_converter import CurrencyConverter
CurrencyConverter.clear_cache()
```

### Issue: Statement parsing fails
**Possible causes:**
1. Incorrect statement type selected
2. File format not matching expected structure
3. Missing required columns

**Solution:**
- Verify statement type matches broker
- Check file has required columns
- Ensure file is not corrupted

### Issue: Cash balance not detected
**Solution:**
- Ensure cash balance row exists in statement
- Check for keywords: "Cash", "Balance", "Available"
- Verify numeric value is present

## Future Enhancements

Planned features:
1. Support for more US brokers (Groww US, etc.)
2. Historical exchange rate tracking
3. Multi-currency support (EUR, GBP, etc.)
4. Automatic price updates for US stocks
5. Transaction history import
6. Dividend tracking

## Technical Details

### Parser Implementation
- **Location**: `backend/app/services/vested_parser.py`, `indmoney_parser.py`
- **Method**: Pandas-based CSV/Excel parsing
- **Flexibility**: Column name matching with multiple variations

### Statement Processor Integration
- **Location**: `backend/app/services/statement_processor.py`
- **Functions**: `process_vested_statement()`, `process_indmoney_statement()`
- **Flow**: Parse → Convert → Store

### Currency Converter
- **Location**: `backend/app/services/currency_converter.py`
- **Class**: `CurrencyConverter`
- **Caching**: In-memory with 1-hour TTL

## Migration

Database migration applied:
```
Revision: 6c64e6666c62
- Added 'us_stock' to AssetType enum
- Added 'cash' to AssetType enum
- Added 'vested_statement' to StatementType enum
- Added 'indmoney_statement' to StatementType enum
```

Run migration:
```bash
cd backend
alembic upgrade head
```

## Support

For issues or questions:
1. Check this documentation
2. Review error messages in statement processing
3. Verify file format matches examples
4. Check backend logs for detailed errors

---

**Made with Bob** - US Stock Broker Integration v1.0