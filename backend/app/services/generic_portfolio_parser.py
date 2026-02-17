"""
Generic Portfolio Parser
Attempts to parse mutual fund portfolio Excel files with various formats
"""
import pandas as pd
import re
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class GenericPortfolioParser:
    """Generic parser that attempts to extract equity holdings from any MF portfolio Excel"""
    
    # Common column name variations
    STOCK_NAME_COLUMNS = [
        'name of the instrument', 'instrument name', 'stock name', 'company name',
        'security name', 'name', 'scrip name', 'instrument'
    ]
    
    ISIN_COLUMNS = ['isin', 'isin code', 'isin number']
    
    INDUSTRY_COLUMNS = [
        'industry', 'sector', 'industry / rating', 'rating', 'classification'
    ]
    
    PERCENTAGE_COLUMNS = [
        '% to net assets', 'percentage', '% of nav', '% to nav', 
        'weightage', 'allocation', '% allocation'
    ]
    
    # Section headers that indicate equity holdings
    EQUITY_SECTION_HEADERS = [
        'equity', 'equity & equity related', 'equity and equity related',
        'listed', 'stock', 'shares', 'equities'
    ]
    
    # Section headers to exclude (debt, etc.)
    EXCLUDE_SECTION_HEADERS = [
        'debt', 'bond', 'debenture', 'government securities', 'treasury',
        'money market', 'cash', 'liquid', 'fixed income'
    ]
    
    def __init__(self, excel_path: str):
        self.excel_path = excel_path
        self.holdings: List[Dict] = []
        
    def parse(self) -> List[Dict]:
        """
        Attempt to parse the Excel file using various strategies
        
        Returns:
            List of holdings with name, isin, industry, percentage
        """
        try:
            # Try PPFAS-specific parser first
            try:
                from ppfas_excel_parser import parse_ppfas_excel
                holdings = parse_ppfas_excel(self.excel_path)
                if holdings and len(holdings) > 0:
                    logger.info(f"Successfully parsed using PPFAS parser: {len(holdings)} holdings")
                    return holdings
            except Exception as e:
                logger.debug(f"PPFAS parser failed: {e}")
            
            # Try generic parsing
            logger.info("Attempting generic parsing...")
            
            # Read Excel file with explicit engine
            # Try openpyxl first (for .xlsx), then xlrd (for .xls)
            xls = None
            try:
                xls = pd.ExcelFile(self.excel_path, engine='openpyxl')
            except Exception as e1:
                logger.debug(f"openpyxl engine failed: {e1}")
                try:
                    xls = pd.ExcelFile(self.excel_path, engine='xlrd')
                except Exception as e2:
                    logger.error(f"xlrd engine also failed: {e2}")
                    raise Exception(f"Failed to read Excel file with both engines: openpyxl and xlrd")
            
            if not xls:
                raise Exception("Could not open Excel file")
            
            all_holdings = []
            
            # Try each sheet - each sheet might be a different fund
            for sheet_name in xls.sheet_names:
                logger.info(f"Processing sheet: {sheet_name}")
                
                try:
                    df = pd.read_excel(
                        self.excel_path,
                        sheet_name=sheet_name,
                        engine='openpyxl' if self.excel_path.endswith('.xlsx') else 'xlrd'
                    )
                    
                    # Try to find equity section and extract holdings
                    holdings = self._extract_from_dataframe(df)
                    
                    if holdings and len(holdings) > 0:
                        logger.info(f"Successfully parsed {len(holdings)} holdings from sheet: {sheet_name}")
                        all_holdings.extend(holdings)
                except Exception as e:
                    logger.warning(f"Failed to parse sheet {sheet_name}: {e}")
                    continue
            
            if all_holdings:
                logger.info(f"Total holdings extracted from all sheets: {len(all_holdings)}")
                return all_holdings
            
            logger.warning("No holdings found in any sheet")
            return []
            
        except Exception as e:
            logger.error(f"Error parsing portfolio: {e}")
            raise Exception(f"Failed to parse portfolio: {str(e)}")
    
    def _extract_from_dataframe(self, df: pd.DataFrame) -> List[Dict]:
        """Extract holdings from a dataframe"""
        
        # Strategy 1: Look for structured table with column headers
        holdings = self._extract_structured_table(df)
        if holdings:
            return holdings
        
        # Strategy 2: Look for section-based format (like PPFAS)
        holdings = self._extract_section_based(df)
        if holdings:
            return holdings
        
        return []
    
    def _extract_structured_table(self, df: pd.DataFrame) -> List[Dict]:
        """Extract from a structured table with clear column headers"""
        
        holdings = []
        
        # Find the header row
        header_row_idx = self._find_header_row(df)
        
        if header_row_idx is None:
            return []
        
        # Set the header row
        df.columns = df.iloc[header_row_idx]
        df = df.iloc[header_row_idx + 1:]
        
        # Find column indices
        name_col = self._find_column(df.columns, self.STOCK_NAME_COLUMNS)
        isin_col = self._find_column(df.columns, self.ISIN_COLUMNS)
        industry_col = self._find_column(df.columns, self.INDUSTRY_COLUMNS)
        pct_col = self._find_column(df.columns, self.PERCENTAGE_COLUMNS)
        
        if name_col is None or pct_col is None:
            logger.debug("Could not find required columns")
            return []
        
        # Extract rows
        for idx, row in df.iterrows():
            try:
                name = str(row[name_col]).strip() if pd.notna(row[name_col]) else None
                percentage = self._extract_percentage(row[pct_col])
                
                if not name or not percentage or percentage <= 0:
                    continue
                
                # Skip totals and subtotals
                if any(keyword in name.lower() for keyword in ['total', 'sub total', 'grand']):
                    continue
                
                # Check if it's in equity section
                if not self._is_equity_holding(name, row):
                    continue
                
                holding = {
                    'name': self._clean_company_name(name),
                    'isin': str(row[isin_col]).strip() if isin_col and pd.notna(row[isin_col]) else '',
                    'industry': str(row[industry_col]).strip() if industry_col and pd.notna(row[industry_col]) else '',
                    'percentage': percentage,
                    'is_foreign': self._is_foreign_stock(row[isin_col] if isin_col else '')
                }
                
                holdings.append(holding)
                
            except Exception as e:
                logger.debug(f"Error parsing row {idx}: {e}")
                continue
        
        return holdings
    
    def _extract_section_based(self, df: pd.DataFrame) -> List[Dict]:
        """Extract from section-based format (like PPFAS)"""
        
        # This is handled by the PPFAS parser
        # Could add more section-based parsers here for other AMCs
        return []
    
    def _find_header_row(self, df: pd.DataFrame) -> Optional[int]:
        """Find the row that contains column headers"""
        
        for idx, row in df.iterrows():
            row_str = ' '.join([str(val).lower() for val in row.values if pd.notna(val)])
            
            # Check if this row contains typical header keywords
            if any(col in row_str for col in ['name', 'isin', 'instrument', 'percentage', 'assets']):
                return idx
        
        return None
    
    def _find_column(self, columns, possible_names: List[str]) -> Optional[str]:
        """Find a column by matching against possible names"""
        
        for col in columns:
            if pd.isna(col):
                continue
            
            col_lower = str(col).lower().strip()
            
            for possible_name in possible_names:
                if possible_name in col_lower:
                    return col
        
        return None
    
    def _extract_percentage(self, value) -> Optional[float]:
        """Extract percentage value from various formats"""
        
        if pd.isna(value):
            return None
        
        try:
            # If it's already a number
            if isinstance(value, (int, float)):
                # If between 0 and 1, convert to percentage
                if 0 < value <= 1:
                    return float(value) * 100
                elif 1 < value <= 100:
                    return float(value)
                elif value > 100:
                    # Might be in basis points or incorrect, cap at 100
                    return min(float(value), 100.0)
            
            # If it's a string, try to extract number
            value_str = str(value).strip()
            
            # Remove % sign
            value_str = value_str.replace('%', '')
            
            # Try to convert to float
            pct = float(value_str)
            
            # Normalize to 0-100 range
            if 0 < pct <= 1:
                return pct * 100
            elif 1 < pct <= 100:
                return pct
            elif pct > 100:
                # Might be in basis points or incorrect, cap at 100
                return min(pct, 100.0)
            
        except (ValueError, TypeError):
            pass
        
        return None
    
    def _is_equity_holding(self, name: str, row: pd.Series) -> bool:
        """Check if this is an equity holding (not debt/bond)"""
        
        name_lower = name.lower()
        
        # Exclude debt instruments
        debt_keywords = ['ncd', 'bond', 'debenture', 'treasury', 'tbill', 't-bill', 'sdl', 'government']
        if any(keyword in name_lower for keyword in debt_keywords):
            return False
        
        # Exclude REITs/InvITs (optional - depends on requirement)
        # if 'reit' in name_lower or 'invit' in name_lower:
        #     return False
        
        return True
    
    def _is_foreign_stock(self, isin: str) -> bool:
        """Check if stock is foreign based on ISIN"""
        
        if not isin or pd.isna(isin):
            return False
        
        isin_str = str(isin).strip()
        
        # Indian ISINs start with INE
        if isin_str.startswith('INE'):
            return False
        
        # US ISINs start with US
        if isin_str.startswith('US'):
            return True
        
        # Other foreign ISINs (2-letter country code)
        if len(isin_str) >= 2 and isin_str[:2].isalpha() and isin_str[:2] != 'IN':
            return True
        
        return False
    
    def _clean_company_name(self, name: str) -> str:
        """Clean up company name"""
        
        # Remove common suffixes
        name = re.sub(r'\s+(Limited|Ltd|Ltd\.|Corporation|Corp|Inc|Pvt|Pvt\.)$', '', name, flags=re.IGNORECASE)
        
        # Remove extra whitespace
        name = ' '.join(name.split())
        
        return name.strip()


def parse_portfolio(excel_path: str) -> List[Dict]:
    """
    Convenience function to parse any mutual fund portfolio Excel
    
    Args:
        excel_path: Path to the Excel file
        
    Returns:
        List of holdings with name, isin, industry, percentage, is_foreign
    """
    parser = GenericPortfolioParser(excel_path)
    return parser.parse()


# Test function
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        excel_path = sys.argv[1]
    else:
        excel_path = "../statements/mfs/PPFCF_PPFAS_Monthly_Portfolio_Report_January_31_2026.xls"
    
    print(f"Parsing: {excel_path}\n")
    
    try:
        holdings = parse_portfolio(excel_path)
        
        if holdings:
            # Separate domestic and foreign
            domestic = [h for h in holdings if not h.get('is_foreign', False)]
            foreign = [h for h in holdings if h.get('is_foreign', False)]
            
            print(f"Found {len(domestic)} domestic and {len(foreign)} foreign holdings\n")
            
            print(f"{'Company Name':<50} {'ISIN':<15} {'%':<10}")
            print("=" * 75)
            
            for holding in holdings[:20]:  # Show first 20
                print(f"{holding['name']:<50} {holding.get('isin', ''):<15} {holding['percentage']:>6.2f}%")
        else:
            print("No holdings found")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

# Made with Bob
