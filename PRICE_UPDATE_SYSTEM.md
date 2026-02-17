# Price Update System Documentation

## Overview
The PortAct application includes an automated price update system that runs every 30 minutes to fetch the latest prices for all assets in your portfolio.

## Features

### 1. **Automated Background Updates**
- Runs automatically every 30 minutes
- Updates prices for stocks, mutual funds, and commodities
- Starts automatically when the backend server starts

### 2. **Manual Price Updates**
You can trigger price updates manually via API:
```bash
POST /api/v1/prices/update
```

### 3. **Price Update Status**
Check the status of the price update service:
```bash
GET /api/v1/prices/status
```

## Supported Asset Types

### Stocks (NSE India)
- **API**: NSE India Official API
- **Coverage**: All NSE-listed stocks
- **Update Frequency**: Every 30 minutes
- **Success Rate**: ~90% (depends on market hours)

**Example**: SUZLON, ITC, HDFCBANK, etc.

### Mutual Funds
- **API**: AMFI India NAV API
- **Coverage**: All AMFI-registered mutual funds
- **Update Frequency**: Every 30 minutes
- **Note**: NAV is updated once daily by fund houses

**Example**: Parag Parikh Flexi Cap, Axis Large Cap, etc.

### Commodities (Gold/Silver)
- **API**: Metals.live API
- **Coverage**: Gold and Silver prices
- **Update Frequency**: Every 30 minutes
- **Note**: Prices are in INR per gram

**Example**: GOLDBEES, SILVERBEES, Gold ETFs

## How It Works

### 1. **Price Fetching**
The system uses multiple free APIs to fetch prices:

```python
# For NSE Stocks
https://www.nseindia.com/api/quote-equity?symbol={SYMBOL}

# For Mutual Funds
https://www.amfiindia.com/spages/NAVAll.txt

# For Gold/Silver
https://api.metals.live/v1/spot/gold
```

### 2. **Price Update Process**
1. Fetch all active assets from database
2. For each asset, determine its type
3. Call appropriate API to get current price
4. Update `current_price` and `current_value` in database
5. Recalculate profit/loss metrics

### 3. **Error Handling**
- Failed updates are logged but don't stop the process
- Assets with failed updates retain their previous prices
- Retry on next scheduled update (30 minutes)

## Configuration

### Scheduler Settings
Located in `backend/app/services/scheduler.py`:

```python
# Change update frequency (default: 30 minutes)
scheduler.add_job(
    func=update_all_prices,
    trigger=IntervalTrigger(minutes=30),  # Change this value
    id='price_update_job',
    name='Update asset prices',
    replace_existing=True
)
```

### API Timeouts
Located in `backend/app/services/price_updater.py`:

```python
response = requests.get(url, headers=headers, timeout=10)  # 10 seconds timeout
```

## Testing

### Manual Test
Run price update manually from command line:

```bash
cd backend
source ../.venv/bin/activate
python -c "from app.services.price_updater import update_all_prices; update_all_prices()"
```

### API Test
Trigger update via API:

```bash
curl -X POST "http://localhost:8000/api/v1/prices/update" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Check Status
```bash
curl "http://localhost:8000/api/v1/prices/status" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Logs

Price update logs are available in:
- **Console**: When running in development mode
- **Backend Log**: `backend.log` file

Example log output:
```
INFO:app.services.price_updater:Starting price update for all assets...
INFO:app.services.price_updater:Updated price for SUZLON: ₹45.70
INFO:app.services.price_updater:Updated price for ITC: ₹313.60
WARNING:app.services.price_updater:Could not fetch price for XYZ (AssetType.STOCK)
INFO:app.services.price_updater:Price update complete. Updated: 20, Failed: 5
```

## Limitations

### 1. **Market Hours**
- NSE API works best during market hours (9:15 AM - 3:30 PM IST)
- Outside market hours, prices may not update

### 2. **API Rate Limits**
- NSE API: No official rate limit, but use responsibly
- AMFI API: No rate limit
- Metals.live: Free tier has rate limits

### 3. **Data Accuracy**
- Prices are fetched from public APIs
- Small delays (1-2 minutes) are normal
- NAV for mutual funds updates once daily

## Troubleshooting

### Issue: Prices not updating
**Solution**: 
1. Check if scheduler is running: `GET /api/v1/prices/status`
2. Check backend logs for errors
3. Verify internet connectivity
4. Try manual update: `POST /api/v1/prices/update`

### Issue: Some assets not updating
**Solution**:
1. Verify asset symbol is correct (NSE symbol for stocks)
2. Check if asset is actively traded
3. For mutual funds, ensure ISIN is correct

### Issue: Scheduler not starting
**Solution**:
1. Check if APScheduler is installed: `pip install apscheduler`
2. Restart backend server
3. Check for errors in startup logs

## Future Enhancements

1. **Additional APIs**
   - BSE India for stocks
   - Yahoo Finance as fallback
   - Cryptocurrency APIs

2. **Smart Updates**
   - Update only during market hours
   - Different frequencies for different asset types
   - Batch updates for better performance

3. **Notifications**
   - Alert on significant price changes
   - Daily price update summary
   - Failed update notifications

## Dependencies

```
apscheduler==3.10.4
requests>=2.31.0
```

## Made with Bob