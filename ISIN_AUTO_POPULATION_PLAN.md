# ISIN Auto-Population Implementation Plan

## Overview
Automatically populate ISIN and API Symbol fields when creating assets from statements, and highlight assets without ISIN in the UI.

## Current Status
✅ ISIN field added to Asset model
✅ Database migration applied
✅ ISIN lookup service created (`backend/app/services/isin_lookup.py`)
✅ Price updater uses ISIN for searches
✅ Frontend allows editing ISIN

## Implementation Plan

### Phase 1: Backend - ISIN Lookup Service ✅
**File:** `backend/app/services/isin_lookup.py`

**Functions:**
- `get_isin_from_nse(symbol)` - Fetch ISIN from NSE for stocks
- `get_isin_from_amfi(fund_name)` - Fetch ISIN from AMFI for mutual funds
- `lookup_isin_for_asset(asset_type, symbol, name)` - Main lookup function

**Status:** ✅ Created and ready to use

### Phase 2: Backend - Update Statement Parsers
Need to update these parsers to populate ISIN:

#### 2.1 IndMoney Parser
**File:** `backend/app/services/indmoney_parser.py`
**Changes:**
```python
from app.services.isin_lookup import lookup_isin_for_asset

# In parse() method, after creating asset data:
if 'isin' in row and row['isin']:
    asset_data['isin'] = row['isin']
    asset_data['api_symbol'] = row['isin']  # For mutual funds
else:
    # Lookup ISIN from API
    isin, api_symbol = lookup_isin_for_asset(
        asset_type=asset_data['asset_type'],
        symbol=asset_data['symbol'],
        name=asset_data['name']
    )
    if isin:
        asset_data['isin'] = isin
        if api_symbol:
            asset_data['api_symbol'] = api_symbol
```

#### 2.2 Vested Parser
**File:** `backend/app/services/vested_parser.py`
**Changes:** Similar to IndMoney, lookup ISIN for US stocks

#### 2.3 Statement Processor (Zerodha, Groww, etc.)
**File:** `backend/app/services/statement_processor.py`
**Changes:** Add ISIN lookup in `process_cas_statement()` and other processing functions

### Phase 3: Backend - Update Asset Creation
**File:** `backend/app/services/statement_processor.py`

**Function:** `create_or_update_asset()`
**Changes:**
```python
def create_or_update_asset(
    user_id: int,
    asset_data: Dict[str, Any],
    db: Session,
    demat_account_id: Optional[int] = None,
    statement_id: Optional[int] = None
) -> Asset:
    # ... existing code ...
    
    # If ISIN not provided, try to lookup
    if not asset_data.get('isin'):
        isin, api_symbol = lookup_isin_for_asset(
            asset_type=asset_data['asset_type'],
            symbol=asset_data.get('symbol', ''),
            name=asset_data.get('name', '')
        )
        if isin:
            asset_data['isin'] = isin
            if api_symbol and not asset_data.get('api_symbol'):
                asset_data['api_symbol'] = api_symbol
    
    # ... rest of existing code ...
```

### Phase 4: Frontend - Highlight Missing ISIN
**File:** `frontend/src/pages/Assets.tsx`

**Changes:**

#### 4.1 Add Visual Indicator
```typescript
// In the assets table row rendering:
<TableRow 
  key={group.symbol}
  sx={{
    backgroundColor: !group.instances[0].isin ? 'rgba(255, 0, 0, 0.1)' : 'inherit'
  }}
>
  {/* ... existing cells ... */}
  
  {/* Add ISIN status cell */}
  <TableCell>
    {group.instances[0].isin ? (
      <Chip 
        label="ISIN OK" 
        color="success" 
        size="small"
        icon={<CheckCircle />}
      />
    ) : (
      <Chip 
        label="ISIN Missing" 
        color="error" 
        size="small"
        icon={<Warning />}
      />
    )}
  </TableCell>
</TableRow>
```

#### 4.2 Add Tooltip with Message
```typescript
import { Tooltip } from '@mui/material';

{!group.instances[0].isin && (
  <Tooltip title="ISIN not found. Please edit asset to add ISIN manually for accurate price updates.">
    <Warning color="error" />
  </Tooltip>
)}
```

#### 4.3 Add Filter for Missing ISIN
```typescript
const [showOnlyMissingIsin, setShowOnlyMissingIsin] = useState(false);

// Filter assets
const filteredAssets = groupedAssets.filter(group => {
  if (showOnlyMissingIsin) {
    return !group.instances[0].isin;
  }
  return true;
});

// Add toggle button
<Button
  variant={showOnlyMissingIsin ? "contained" : "outlined"}
  onClick={() => setShowOnlyMissingIsin(!showOnlyMissingIsin)}
  startIcon={<Warning />}
>
  Show Missing ISIN ({missingIsinCount})
</Button>
```

### Phase 5: Testing

#### 5.1 Test ISIN Lookup
```bash
cd backend
source ../.venv/bin/activate
python -c "
from app.services.isin_lookup import lookup_isin_for_asset

# Test stock
isin, api_symbol = lookup_isin_for_asset('stock', 'RELIANCE', 'Reliance Industries')
print(f'Stock: ISIN={isin}, API Symbol={api_symbol}')

# Test mutual fund
isin, api_symbol = lookup_isin_for_asset('equity_mutual_fund', 'ICICI Prudential Bluechip Fund', 'ICICI Prudential Bluechip Fund')
print(f'MF: ISIN={isin}, API Symbol={api_symbol}')
"
```

#### 5.2 Test Statement Upload
1. Upload a statement with stocks/mutual funds
2. Verify ISIN is populated automatically
3. Verify api_symbol is set correctly
4. Check assets without ISIN are highlighted in red

### Phase 6: Documentation

#### 6.1 Update API Documentation
Document the new ISIN and api_symbol fields in asset schemas

#### 6.2 Update User Guide
Add section explaining:
- ISIN auto-population
- How to manually add ISIN for missing assets
- Why ISIN is important for accurate price updates

## Benefits

1. **Automatic ISIN Population**: No manual entry needed for most assets
2. **Accurate Price Updates**: ISIN ensures correct fund/stock matching
3. **Visual Feedback**: Red highlighting shows which assets need attention
4. **Better Data Quality**: Consistent ISIN across all assets
5. **Easier Troubleshooting**: Quickly identify assets with missing data

## Migration Strategy

### For Existing Assets
Create a script to backfill ISIN for existing assets:

```python
# backend/backfill_isin.py
from app.core.database import SessionLocal
from app.models.asset import Asset
from app.services.isin_lookup import lookup_isin_for_asset

db = SessionLocal()
assets = db.query(Asset).filter(Asset.isin == None).all()

for asset in assets:
    isin, api_symbol = lookup_isin_for_asset(
        asset_type=asset.asset_type.value,
        symbol=asset.symbol,
        name=asset.name
    )
    if isin:
        asset.isin = isin
        if api_symbol and not asset.api_symbol:
            asset.api_symbol = api_symbol
        print(f"Updated {asset.symbol}: ISIN={isin}")

db.commit()
db.close()
```

## Timeline

- **Phase 1**: ✅ Complete (ISIN lookup service created)
- **Phase 2**: 2-3 hours (Update all parsers)
- **Phase 3**: 1 hour (Update asset creation)
- **Phase 4**: 2 hours (Frontend changes)
- **Phase 5**: 1 hour (Testing)
- **Phase 6**: 1 hour (Documentation)
- **Total**: ~7-8 hours

## Priority

**HIGH** - This significantly improves data quality and user experience

## Next Steps

1. Review and approve this plan
2. Implement Phase 2 (update parsers)
3. Implement Phase 3 (update asset creation)
4. Implement Phase 4 (frontend highlighting)
5. Test thoroughly
6. Create backfill script for existing assets
7. Deploy and monitor

## Notes

- ISIN lookup may fail for some assets (delisted stocks, new funds, etc.)
- Need rate limiting for NSE API calls
- Consider caching ISIN lookups to reduce API calls
- May need fallback to manual entry for edge cases