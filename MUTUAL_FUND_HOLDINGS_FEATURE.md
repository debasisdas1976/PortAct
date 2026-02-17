# Mutual Fund Holdings Deep Dive Feature

## Overview

This feature enables users to deep dive into their equity mutual fund holdings, extracting the underlying stock-level holdings with percentages, and viewing them in a comprehensive dashboard that combines both mutual fund holdings and direct stock holdings.

## Key Capabilities

### 1. **Automatic Holdings Extraction**
- Automatically downloads and parses portfolio disclosure Excel files from AMC websites
- Extracts equity holdings with stock names, ISINs, and holding percentages
- Supports 30+ AMCs through AMFI portfolio disclosure integration

### 2. **Holdings Dashboard**
- Unified view of all stock holdings across:
  - Direct stock investments
  - Indirect holdings through mutual funds
- Shows aggregated holdings when the same stock is held both directly and through MFs
- Calculates actual holding values based on:
  - Mutual fund units held
  - Current NAV
  - Holding percentage in the fund

### 3. **Multi-Source Support**
- **Automatic Update**: Scrapes AMFI to find AMC URLs and downloads latest portfolios
- **Manual URL**: Provide direct Excel file URL
- **Manual Upload**: Upload CSV file with holdings data

## Architecture

### Backend Components

#### 1. Database Model
**File**: `backend/app/models/mutual_fund_holding.py`

```python
class MutualFundHolding:
    - asset_id: Link to mutual fund asset
    - stock_name: Name of the underlying stock
    - isin: ISIN code for stock identification
    - holding_percentage: Percentage of fund invested in this stock
    - holding_value: Calculated value based on user's MF units
    - sector, industry, market_cap: Additional metadata
```

#### 2. Services

##### AMFI Scraper Service
**File**: `backend/app/services/amfi_scraper.py`

- Scrapes https://www.amfiindia.com/online-center/portfolio-disclosure
- Maps fund names to AMC identifiers
- Finds portfolio disclosure URLs for each AMC
- Discovers latest Excel file URLs from AMC pages

**Key Methods**:
```python
get_amc_urls() -> Dict[str, List[str]]
get_amc_url_for_fund(fund_name: str) -> Optional[str]
find_latest_excel_url(amc_portfolio_url: str) -> Optional[str]
```

##### Portfolio Downloader Service
**File**: `backend/app/services/portfolio_downloader.py`

- Downloads Excel files from URLs
- Handles both direct Excel URLs and AMC portfolio pages
- Auto-discovers latest PPFAS portfolios
- Manages temporary files with automatic cleanup

**Key Methods**:
```python
download_portfolio(url: str) -> str  # Returns path to downloaded file
download_latest_ppfas_portfolio() -> str
```

##### Portfolio Parsers

**PPFAS Parser** (`backend/app/services/ppfas_excel_parser.py`):
- Specialized parser for Parag Parikh Flexi Cap Fund
- Extracts both domestic and foreign equity holdings
- Section-based extraction with intelligent row detection

**Generic Parser** (`backend/app/services/generic_portfolio_parser.py`):
- Multi-strategy parser for any AMC format
- Tries PPFAS parser first, then generic column detection
- Intelligent column matching for stock name, ISIN, industry, percentage
- Automatically filters out debt instruments

**Key Methods**:
```python
parse_portfolio(file_path: str) -> List[Dict]
# Returns: [{'name': str, 'isin': str, 'percentage': float, ...}]
```

#### 3. API Endpoints

**File**: `backend/app/api/v1/endpoints/mutual_fund_holdings.py`

##### Auto-Update All Holdings
```
POST /api/v1/mutual-fund-holdings/auto-update-all
Query Parameters:
  - force_refresh: bool (default: false)

Response:
{
  "success": true,
  "message": "Auto-update completed: 5 successful, 0 failed",
  "total_funds": 5,
  "successful_updates": 5,
  "failed_updates": 0,
  "results": [
    {
      "asset_id": 123,
      "fund_name": "Parag Parikh Flexi Cap Fund",
      "success": true,
      "message": "Successfully updated 45 holdings",
      "holdings_count": 45,
      "source_url": "https://..."
    }
  ]
}
```

**Process**:
1. Finds all equity mutual funds in user's portfolio
2. For each fund:
   - Checks if AMC URL is stored in asset.details
   - If not, uses AMFI scraper to find it
   - Stores URL for future use
   - Finds latest Excel file URL
   - Downloads and parses portfolio
   - Updates holdings in database
3. Returns summary of successful and failed updates

##### Download from URL
```
POST /api/v1/mutual-fund-holdings/{asset_id}/download-from-url
Query Parameters:
  - url: str (required) - Direct Excel URL or AMC portfolio page

Response:
{
  "success": true,
  "message": "Successfully downloaded and parsed portfolio from URL",
  "holdings_count": 45,
  "domestic_count": 38,
  "foreign_count": 7,
  "url": "https://..."
}
```

##### Upload CSV
```
POST /api/v1/mutual-fund-holdings/{asset_id}/upload-csv
Body: multipart/form-data with CSV file

CSV Format:
stock_name,isin,holding_percentage,sector,industry
Reliance Industries,INE002A01018,5.25,Energy,Oil & Gas
HDFC Bank,INE040A01034,4.80,Financials,Banking
```

##### Get Holdings Dashboard
```
GET /api/v1/mutual-fund-holdings/dashboard/stocks

Response:
{
  "stocks": [
    {
      "stock_name": "Reliance Industries",
      "isin": "INE002A01018",
      "direct_holding": {
        "quantity": 100,
        "value": 250000,
        "avg_price": 2500
      },
      "mf_holdings": [
        {
          "fund_name": "Parag Parikh Flexi Cap Fund",
          "holding_percentage": 5.25,
          "holding_value": 52500,
          "units_held": 1000,
          "nav": 50
        }
      ],
      "total_value": 302500,
      "total_percentage": 3.5
    }
  ],
  "summary": {
    "total_stocks": 45,
    "total_value": 8500000,
    "direct_value": 3000000,
    "mf_value": 5500000
  }
}
```

### Frontend Components

#### Holdings Dashboard Page
**File**: `frontend/src/pages/MutualFundHoldings.tsx`

**Features**:
- Tabbed interface for different views
- Stock-level aggregation showing direct + MF holdings
- Fund-level view showing holdings per mutual fund
- Auto-update button to refresh all holdings
- Manual upload/URL input options
- Sortable tables with search functionality
- Visual indicators for holding sources

**Navigation**: Added to main menu as "MF Holdings"

## Usage Guide

### For Users

#### Option 1: Automatic Update (Recommended)
1. Navigate to "MF Holdings" page
2. Click "Auto-Update All Holdings" button
3. System will:
   - Find all your equity mutual funds
   - Download latest portfolios from AMC websites
   - Parse and update holdings
   - Show success/failure summary

#### Option 2: Manual URL
1. Go to specific mutual fund
2. Click "Update from URL"
3. Paste the Excel file URL or AMC portfolio page URL
4. System downloads and parses automatically

#### Option 3: Manual CSV Upload
1. Download sample CSV template
2. Fill in holdings data
3. Upload CSV file
4. Holdings are imported

### For Developers

#### Adding Support for New AMC

1. **Add AMC mapping** in `amfi_scraper.py`:
```python
AMC_MAPPINGS = {
    'new amc name': 'newamc',
    # ... existing mappings
}
```

2. **Add domain identification** in `_identify_amc()`:
```python
elif 'newamc' in domain_lower:
    return 'newamc'
```

3. **Test with sample fund**:
```python
scraper = AMFIScraper()
url = scraper.get_amc_url_for_fund("New AMC Flexi Cap Fund")
print(url)
```

#### Creating Custom Parser

If generic parser doesn't work for a specific AMC format:

1. Create new parser in `backend/app/services/`
2. Implement `parse_portfolio(file_path: str) -> List[Dict]`
3. Return list of holdings with required fields:
   - `name`: Stock name (required)
   - `percentage`: Holding percentage (required)
   - `isin`: ISIN code (optional but recommended)
   - `industry`: Industry classification (optional)
   - `sector`: Sector classification (optional)

4. Update `generic_portfolio_parser.py` to try your parser

## Data Flow

```
User Portfolio (Equity MFs)
    ↓
AMFI Scraper → Find AMC URLs
    ↓
Portfolio Downloader → Download Excel
    ↓
Portfolio Parser → Extract Holdings
    ↓
Database (mutual_fund_holdings table)
    ↓
API Endpoints → Calculate Values
    ↓
Frontend Dashboard → Display Aggregated View
```

## Value Calculation

For each stock holding in a mutual fund:

```
holding_value = (mf_units × mf_nav) × (holding_percentage / 100)
```

Example:
- You hold 1000 units of PPFAS
- Current NAV: ₹50
- Fund holds 5.25% in Reliance
- Your indirect Reliance holding value: (1000 × 50) × (5.25 / 100) = ₹2,625

## Supported AMCs

Currently catalogued 30+ AMCs including:
- HDFC, ICICI Prudential, SBI, Axis, Kotak
- Aditya Birla Sun Life, Nippon India
- PPFAS (Parag Parikh), DSP, Franklin Templeton
- Mirae Asset, Motilal Oswal, UTI, Tata
- Quantum, Quant, 360 ONE (IIFL)
- And many more...

See `AMC_PORTFOLIO_DISCLOSURE_URLS.md` for complete list.

## Technical Details

### Database Schema

```sql
CREATE TABLE mutual_fund_holdings (
    id SERIAL PRIMARY KEY,
    asset_id INTEGER REFERENCES assets(id),
    user_id INTEGER REFERENCES users(id),
    stock_name VARCHAR(255) NOT NULL,
    stock_symbol VARCHAR(50),
    isin VARCHAR(12),  -- Indexed for fast lookups
    holding_percentage DECIMAL(10, 4),
    holding_value DECIMAL(15, 2),
    sector VARCHAR(100),
    industry VARCHAR(100),
    market_cap VARCHAR(50),
    data_source VARCHAR(50),
    last_updated TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_mf_holdings_isin ON mutual_fund_holdings(isin);
CREATE INDEX idx_mf_holdings_asset ON mutual_fund_holdings(asset_id);
```

### Asset Details JSON

AMC URLs are stored in the asset's `details` JSON field:

```json
{
  "amc_portfolio_url": "https://www.ppfas.com/downloads/portfolio-disclosure/"
}
```

This allows the system to remember the URL and avoid re-scraping AMFI on subsequent updates.

## Error Handling

The system handles various error scenarios:

1. **AMC URL Not Found**: Logs warning, skips fund
2. **Download Failure**: Retries with timeout, reports error
3. **Parse Failure**: Falls back to generic parser, reports if no holdings found
4. **Invalid Data**: Validates percentages, filters out debt instruments
5. **Database Errors**: Rolls back transaction, preserves existing data

## Performance Considerations

- **Caching**: AMFI scraper caches AMC URLs to avoid repeated scraping
- **Batch Processing**: Auto-update processes all funds in one request
- **Async Operations**: Downloads and parsing are async where possible
- **Temporary Files**: Automatically cleaned up after parsing
- **Database Indexing**: ISIN field indexed for fast aggregation queries

## Future Enhancements

1. **Scheduled Updates**: Automatic monthly updates when new portfolios are published
2. **Change Tracking**: Track changes in holdings over time
3. **Alerts**: Notify when fund significantly changes holdings
4. **Comparison**: Compare holdings across multiple funds
5. **Export**: Export aggregated holdings to Excel/PDF
6. **Visualization**: Charts showing sector allocation, top holdings, etc.

## Testing

### Test AMFI Scraper
```bash
cd backend
python -m app.services.amfi_scraper
```

### Test Portfolio Download and Parse
```bash
cd backend
python -m app.services.portfolio_downloader
```

### Test API Endpoint
```bash
curl -X POST "http://localhost:8000/api/v1/mutual-fund-holdings/auto-update-all" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Troubleshooting

### Issue: No holdings found
- **Check**: Is the fund an equity mutual fund?
- **Check**: Does the AMC publish portfolio disclosures?
- **Solution**: Try manual CSV upload

### Issue: Parser fails
- **Check**: Excel file format
- **Solution**: Create custom parser for that AMC

### Issue: ISIN not found
- **Impact**: Stock won't be aggregated with direct holdings
- **Solution**: Manually add ISIN to holdings or update parser

### Issue: Outdated holdings
- **Solution**: Use `force_refresh=true` parameter in auto-update

## Security Considerations

- All endpoints require authentication
- Users can only access their own holdings
- File uploads are validated and sanitized
- Temporary files are cleaned up immediately
- No sensitive data stored in logs

## Compliance

- Data sourced from publicly available AMC disclosures
- No scraping of restricted content
- Respects robots.txt and rate limits
- User data privacy maintained

## Support

For issues or questions:
1. Check logs: `backend.log`
2. Review error messages in API responses
3. Verify AMC URL in `AMC_PORTFOLIO_DISCLOSURE_URLS.md`
4. Test with sample CSV upload first

## License

This feature is part of the PortAct portfolio management system.