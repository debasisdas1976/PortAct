# Mutual Fund Holdings Excel Parser

## Overview
A robust parser for extracting equity holdings from Parag Parikh Flexi Cap Fund (PPFAS) monthly portfolio Excel files. The parser accurately extracts both domestic and foreign equity holdings with complete details including ISIN codes.

## Features

### 1. Comprehensive Data Extraction
- **Company Name**: Full name of the stock
- **ISIN Code**: International Securities Identification Number (both Indian INE... and US formats)
- **Industry/Sector**: Industry classification
- **Holding Percentage**: Percentage of fund invested in each stock
- **Foreign Flag**: Distinguishes between domestic and foreign holdings

### 2. Dual Section Support
- **Domestic Equity**: "Equity & Equity related" section
- **Foreign Equity**: "Equity & Equity related Foreign Investments" section

### 3. Data Validation
- Filters out subtotals and headers
- Validates percentage ranges
- Cleans company names (removes "Limited", "Ltd" suffixes)
- Handles missing or malformed data gracefully

## Database Integration

### ISIN Storage
The ISIN code is stored in the database with proper indexing:

```python
# Model: backend/app/models/mutual_fund_holding.py
isin = Column(String, index=True)  # Line 18

# Schema: backend/app/schemas/mutual_fund_holding.py
isin: Optional[str] = Field(None, max_length=50)  # Line 10
```

### Complete Data Model
Each holding stores:
- `stock_name`: Company name
- `stock_symbol`: Stock ticker
- `isin`: ISIN code (indexed for fast lookups)
- `holding_percentage`: Fund allocation percentage
- `holding_value`: Calculated value based on user's MF units
- `quantity_held`: Approximate shares held through MF
- `sector`: Stock sector
- `industry`: Industry classification
- `market_cap`: Large/Mid/Small cap
- `stock_current_price`: Current stock price

## Usage

### Basic Usage
```python
from app.services.ppfas_excel_parser import parse_ppfas_excel

# Parse Excel file
holdings = parse_ppfas_excel('path/to/portfolio.xls')

# Each holding contains:
for holding in holdings:
    print(f"{holding['name']}")
    print(f"  ISIN: {holding['isin']}")
    print(f"  Industry: {holding['industry']}")
    print(f"  Holding: {holding['percentage']}%")
    print(f"  Foreign: {holding['is_foreign']}")
```

### Integration with Database
```python
from app.services.ppfas_excel_parser import parse_ppfas_excel
from app.models.mutual_fund_holding import MutualFundHolding

# Parse Excel
holdings = parse_ppfas_excel('portfolio.xls')

# Save to database
for holding in holdings:
    db_holding = MutualFundHolding(
        asset_id=mutual_fund_asset_id,
        user_id=current_user_id,
        stock_name=holding['name'],
        isin=holding['isin'],
        industry=holding['industry'],
        holding_percentage=holding['percentage'],
        data_source='excel_upload'
    )
    db.add(db_holding)
db.commit()
```

## Test Results

### Sample File: PPFCF_PPFAS_Monthly_Portfolio_Report_January_31_2026.xls

#### Domestic Equity (31 stocks)
| Company | ISIN | Industry | % |
|---------|------|----------|---|
| HDFC Bank | INE040A01034 | Banks | 8.04% |
| Power Grid Corporation of India | INE752E01010 | Power | 6.00% |
| Coal India | INE522F01014 | Consumable Fuels | 5.26% |
| ITC | INE154A01025 | Diversified FMCG | 5.05% |
| ICICI Bank | INE090A01021 | Banks | 4.99% |
| ... | ... | ... | ... |

**Total Domestic: 65.59%**

#### Foreign Equity (4 stocks)
| Company | ISIN | Industry | % |
|---------|------|----------|---|
| Alphabet Inc A | US02079K3059 | Computer Software | 4.39% |
| Meta Platforms | US30303M1027 | Computer Software | 2.91% |
| Amazon Com | US0231351067 | Catalog/Specialty Distribution | 2.27% |
| Microsoft | US5949181045 | Computer Software | 2.17% |

**Total Foreign: 11.74%**

**Grand Total Equity: 77.33%**

## ISIN Code Benefits

### 1. Unique Identification
- ISIN provides globally unique identification for securities
- Enables accurate matching with direct stock holdings
- Facilitates price lookups from market data APIs

### 2. Cross-Reference Capability
- Match MF holdings with user's direct stock portfolio
- Aggregate holdings across multiple mutual funds
- Identify overlapping investments

### 3. Data Enrichment
- Use ISIN to fetch real-time stock prices
- Get company fundamentals and financial data
- Link to external financial databases

## Dashboard Integration

### Consolidated View
The ISIN enables creating a unified dashboard showing:

```
Stock: HDFC Bank (INE040A01034)
├── Direct Holdings
│   ├── Quantity: 100 shares
│   ├── Value: ₹160,000
│   └── Invested: ₹150,000
└── Mutual Fund Holdings
    ├── Through PPFCF: 8.04% (₹50,000 value)
    ├── Through Other MFs: 2.5% (₹15,000 value)
    └── Total MF Value: ₹65,000

Total HDFC Bank Holdings: ₹225,000
```

### Value Calculation
```python
# For each stock in MF
holding_value = (mf_units × mf_nav) × (holding_percentage / 100)

# Example: HDFC Bank in PPFCF
# User has 1000 units of PPFCF at NAV ₹93.52
# PPFCF holds 8.04% in HDFC Bank
holding_value = (1000 × 93.52) × (8.04 / 100)
             = 93,520 × 0.0804
             = ₹7,519
```

## File Structure

```
backend/app/services/
├── ppfas_excel_parser.py          # Main Excel parser
└── ppfas_factsheet_parser.py      # PDF parser (backup)

backend/app/models/
└── mutual_fund_holding.py          # Database model with ISIN field

backend/app/schemas/
└── mutual_fund_holding.py          # Pydantic schemas with ISIN

backend/app/api/v1/endpoints/
└── mutual_fund_holdings.py         # API endpoints (to be updated)
```

## Next Steps

### 1. API Endpoint for Excel Upload
```python
@router.post("/{asset_id}/upload-excel")
async def upload_excel_holdings(
    asset_id: int,
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Save uploaded file
    # Parse using ppfas_excel_parser
    # Store holdings in database with ISIN
    # Return success response
```

### 2. Dashboard Enhancement
- Display ISIN codes in holdings table
- Enable filtering by ISIN
- Show combined holdings (direct + MF) grouped by ISIN
- Add ISIN-based search functionality

### 3. Price Updates
- Use ISIN to fetch real-time prices
- Update `stock_current_price` field
- Recalculate `holding_value` and `quantity_held`

## Technical Notes

### Excel Format Support
- Supports `.xls` format (Excel 97-2003)
- Uses pandas for robust parsing
- Handles merged cells and complex layouts

### Error Handling
- Gracefully handles missing data
- Validates ISIN format
- Logs parsing errors for debugging

### Performance
- Efficient pandas operations
- Indexed ISIN field for fast queries
- Batch database inserts for large portfolios

## Conclusion

The PPFAS Excel parser successfully extracts all equity holdings including ISIN codes, enabling:
- Accurate stock identification
- Cross-referencing with direct holdings
- Real-time price updates
- Comprehensive portfolio analysis

The ISIN field is properly stored in the database with indexing for optimal performance.