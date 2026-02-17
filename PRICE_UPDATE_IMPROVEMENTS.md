# Price Update System Improvements

## Overview
Enhanced the price update system to track failures, provide visual indicators, and allow manual updates and edits.

## Changes Made

### 1. Database Schema Updates

#### Asset Model (`backend/app/models/asset.py`)
Added three new fields to track price update status:
- `price_update_failed` (Boolean): Flag indicating if the last price update failed
- `last_price_update` (DateTime): Timestamp of the last successful price update
- `price_update_error` (Text): Error message from the last failed update

#### Migration
Created migration file: `backend/alembic/versions/add_price_update_tracking.py`
- Adds the three new columns to the `assets` table
- Migration successfully applied to database

### 2. Backend Updates

#### Price Updater Service (`backend/app/services/price_updater.py`)
Enhanced the `update_asset_price()` function to:
- Track success/failure of each price update attempt
- Store error messages when updates fail
- Update `last_price_update` timestamp on successful updates
- Set `price_update_failed` flag and `price_update_error` message on failures
- Provide detailed error messages for different failure scenarios:
  - NSE stock price fetch failures
  - US stock price fetch failures
  - Mutual fund NAV fetch failures
  - Gold price fetch failures
  - Crypto price fetch failures

#### Asset Schema (`backend/app/schemas/asset.py`)
Updated `AssetInDB` schema to include:
- `price_update_failed: bool = False`
- `last_price_update: Optional[datetime] = None`
- `price_update_error: Optional[str] = None`

#### Assets API (`backend/app/api/v1/endpoints/assets.py`)
Added two new endpoints:

1. **Manual Single Asset Price Update**
   - `POST /api/v1/assets/{asset_id}/update-price`
   - Allows users to manually trigger price update for a specific asset
   - Returns updated asset with current price update status

2. **Manual Bulk Price Update**
   - `POST /api/v1/assets/update-all-prices`
   - Triggers price update for all active assets
   - Returns summary with counts of updated/failed assets
   - Includes list of failed assets with error messages

### 3. Frontend Updates

#### Assets Page (`frontend/src/pages/Assets.tsx`)

**New Features:**

1. **Visual Indicators for Price Update Status**
   - ⚠️ Warning icon (yellow) displayed next to current price when update fails
   - ✓ Success icon (green) displayed when price was recently updated
   - Hover over warning icon shows the error message

2. **Manual Price Update Button**
   - Refresh icon button added to each asset row
   - Click to manually trigger price update for that specific asset
   - Shows loading spinner while updating
   - Works for both grouped and individual asset instances

3. **Edit Asset Functionality**
   - Edit icon button added to each asset row
   - Opens dialog to edit:
     - Quantity
     - Purchase Price
     - Current Price
   - Asset name and symbol are read-only (cannot be changed)
   - Shows price update error in dialog if update failed
   - Saves changes via API

4. **Enhanced Action Buttons**
   - Each asset now has three action buttons:
     - 🔄 Refresh (Update price)
     - ✏️ Edit (Edit asset details)
     - 🗑️ Delete (Delete asset)
   - All buttons have tooltips for better UX
   - Buttons are properly disabled during operations

**Updated Interface:**
```typescript
interface Asset {
  // ... existing fields ...
  price_update_failed?: boolean;
  last_price_update?: string;
  price_update_error?: string;
}
```

**New Handler Functions:**
- `handleManualPriceUpdate()`: Triggers manual price update for single asset
- `handleEditAsset()`: Opens edit dialog
- `handleEditDialogClose()`: Closes edit dialog
- `handleEditAssetSubmit()`: Saves asset changes

### 4. User Experience Improvements

#### Visual Feedback
- **Failed Updates**: Assets with failed price updates show a warning icon
- **Successful Updates**: Assets with recent successful updates show a success icon
- **Loading States**: Buttons show loading spinners during operations
- **Error Messages**: Detailed error messages displayed in:
  - Tooltip on warning icon
  - Edit dialog alert box
  - Snackbar notifications

#### Manual Control
- Users can now manually update prices for assets where automatic updates fail
- Users can edit asset details (quantity, prices) directly
- Bulk update option available via "Refresh Prices" button

### 5. Common Issues Addressed

#### SILVERBEES-E and GOLDBEES-E Price Updates
The system now:
1. Attempts to fetch prices using the mutual fund NAV API
2. If fetch fails, marks the asset with `price_update_failed = true`
3. Stores the error message (e.g., "Failed to fetch NAV for SILVERBEES-E")
4. Shows warning icon next to the price
5. Allows user to manually update or edit the price

#### Error Tracking
All price update failures are now:
- Logged in the backend
- Stored in the database
- Displayed to the user
- Actionable (user can manually update)

## Testing

### Backend Testing
```bash
# Run migration
cd backend
alembic upgrade head

# Test price updater
python -m app.services.price_updater
```

### API Testing
```bash
# Manual single asset update
curl -X POST http://localhost:8000/api/v1/assets/{asset_id}/update-price \
  -H "Authorization: Bearer {token}"

# Manual bulk update
curl -X POST http://localhost:8000/api/v1/assets/update-all-prices \
  -H "Authorization: Bearer {token}"
```

### Frontend Testing
1. Navigate to Assets page
2. Look for assets with warning icons (failed updates)
3. Click refresh button to manually update price
4. Click edit button to manually set price
5. Verify visual indicators appear correctly

## Benefits

1. **Transparency**: Users can see which assets have stale/failed price updates
2. **Control**: Users can manually update prices when automatic updates fail
3. **Flexibility**: Users can edit asset details including prices
4. **Debugging**: Error messages help identify why updates fail
5. **Reliability**: System continues to work even when some price sources fail

## Future Enhancements

1. Add automatic retry logic for failed updates
2. Implement alternative price sources as fallbacks
3. Add notification system for persistent failures
4. Create admin dashboard for monitoring price update health
5. Add bulk edit functionality
6. Implement price history tracking

## Files Modified

### Backend
- `backend/app/models/asset.py`
- `backend/app/schemas/asset.py`
- `backend/app/services/price_updater.py`
- `backend/app/api/v1/endpoints/assets.py`
- `backend/alembic/versions/add_price_update_tracking.py` (new)

### Frontend
- `frontend/src/pages/Assets.tsx`

## Migration Status
✅ Database migration successfully applied
✅ All new fields added to assets table
✅ Existing assets have default values (price_update_failed = false)

## Deployment Notes

1. Run database migration before deploying backend changes
2. No breaking changes - backward compatible
3. Frontend changes are additive - no breaking changes
4. Restart backend service after deployment
5. Clear browser cache if frontend changes don't appear

---

**Status**: ✅ Complete and Ready for Production

All features have been implemented and tested. The system now provides comprehensive price update tracking and manual control capabilities.