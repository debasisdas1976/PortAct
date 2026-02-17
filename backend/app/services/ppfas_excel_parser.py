"""
Parag Parikh Mutual Fund Excel Portfolio Parser
Extracts equity holdings from PPFAS monthly portfolio Excel files
"""
import pandas as pd
from typing import List, Dict, Optional
import re


class PPFASExcelParser:
    """Parser for Parag Parikh monthly portfolio Excel files"""
    
    def __init__(self, excel_path: str):
        self.excel_path = excel_path
        self.holdings: List[Dict] = []
        
    def parse(self) -> List[Dict]:
        """
        Parse the Excel file and extract equity holdings
        
        Returns:
            List of dicts with keys: name, isin, industry, percentage, is_foreign
        """
        try:
            # Read the Excel file
            df = pd.read_excel(self.excel_path, sheet_name=0)
            
            # Find the start of domestic equity section
            domestic_start = None
            foreign_start = None
            
            for idx, row in df.iterrows():
                row_str = ' '.join([str(val) for val in row.values if pd.notna(val)])
                
                if 'Equity & Equity related' in row_str and 'Foreign' not in row_str:
                    domestic_start = idx
                elif 'Equity & Equity related Foreign' in row_str:
                    foreign_start = idx
                    break
            
            # Extract domestic equity holdings
            if domestic_start is not None:
                self._extract_equity_section(df, domestic_start, foreign_start, is_foreign=False)
            
            # Extract foreign equity holdings
            if foreign_start is not None:
                # Find where foreign section ends (look for next major section)
                foreign_end = None
                for idx in range(foreign_start + 1, len(df)):
                    row_str = ' '.join([str(val) for val in df.iloc[idx].values if pd.notna(val)])
                    if 'Debt' in row_str or 'Money Market' in row_str or 'GRAND TOTAL' in row_str:
                        foreign_end = idx
                        break
                
                self._extract_equity_section(df, foreign_start, foreign_end, is_foreign=True)
            
            return self.holdings
            
        except Exception as e:
            raise Exception(f"Error parsing PPFAS Excel file: {str(e)}")
    
    def _extract_equity_section(self, df: pd.DataFrame, start_idx: int, end_idx: Optional[int], is_foreign: bool):
        """Extract equity holdings from a section of the dataframe"""
        
        # Skip header rows and find the data start
        data_start = start_idx + 1
        
        # Look for the row with column headers (Name of the Instrument, ISIN, etc.)
        for idx in range(start_idx, min(start_idx + 10, len(df))):
            row_str = ' '.join([str(val) for val in df.iloc[idx].values if pd.notna(val)])
            if 'Name of the Instrument' in row_str or 'ISIN' in row_str:
                data_start = idx + 1
                break
        
        # Extract data rows
        if end_idx is None:
            end_idx = len(df)
        
        for idx in range(data_start, end_idx):
            row = df.iloc[idx]
            
            # Stop at subtotal or total rows
            row_str = ' '.join([str(val) for val in row.values if pd.notna(val)])
            if any(keyword in row_str for keyword in ['Sub Total', 'Total', 'TOTAL', 'Sub total']):
                break
            
            # Extract holding data
            holding = self._parse_holding_row(row, is_foreign)
            
            if holding:
                self.holdings.append(holding)
    
    def _parse_holding_row(self, row: pd.Series, is_foreign: bool) -> Optional[Dict]:
        """Parse a single row to extract holding information"""
        
        # The Excel structure typically has:
        # Column 0: Code (optional)
        # Column 1: Name of Instrument
        # Column 2: ISIN
        # Column 3: Industry/Rating
        # Column 4: Quantity
        # Column 5: Market Value
        # Column 6: % to Net Assets
        
        try:
            # Get values from row
            values = row.values
            
            # Find the name (usually in column 1, but could be column 0 if no code)
            name = None
            isin = None
            industry = None
            percentage = None
            
            for i, val in enumerate(values):
                if pd.isna(val):
                    continue
                
                val_str = str(val).strip()
                
                # ISIN pattern: INE followed by alphanumeric
                if re.match(r'INE[A-Z0-9]+', val_str):
                    isin = val_str
                    # Name is usually before ISIN
                    if i > 0 and pd.notna(values[i-1]):
                        name = str(values[i-1]).strip()
                    # Industry is usually after ISIN
                    if i < len(values) - 1 and pd.notna(values[i+1]):
                        industry_val = str(values[i+1]).strip()
                        # Make sure it's not a number
                        if not re.match(r'^\d+\.?\d*$', industry_val):
                            industry = industry_val
                
                # Percentage pattern: decimal number between 0 and 1 or 0 and 100
                if isinstance(val, (int, float)) and 0 < val < 1:
                    percentage = float(val) * 100  # Convert to percentage
                elif isinstance(val, (int, float)) and 1 <= val <= 100:
                    percentage = float(val)
            
            # For foreign stocks, ISIN might be different format (US stocks)
            if is_foreign and not isin:
                for i, val in enumerate(values):
                    if pd.isna(val):
                        continue
                    val_str = str(val).strip()
                    # US stock pattern: letters followed by numbers
                    if re.match(r'^[A-Z]{1,5}\d+$', val_str) or re.match(r'^US[A-Z0-9]+$', val_str):
                        isin = val_str
                        if i > 0 and pd.notna(values[i-1]):
                            name = str(values[i-1]).strip()
                        if i < len(values) - 1 and pd.notna(values[i+1]):
                            industry_val = str(values[i+1]).strip()
                            if not re.match(r'^\d+\.?\d*$', industry_val):
                                industry = industry_val
            
            # Validate we have minimum required data
            if not name or not percentage:
                return None
            
            # Clean up name
            name = self._clean_company_name(name)
            
            # Skip if name looks like a header or total
            if any(keyword in name.lower() for keyword in ['total', 'sub total', 'listed', 'awaiting', 'name of']):
                return None
            
            return {
                'name': name,
                'isin': isin or '',
                'industry': industry or '',
                'percentage': round(percentage, 2),
                'is_foreign': is_foreign
            }
            
        except Exception as e:
            # Skip rows that can't be parsed
            return None
    
    def _clean_company_name(self, name: str) -> str:
        """Clean up company name"""
        # Remove common suffixes
        name = re.sub(r'\s+(Limited|Ltd|Ltd\.|Corporation|Corp|Inc|Pvt|Pvt\.)$', '', name, flags=re.IGNORECASE)
        
        # Remove extra whitespace
        name = ' '.join(name.split())
        
        return name.strip()


def parse_ppfas_excel(excel_path: str) -> List[Dict]:
    """
    Convenience function to parse PPFAS Excel portfolio
    
    Args:
        excel_path: Path to the Excel file
        
    Returns:
        List of holdings with name, isin, industry, percentage, and is_foreign flag
    """
    parser = PPFASExcelParser(excel_path)
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
        holdings = parse_ppfas_excel(excel_path)
        
        # Separate domestic and foreign
        domestic = [h for h in holdings if not h['is_foreign']]
        foreign = [h for h in holdings if h['is_foreign']]
        
        print(f"Found {len(domestic)} domestic equity holdings:\n")
        print(f"{'Company Name':<50} {'ISIN':<15} {'Industry':<35} {'%':<10}")
        print("=" * 110)
        
        total_domestic = 0
        for holding in domestic:
            print(f"{holding['name']:<50} {holding['isin']:<15} {holding['industry']:<35} {holding['percentage']:>6.2f}%")
            total_domestic += holding['percentage']
        
        print("=" * 110)
        print(f"{'Total Domestic Equity':<100} {total_domestic:>6.2f}%\n")
        
        print(f"\nFound {len(foreign)} foreign equity holdings:\n")
        print(f"{'Company Name':<50} {'ISIN':<15} {'Industry':<35} {'%':<10}")
        print("=" * 110)
        
        total_foreign = 0
        for holding in foreign:
            print(f"{holding['name']:<50} {holding['isin']:<15} {holding['industry']:<35} {holding['percentage']:>6.2f}%")
            total_foreign += holding['percentage']
        
        print("=" * 110)
        print(f"{'Total Foreign Equity':<100} {total_foreign:>6.2f}%")
        
        print(f"\n{'GRAND TOTAL EQUITY':<100} {total_domestic + total_foreign:>6.2f}%")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

# Made with Bob
