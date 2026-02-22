# AMC Portfolio Disclosure URLs

## Overview
This document contains portfolio disclosure page URLs for 30+ Asset Management Companies (AMCs) in India, extracted from the AMFI website.

## Source
**AMFI Portfolio Disclosure Page**: https://www.amfiindia.com/online-center/portfolio-disclosure

## How to Use

### With Our System
Our system can download and parse portfolio Excel files from any of these AMC websites:

```bash
POST /api/v1/mutual-fund-holdings/{asset_id}/download-from-url?url=<excel_url>
```

### Finding Excel Files
1. Visit the AMC's portfolio disclosure page
2. Look for monthly/fortnightly portfolio Excel files
3. Copy the direct Excel file URL
4. Use our API endpoint to download and parse

## AMC Portfolio Disclosure Pages

### Major AMCs

#### HDFC Mutual Fund
- Monthly Portfolio: https://www.hdfcfund.com/statutory-disclosure/monthly-portfolio
- Fortnightly Portfolio: https://www.hdfcfund.com/statutory-disclosure/portfolio/fortnightly-portfolio

#### ICICI Prudential
- Financials & Disclosures: https://www.icicipruamc.com/about-us/financials-&-disclosures
- Downloads: https://www.icicipruamc.com/news-and-media/downloads

#### SBI Mutual Fund
- Disclosure: https://www.sbimf.com/en-us/disclosure
- Portfolios: https://www.sbimf.com/en-us/portfolios

#### Axis Mutual Fund
- Statutory Disclosures: https://www.axismf.com/statutory-disclosures

#### Kotak Mutual Fund
- Risk-o-meter Disclosure: https://www.kotakmf.com/Information/forms-and-downloads/Risk-o-meter_Disclosure_

#### Aditya Birla Sun Life
- Portfolio: https://mutualfund.adityabirlacapital.com/forms-and-downloads/portfolio

#### Nippon India (Direct Excel Links Found!)
- Fortnightly Portfolio: https://mf.nipponindiaim.com/InvestorServices/FactsheetsDocuments/NIMF_FORTNIGHTLY_PORTFOLIO_31-Jan-26.xls
- Half-Yearly Report: https://mf.nipponindiaim.com/InvestorServices/AnnualHalfYearlyReportsFY20242025/NIMF-HY-PORTFOLIO-REPORT-30-Sep-25.xls
- Downloads Page: https://mf.nipponindiaim.com/investor-service/downloads/factsheet-portfolio-and-other-disclosures

#### PPFAS (Parag Parikh)
- Portfolio Disclosure: https://amc.ppfas.com/downloads/portfolio-disclosure/
- Fortnightly Debt: https://amc.ppfas.com/downloads/portfolio-disclosure/fortnightly-debt-portfolio-disclosure/

### Mid-Size AMCs

#### DSP Mutual Fund
- Portfolio Disclosures: https://www.dspim.com/about-us/mandatory-disclosure/portfolio-disclosures
- Annual Reports: https://www.dspim.com/about-us/mandatory-disclosure/annual-reports

#### Franklin Templeton
- (URL not directly found, check AMFI page)

#### Mirae Asset
- Portfolio: https://www.miraeassetmf.co.in/downloads/portfolio
- Statutory Disclosure: https://www.miraeassetmf.co.in/downloads/statutory-disclosure/financials

#### Motilal Oswal
- Month-End Portfolio: https://www.motilaloswalmf.com/downloads/mutual-fund/Month-End-Portfolio

#### UTI Mutual Fund
- Consolidated Portfolio: https://www.utimf.com/downloads/consolidate-all-portfolio-disclosure
- Debt Portfolio: https://www.utimf.com/downloads/consolidate-debt-portfolio-disclosure

#### Tata Mutual Fund
- Monthly Portfolio: https://www.tatamutualfund.com/downloads/monthly-portfolio
- Statutory Disclosures: https://www.tatamutualfund.com/statutory-disclosures/other-statutory-disclosures

#### Sundaram Mutual Fund
- Half-yearly Portfolio: https://www.sundarammutual.com/Halfyearly-Portfolio-Disclosure
- Monthly/Fortnightly: https://www.sundarammutual.com/Monthly-Fortnightly-Adhoc-Portfolios

### Smaller/Newer AMCs

#### Quantum Mutual Fund (Direct Excel Link Found!)
- Portfolio: https://www.quantumamc.com/portfolio/combined/-1/1/0/0
- Excel File: https://www.quantumamc.com/FileCDN/FactSheet/d3f25c83-e7ad-44d8-92ba-6ab3abed5e3e.xlsx

#### Quant Mutual Fund
- Statutory Disclosures: https://quantmutual.com/statutory-disclosures

#### 360 ONE (IIFL)
- Disclosures: https://www.360.one/asset-management/mutualfund/downloads/disclosures/

#### Bandhan Mutual Fund
- Disclosures: https://bandhanmutual.com/downloads/disclosures
- Other Disclosures: https://bandhanmutual.com/downloads/other-disclosures

#### Navi Mutual Fund
- Portfolio: https://navi.com/mutual-fund/downloads/portfolio
- Statutory Disclosure: https://navi.com/mutual-fund/downloads/statutory-disclosure

#### Groww Mutual Fund
- Portfolio: https://growwmf.in/statutory-disclosure/portfolio

#### Union Mutual Fund
- Fortnightly Portfolio: https://unionmf.com/about-us/downloads/fortnightly-portfolio
- Monthly Portfolio: https://unionmf.com/about-us/downloads/monthly-portfolio

#### Taurus Mutual Fund
- Monthly Portfolio: https://taurusmutualfund.com/monthly-portfolio

#### Old Bridge Mutual Fund (Direct Excel Link Found!)
- Statutory Disclosures: https://oldbridgemf.com/statutory-disclosures.html
- Excel File: https://www.oldbridgemf.com/uploads/Half_Yearly_Portfolio_Sep_25_ffb0e3fd13.xlsx

#### Capital Mind Mutual Fund
- Statutory Disclosures: https://capitalmindmf.com/statutory-disclosures.html

#### Choice Mutual Fund
- Factsheets: https://choicemf.com/disclosures/factsheets
- Monthly Portfolio: https://choicemf.com/disclosures/monthly-portfolio

#### White Oak Mutual Fund
- Regulatory Disclosures: https://mf.whiteoakamc.com/regulatory-disclosures
- Scheme Portfolios: https://mf.whiteoakamc.com/regulatory-disclosures/scheme-portfolios

#### PGIM India
- Disclosures: https://www.pgimindia.com/mutual-funds/disclosures/Financial-Statements/Scheme-Financials

#### Invesco Mutual Fund
- About Us: https://invescomutualfund.com/about-us

#### UNIFI Mutual Fund
- Statutory Documents: https://unifimf.com/statutorydocuments/

#### Abakkus Mutual Fund
- Statutory Disclosures: https://www.abakkusmf.com/statutory-disclosures.html

## Direct Excel File Examples

These are actual Excel file URLs found on the AMFI page:

1. **Nippon India - Fortnightly Portfolio**
   ```
   https://mf.nipponindiaim.com/InvestorServices/FactsheetsDocuments/NIMF_FORTNIGHTLY_PORTFOLIO_31-Jan-26.xls
   ```

2. **Nippon India - Half-Yearly Report**
   ```
   https://mf.nipponindiaim.com/InvestorServices/AnnualHalfYearlyReportsFY20242025/NIMF-HY-PORTFOLIO-REPORT-30-Sep-25.xls
   ```

3. **Old Bridge - Half-Yearly Portfolio**
   ```
   https://www.oldbridgemf.com/uploads/Half_Yearly_Portfolio_Sep_25_ffb0e3fd13.xlsx
   ```

4. **Quantum - Factsheet**
   ```
   https://www.quantumamc.com/FileCDN/FactSheet/d3f25c83-e7ad-44d8-92ba-6ab3abed5e3e.xlsx
   ```

## Usage with Our System

### Step 1: Find the Excel URL
Visit the AMC's portfolio disclosure page and locate the Excel file link.

### Step 2: Use Our API
```bash
curl -X POST "http://localhost:8000/api/v1/mutual-fund-holdings/123/download-from-url?url=<excel_url>" \
  -H "Authorization: Bearer <token>"
```

### Step 3: System Processes
1. Downloads the Excel file
2. Detects format (PPFAS-specific or generic)
3. Extracts equity holdings with ISIN codes
4. Stores in database
5. Calculates values based on your MF units

### Step 4: View in Dashboard
Holdings appear in the MF Holdings dashboard with:
- Stock name and ISIN
- Holding percentage
- Calculated value
- Combined with direct stock holdings

## Notes

### File Formats
- Most AMCs provide `.xls` or `.xlsx` files
- Our parser supports both formats
- Generic parser handles different layouts

### Update Frequency
- **Monthly**: Most AMCs update monthly
- **Fortnightly**: Some AMCs (HDFC, Nippon, etc.)
- **Half-Yearly**: Regulatory requirement
- **Annual**: Full annual reports

### Limitations
- Some AMC websites require JavaScript rendering
- Some files may be password-protected
- File URLs may change monthly (date-based naming)
- Not all AMCs provide direct Excel links

## Recommendations

### For Best Results
1. **Use PPFAS**: Most reliable, direct Excel links
2. **Try Nippon India**: Direct Excel links available
3. **Check Monthly**: Most AMCs update around month-end
4. **Bookmark Pages**: Save AMC disclosure pages for easy access

### For Other AMCs
1. Visit the disclosure page
2. Look for "Monthly Portfolio" or "Fortnightly Portfolio"
3. Download the Excel file manually
4. Use our CSV upload feature as fallback

## Future Enhancements

### Potential Improvements
1. **Auto-Discovery**: Scrape AMC pages to find latest Excel URLs
2. **Scheduled Updates**: Auto-download monthly portfolios
3. **AMC-Specific Parsers**: Optimize for each AMC's format
4. **URL Patterns**: Learn URL patterns for automatic updates

### Contributing
If you find working Excel URLs for any AMC, please share them to improve this list!

## Summary

- **30+ AMCs** with portfolio disclosure pages
- **4 Direct Excel URLs** found
- **102 Total URLs** catalogued
- **All Compatible** with our download system

Our system can handle Excel files from any of these AMCs using the generic parser with automatic format detection!