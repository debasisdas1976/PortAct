# Mutual Fund Holdings CSV Upload Guide

## Overview
Since free APIs don't provide mutual fund portfolio holdings data, we've implemented a **CSV upload feature** that allows you to manually upload portfolio holdings for your mutual funds.

## How to Get Portfolio Holdings Data

### Option 1: From AMC Website (Recommended)
1. Visit your mutual fund's AMC (Asset Management Company) website
2. Navigate to the fund's page
3. Download the latest **Monthly Factsheet** (PDF)
4. Extract the portfolio holdings section
5. Convert to CSV format

### Option 2: From Investment Platforms
- **Moneycontrol**: Visit fund page → Portfolio tab
- **ValueResearch Online**: Fund page → Portfolio section
- **ET Money**: Fund details → Holdings
- **Groww/Zerodha Coin**: Fund page → Portfolio

### Option 3: From SEBI SCORES
1. Visit https://scores.gov.in/
2. Search for your mutual fund scheme
3. Download portfolio disclosure documents

## CSV Format

### Required Columns
- **Stock Name**: Name of the company/stock
- **Holding %**: Percentage of fund invested in this stock

### Optional Columns (Recommended)
- **Symbol**: Stock ticker symbol (e.g., RELIANCE, HDFCBANK)
- **ISIN**: ISIN code of the stock
- **Sector**: Sector classification (e.g., Financials, IT)
- **Industry**: Industry classification (e.g., Banking, Software)
- **Market Cap**: Large Cap, Mid Cap, or Small Cap

### Sample CSV Format

```csv
Stock Name,Symbol,ISIN,Holding %,Sector,Industry,Market Cap
Reliance Industries Ltd,RELIANCE,INE002A01018,8.5,Energy,Oil & Gas,Large Cap
HDFC Bank Ltd,HDFCBANK,INE040A01034,7.2,Financials,Banking,Large Cap
Infosys Ltd,INFY,INE009A01021,6.8,Information Technology,IT Services,Large Cap
ICICI Bank Ltd,ICICIBANK,INE090A01021,5.9,Financials,Banking,Large Cap
TCS Ltd,TCS,INE467B01029,5.5,Information Technology,IT Services,Large Cap
```

### Minimal CSV Format (Only Required Fields)

```csv
Stock Name,Holding %
Reliance Industries Ltd,8.5
HDFC Bank Ltd,7.2
Infosys Ltd,6.8
ICICI Bank Ltd,5.9
TCS Ltd,5.5
```

## Step-by-Step Upload Process

### Step 1: Download Sample Template
1. Go to **MF Holdings** page
2. Click **"Sample CSV"** button at the top
3. A template CSV file will be downloaded
4. Open it in Excel/Google Sheets

### Step 2: Fill in Your Data
1. Replace the sample data with your fund's actual holdings
2. Ensure **Stock Name** and **Holding %** are filled for all rows
3. Add optional fields if available
4. Save the file as CSV

### Step 3: Upload to PortAct
1. Go to **MF Holdings** page
2. Switch to **"By Fund"** view
3. Find the mutual fund you want to upload holdings for
4. Click the **Upload icon** (📤) next to the fund name
5. Select your CSV file
6. Wait for upload confirmation

### Step 4: Verify Data
1. Expand the fund's accordion
2. Review the uploaded holdings
3. Check if values are calculated correctly
4. View the **Dashboard** tab to see consolidated holdings

## Important Notes

### Holding Percentages
- Total holding percentage should be ≤ 100%
- The system will validate this during upload
- Top 10-15 holdings typically account for 40-60% of the fund

### Value Calculations
- **Holding Value** = (Your MF Units × Current NAV) × (Holding % / 100)
- **Approximate Quantity** = Holding Value / Stock Current Price
- Values are automatically calculated based on your MF units

### Data Freshness
- Portfolio holdings are typically updated monthly by AMCs
- Upload the latest factsheet for accurate data
- Re-upload when new factsheets are released

### Multiple Funds
- Upload CSV separately for each mutual fund
- Each fund can have different holdings
- Dashboard will aggregate all holdings automatically

## Troubleshooting

### Upload Fails
**Error: "Total holding percentage seems incorrect"**
- Check if percentages add up to more than 150%
- Verify you're using percentages (8.5) not decimals (0.085)
- Remove any summary rows from CSV

**Error: "Duplicate stock names found"**
- Ensure each stock appears only once in the CSV
- Check for extra spaces in stock names
- Remove any duplicate rows

**Error: "No holdings found in CSV file"**
- Verify CSV has proper headers
- Check if Stock Name and Holding % columns exist
- Ensure file is saved as CSV, not Excel format

### Values Not Calculating
- Ensure your MF units and NAV are up to date in Assets page
- Click the recalculate button if needed
- Refresh the page and check again

### Missing Stock Prices
- Stock prices need to be fetched separately
- Add stocks to your direct holdings for price tracking
- Or manually update stock prices in the database

## Tips for Best Results

### 1. Use Consistent Naming
- Use full company names as they appear in factsheets
- Example: "Reliance Industries Ltd" not "Reliance" or "RIL"

### 2. Include ISINs When Possible
- ISINs help match stocks across funds
- Enables better overlap detection
- Improves dashboard accuracy

### 3. Add Sector Information
- Helps with sector-wise analysis
- Useful for portfolio diversification review
- Can be added later if not available initially

### 4. Regular Updates
- Upload new data monthly when factsheets are released
- Keep track of portfolio changes
- Monitor fund manager's stock picking

### 5. Verify After Upload
- Always check the dashboard after upload
- Ensure values make sense
- Compare with your fund's total value

## Example Workflow

### For Parag Parikh Flexi Cap Fund

1. **Get Data**:
   - Visit PPFAS website
   - Download latest factsheet PDF
   - Note top 10 holdings with percentages

2. **Create CSV**:
   ```csv
   Stock Name,Holding %
   Alphabet Inc Class A,6.8
   Microsoft Corporation,5.2
   HDFC Bank Ltd,4.9
   Infosys Ltd,4.5
   Bajaj Finance Ltd,3.8
   ```

3. **Upload**:
   - Go to MF Holdings → By Fund
   - Find "Parag Parikh Flexi Cap Fund"
   - Click upload icon
   - Select CSV file

4. **Verify**:
   - Check holdings are displayed
   - Verify calculated values
   - View in Dashboard tab

## Future Enhancements

We're working on:
- Automatic factsheet PDF parsing
- Integration with paid APIs for auto-updates
- Historical holdings tracking
- Portfolio rebalancing alerts

## Need Help?

If you encounter issues:
1. Download and check the sample CSV format
2. Verify your CSV matches the format
3. Check backend logs for detailed error messages
4. Ensure your mutual fund details (units, NAV) are correct

---

**Made with Bob** - Making portfolio tracking easier, one CSV at a time! 📊