# End of Day (EOD) Snapshot System

## Overview

The EOD Snapshot System automatically captures daily snapshots of portfolio and asset values to track performance over time. This enables historical performance analysis and trend visualization in the dashboard.

## Features

1. **Automatic Daily Snapshots**: Captures portfolio state every day at 7 PM IST
2. **Missed Snapshot Recovery**: Automatically captures missed snapshots when the application restarts
3. **Portfolio Performance Tracking**: View overall portfolio performance over time
4. **Individual Asset Tracking**: Track performance of specific assets
5. **Flexible Time Periods**: View data for 7 days, 30 days, 90 days, 6 months, or 1 year

## Architecture

### Database Schema

#### portfolio_snapshots Table
Stores daily portfolio-level metrics:
- `id`: Primary key
- `user_id`: Foreign key to users table
- `snapshot_date`: Date of the snapshot
- `total_invested`: Total amount invested
- `total_current_value`: Current portfolio value
- `total_profit_loss`: Absolute profit/loss
- `total_profit_loss_percentage`: Percentage profit/loss
- `total_assets_count`: Number of active assets
- `created_at`: Timestamp of snapshot creation

#### asset_snapshots Table
Stores daily asset-level metrics:
- `id`: Primary key
- `portfolio_snapshot_id`: Foreign key to portfolio_snapshots
- `asset_id`: Foreign key to assets table
- `snapshot_date`: Date of the snapshot
- `asset_type`: Type of asset (for historical reference)
- `asset_name`: Name of asset (for historical reference)
- `asset_symbol`: Symbol of asset (for historical reference)
- `quantity`: Asset quantity
- `purchase_price`: Average purchase price
- `current_price`: Current market price
- `total_invested`: Total invested in this asset
- `current_value`: Current value of this asset
- `profit_loss`: Absolute profit/loss
- `profit_loss_percentage`: Percentage profit/loss
- `created_at`: Timestamp of snapshot creation

### Backend Components

#### Models
- `backend/app/models/portfolio_snapshot.py`: SQLAlchemy models for snapshots
- Updated `backend/app/models/user.py`: Added relationship to portfolio_snapshots

#### Services
- `backend/app/services/eod_snapshot_service.py`: Core EOD snapshot logic
  - `capture_snapshot()`: Captures snapshot for a specific user and date
  - `capture_all_users_snapshots()`: Captures snapshots for all users (scheduled job)
  - `check_and_run_missed_snapshots()`: Recovers missed snapshots on startup

#### Scheduler
- `backend/app/services/scheduler.py`: Updated to include EOD job
  - Runs daily at 7 PM IST (1:30 PM UTC)
  - Checks for missed snapshots on application startup

#### API Endpoints
- `GET /api/v1/dashboard/portfolio-performance?days=30`: Get portfolio performance history
- `GET /api/v1/dashboard/asset-performance/{asset_id}?days=30`: Get asset performance history
- `GET /api/v1/dashboard/assets-list`: Get list of all active assets

### Frontend Components

#### Redux Store
- `frontend/src/store/slices/portfolioSlice.ts`: Updated with new actions
  - `fetchPortfolioPerformance`: Fetch portfolio performance data
  - `fetchAssetPerformance`: Fetch individual asset performance
  - `fetchAssetsList`: Fetch list of assets for selection

#### API Service
- `frontend/src/services/api.ts`: Added new API methods
  - `getPortfolioPerformance(days)`
  - `getAssetPerformance(assetId, days)`
  - `getAssetsList()`

#### UI Components
- `frontend/src/components/charts/PerformanceChart.tsx`: Enhanced chart component
  - Toggle between portfolio and individual asset views
  - Asset selection dropdown
  - Time period selection (7D, 30D, 90D, 6M, 1Y)
  - Dual-line chart showing current value vs invested amount

## Usage

### Viewing Portfolio Performance

1. Navigate to the Dashboard
2. The "Portfolio Performance" section shows historical data
3. Use the toggle buttons to switch between:
   - **Portfolio**: Overall portfolio performance
   - **Individual Asset**: Performance of a specific asset
4. Select time period: 7D, 30D, 90D, 6M, or 1Y
5. For individual assets, select the asset from the dropdown

### Chart Features

- **Blue Line**: Current value over time
- **Orange Line**: Invested amount over time
- **Tooltip**: Hover over any point to see detailed metrics
- **Legend**: Click legend items to show/hide lines

## Scheduling Details

### Daily Snapshot Schedule
- **Time**: 7:00 PM IST (1:30 PM UTC)
- **Frequency**: Once per day
- **Process**:
  1. Fetches all active users
  2. For each user:
     - Gets all active assets
     - Calculates current metrics
     - Creates portfolio snapshot
     - Creates individual asset snapshots
  3. Logs success/failure for each user

### Missed Snapshot Recovery
- **Trigger**: Application startup
- **Process**:
  1. For each user, finds the last snapshot date
  2. Identifies missing dates between last snapshot and yesterday
  3. Captures snapshots for all missed dates
  4. Uses asset values as they were on those dates (if available)

### Handling Application Downtime

If the application is not running at 7 PM:
1. The scheduled job will not run
2. On next startup, the missed snapshot check runs automatically
3. All missed snapshots are captured retroactively
4. Historical data remains complete

## Database Migration

To apply the database changes:

```bash
cd backend
# The migration file is already created
# Run the migration when you restart the application
# Or manually run: alembic upgrade head
```

Migration file: `backend/alembic/versions/f1a2b3c4d5e6_add_portfolio_snapshots_tables.py`

## API Examples

### Get Portfolio Performance (Last 30 Days)
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/v1/dashboard/portfolio-performance?days=30"
```

Response:
```json
{
  "period_days": 30,
  "start_date": "2026-01-18",
  "end_date": "2026-02-17",
  "snapshots": [
    {
      "date": "2026-01-18",
      "total_invested": 100000.00,
      "total_current_value": 105000.00,
      "total_profit_loss": 5000.00,
      "total_profit_loss_percentage": 5.00,
      "total_assets_count": 10
    },
    ...
  ]
}
```

### Get Asset Performance
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/v1/dashboard/asset-performance/123?days=30"
```

Response:
```json
{
  "asset_id": 123,
  "asset_name": "Reliance Industries",
  "asset_type": "stock",
  "asset_symbol": "RELIANCE",
  "period_days": 30,
  "start_date": "2026-01-18",
  "end_date": "2026-02-17",
  "snapshots": [
    {
      "date": "2026-01-18",
      "quantity": 10.0,
      "current_price": 2500.00,
      "total_invested": 24000.00,
      "current_value": 25000.00,
      "profit_loss": 1000.00,
      "profit_loss_percentage": 4.17
    },
    ...
  ]
}
```

## Performance Considerations

1. **Snapshot Size**: Each snapshot stores minimal data (numeric values only)
2. **Query Optimization**: Indexes on `user_id`, `snapshot_date`, and `asset_id`
3. **Data Retention**: Consider implementing data retention policy for old snapshots
4. **Batch Processing**: All users processed in a single transaction per user

## Troubleshooting

### No Data Showing in Charts
- **Cause**: No snapshots have been captured yet
- **Solution**: Wait until 7 PM IST for first snapshot, or manually trigger EOD process

### Missing Historical Data
- **Cause**: Application was down during snapshot time
- **Solution**: Restart application to trigger missed snapshot recovery

### Snapshot Errors in Logs
- **Check**: Database connectivity
- **Check**: Asset price data availability
- **Check**: User permissions

## Future Enhancements

1. **Manual Snapshot Trigger**: Add admin endpoint to manually trigger snapshots
2. **Data Export**: Export historical data to CSV/Excel
3. **Comparison Views**: Compare multiple assets side-by-side
4. **Benchmark Comparison**: Compare portfolio against market indices
5. **Data Retention Policy**: Automatically archive old snapshots
6. **Snapshot Notifications**: Alert users of significant portfolio changes

## Made with Bob