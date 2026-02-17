"""
Consolidated MF Holdings Parser
Parses a single Excel file with multiple tabs, each containing a different mutual fund's holdings
"""
import pandas as pd
import re
from typing import List, Dict, Tuple, Optional
import logging
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class ConsolidatedMFParser:
    """Parser for consolidated MF holdings Excel file with multiple tabs"""
    
    def __init__(self, excel_path: str):
        self.excel_path = excel_path
        
    def parse_all_funds(self) -> Dict[str, List[Dict]]:
        """
        Parse all tabs in the Excel file
        
        Returns:
            Dict mapping fund name to list of holdings
        """
        try:
            # Read Excel file with explicit engine
            xls = pd.ExcelFile(self.excel_path, engine='openpyxl')
            
            all_funds = {}
            
            for sheet_name in xls.sheet_names:
                logger.info(f"Processing sheet: {sheet_name}")
                
                try:
                    # Read the sheet WITHOUT header to get raw data including first row
                    df_raw = pd.read_excel(
                        self.excel_path,
                        sheet_name=sheet_name,
                        engine='openpyxl',
                        header=None
                    )
                    
                    # Extract fund name from the raw sheet (including first row)
                    fund_name = self._extract_fund_name(df_raw, sheet_name)
                    
                    # Now read again with default settings for holdings extraction
                    df = pd.read_excel(
                        self.excel_path,
                        sheet_name=sheet_name,
                        engine='openpyxl'
                    )
                    
                    if not fund_name:
                        logger.warning(f"Could not extract fund name from sheet: {sheet_name}")
                        continue
                    
                    # Extract holdings
                    holdings = self._extract_holdings(df)
                    
                    if holdings:
                        all_funds[fund_name] = holdings
                        logger.info(f"Extracted {len(holdings)} holdings for: {fund_name}")
                    else:
                        logger.warning(f"No holdings found in sheet: {sheet_name}")
                        
                except Exception as e:
                    logger.error(f"Error processing sheet {sheet_name}: {e}")
                    continue
            
            return all_funds
            
        except Exception as e:
            logger.error(f"Error reading Excel file: {e}")
            raise
    
    def _extract_fund_name(self, df: pd.DataFrame, sheet_name: str) -> Optional[str]:
        """
        Extract fund name from the dataframe
        Usually in the first row (row 0)
        """
        # Strategy 1: Check the very first row (row 0) for fund name
        # Fund names are typically in column 0 or 1 of the first row
        if len(df) > 0:
            first_row = df.iloc[0]
            for cell in first_row:
                if pd.isna(cell):
                    continue
                
                cell_str = str(cell).strip()
                
                # Look for fund name patterns (must contain "fund" or "scheme")
                if any(keyword in cell_str.lower() for keyword in ['fund', 'scheme']):
                    # Must be reasonably long
                    if len(cell_str) > 15:
                        fund_name = self._clean_fund_name(cell_str)
                        if len(fund_name) > 10:
                            logger.info(f"Extracted fund name from first row: {fund_name}")
                            return fund_name
        
        # Strategy 2: Look for "Monthly Portfolio Statement" or similar headers
        # The fund name might be nearby
        for i in range(min(10, len(df))):
            row = df.iloc[i]
            row_str = ' '.join([str(cell) for cell in row if pd.notna(cell)]).strip()
            
            # Check if this row contains "Monthly Portfolio Statement" or similar
            if any(keyword in row_str.lower() for keyword in [
                'monthly portfolio statement', 'portfolio statement',
                'scheme name', 'fund name'
            ]):
                # The fund name might be in the same row or previous rows
                for j in range(max(0, i-2), min(i + 3, len(df))):
                    check_row = df.iloc[j]
                    for cell in check_row:
                        if pd.isna(cell):
                            continue
                        cell_str = str(cell).strip()
                        
                        # Look for fund name patterns
                        if any(keyword in cell_str.lower() for keyword in ['fund', 'scheme']):
                            # Must be reasonably long and not a header
                            if len(cell_str) > 15 and 'statement' not in cell_str.lower():
                                fund_name = self._clean_fund_name(cell_str)
                                if len(fund_name) > 10:
                                    logger.info(f"Extracted fund name from row {j}: {fund_name}")
                                    return fund_name
        
        # Strategy 3: Look in first 10 rows for any cell with fund keywords
        for i in range(min(10, len(df))):
            row = df.iloc[i]
            
            for cell in row:
                if pd.isna(cell):
                    continue
                    
                cell_str = str(cell).strip()
                
                # Look for fund name patterns
                if any(keyword in cell_str.lower() for keyword in [
                    'fund', 'scheme', 'plan'
                ]) and len(cell_str) > 15:
                    # Skip if it's a header or label
                    if any(skip in cell_str.lower() for skip in [
                        'statement', 'name of', 'scheme name', 'fund name', 'back to'
                    ]):
                        continue
                    
                    # Clean up the fund name
                    fund_name = self._clean_fund_name(cell_str)
                    if len(fund_name) > 10:  # Reasonable length for a fund name
                        logger.info(f"Extracted fund name from row {i}: {fund_name}")
                        return fund_name
        
        # Strategy 4: Use sheet name if it looks like a fund name
        if len(sheet_name) > 5 and any(keyword in sheet_name.lower() for keyword in [
            'fund', 'scheme', 'plan'
        ]):
            return self._clean_fund_name(sheet_name)
        
        # Strategy 5: Return sheet name as fallback
        logger.warning(f"Using sheet name as fund name: {sheet_name}")
        return sheet_name
    
    def _clean_fund_name(self, name: str) -> str:
        """Clean and normalize fund name"""
        # Remove extra whitespace
        name = ' '.join(name.split())
        
        # Remove common prefixes/suffixes
        name = re.sub(r'^(Scheme Name|Fund Name|Name)[\s:]+', '', name, flags=re.IGNORECASE)
        
        return name.strip()
    
    def _extract_holdings(self, df: pd.DataFrame) -> List[Dict]:
        """Extract equity holdings from the dataframe"""
        
        holdings = []
        raw_holdings = []  # Store raw data first for validation
        
        # Find the header row (contains column names like "Name", "ISIN", "%" etc.)
        header_row_idx = self._find_header_row(df)
        
        if header_row_idx is None:
            logger.warning("Could not find header row")
            return []
        
        # Set the header
        df.columns = df.iloc[header_row_idx]
        df = df.iloc[header_row_idx + 1:]
        
        # Find column indices
        name_col = self._find_column(df.columns, [
            'name of the instrument', 'instrument name', 'stock name', 
            'company name', 'security name', 'name', 'scrip name', 'instrument'
        ])
        
        isin_col = self._find_column(df.columns, [
            'isin', 'isin code', 'isin number'
        ])
        
        pct_col = self._find_column(df.columns, [
            '% to net assets', 'percentage', '% of nav', '% to nav',
            'weightage', 'allocation', '% allocation', '%'
        ])
        
        industry_col = self._find_column(df.columns, [
            'industry', 'sector', 'industry / rating', 'rating', 'classification'
        ])
        
        if name_col is None or pct_col is None:
            logger.warning("Could not find required columns (name and percentage)")
            return []
        
        # Extract holdings
        for idx, row in df.iterrows():
            try:
                name = str(row[name_col]).strip() if pd.notna(row[name_col]) else None
                
                if not name or name.lower() in ['nan', 'total', 'grand total', '']:
                    continue
                
                # Skip if it looks like a section header
                if any(keyword in name.lower() for keyword in [
                    'equity', 'debt', 'total', 'sub-total', 'grand total',
                    'money market', 'cash', 'net assets'
                ]):
                    continue
                
                # Get percentage
                pct_value = row[pct_col]
                if pd.isna(pct_value):
                    continue
                
                try:
                    # Check if original value contains % symbol
                    original_str = str(pct_value)
                    has_percent_symbol = '%' in original_str
                    
                    # Remove % symbol and convert to float
                    pct_str = original_str.replace('%', '').strip()
                    percentage = float(pct_str)
                    
                    # Store raw percentage for later validation
                    raw_percentage = percentage
                    
                    # Apply different logic based on whether % symbol was present
                    if has_percent_symbol:
                        # Data has % symbol (e.g., "8.5%")
                        # The value is already in percentage format, use as-is
                        # If it's in decimal format (0.085%), multiply by 100
                        if 0 < percentage < 1:
                            percentage = percentage * 100
                    else:
                        # Data does NOT have % symbol (e.g., "8.5" or "0.085")
                        # Store as-is for now, we'll validate total later
                        if 0 < percentage < 1:
                            # Decimal format without % symbol (0.085 means 8.5%)
                            percentage = percentage * 100
                        # For values 1-100, keep as-is for now (will validate total later)
                        elif percentage > 100:
                            # Likely in basis points (850 = 8.5%)
                            if percentage <= 10000:
                                percentage = percentage / 100
                            else:
                                logger.warning(f"Skipping holding with invalid percentage: {percentage}")
                                continue
                        
                except Exception as e:
                    logger.debug(f"Error parsing percentage: {e}")
                    continue
                
                # Skip if percentage is 0 or negative
                if percentage <= 0:
                    continue
                
                # Get ISIN
                isin = ''
                if isin_col and pd.notna(row[isin_col]):
                    isin = str(row[isin_col]).strip()
                
                # Get industry
                industry = ''
                if industry_col and pd.notna(row[industry_col]):
                    industry = str(row[industry_col]).strip()
                
                # Check if it's a foreign stock (non-Indian ISIN)
                is_foreign = self._is_foreign_stock(isin)
                
                raw_holdings.append({
                    'name': name,
                    'isin': isin,
                    'percentage': percentage,
                    'raw_percentage': raw_percentage,
                    'has_percent_symbol': has_percent_symbol,
                    'industry': industry,
                    'sector': industry,
                    'is_foreign': is_foreign
                })
                
            except Exception as e:
                logger.debug(f"Error processing row {idx}: {e}")
                continue
        
        # Validate total percentage and adjust if needed
        if raw_holdings:
            total_pct = sum(h['percentage'] for h in raw_holdings)
            
            # If total is way over 100% and data doesn't have % symbols, divide by 100
            if total_pct > 150:
                # Check if most holdings don't have % symbol
                no_percent_count = sum(1 for h in raw_holdings if not h['has_percent_symbol'])
                if no_percent_count > len(raw_holdings) * 0.5:  # More than 50% without % symbol
                    logger.info(f"Total percentage is {total_pct:.2f}%, dividing all by 100")
                    for h in raw_holdings:
                        h['percentage'] = h['percentage'] / 100
            
            # Create final holdings list without metadata
            for h in raw_holdings:
                holdings.append({
                    'name': h['name'],
                    'isin': h['isin'],
                    'percentage': h['percentage'],
                    'industry': h['industry'],
                    'sector': h['sector'],
                    'is_foreign': h['is_foreign']
                })
        
        return holdings
    
    def _find_header_row(self, df: pd.DataFrame) -> Optional[int]:
        """Find the row that contains column headers"""
        
        header_keywords = [
            'name', 'isin', 'percentage', '%', 'instrument', 'security',
            'stock', 'company', 'scrip'
        ]
        
        for idx in range(min(20, len(df))):
            row = df.iloc[idx]
            row_str = ' '.join([str(cell).lower() for cell in row if pd.notna(cell)])
            
            # Check if this row contains multiple header keywords
            matches = sum(1 for keyword in header_keywords if keyword in row_str)
            
            if matches >= 2:  # At least 2 header keywords found
                return idx
        
        return None
    
    def _find_column(self, columns, possible_names: List[str]) -> Optional[str]:
        """Find a column by matching against possible names"""
        
        columns_lower = {str(col).lower().strip(): col for col in columns if pd.notna(col)}
        
        for possible_name in possible_names:
            possible_lower = possible_name.lower().strip()
            
            # Exact match
            if possible_lower in columns_lower:
                return columns_lower[possible_lower]
            
            # Partial match
            for col_lower, col_original in columns_lower.items():
                if possible_lower in col_lower or col_lower in possible_lower:
                    return col_original
        
        return None
    
    def _is_foreign_stock(self, isin: str) -> bool:
        """Check if stock is foreign based on ISIN"""
        if not isin or len(isin) < 2:
            return False
        
        # Indian ISINs start with 'IN'
        return not isin.upper().startswith('IN')


def match_fund_to_asset(fund_name: str, asset_names: List[str]) -> Tuple[Optional[str], float]:
    """
    Match a fund name from Excel to an asset name from database
    
    Returns:
        Tuple of (matched_asset_name, similarity_score)
    """
    if not asset_names:
        return None, 0.0
    
    # Normalize fund name
    fund_normalized = fund_name.lower().strip()
    fund_normalized = re.sub(r'[^\w\s]', ' ', fund_normalized)
    fund_normalized = ' '.join(fund_normalized.split())
    
    best_match = None
    best_score = 0.0
    
    for asset_name in asset_names:
        # Normalize asset name
        asset_normalized = asset_name.lower().strip()
        asset_normalized = re.sub(r'[^\w\s]', ' ', asset_normalized)
        asset_normalized = ' '.join(asset_normalized.split())
        
        # Calculate similarity
        score = SequenceMatcher(None, fund_normalized, asset_normalized).ratio()
        
        # Boost score if key words match
        fund_words = set(fund_normalized.split())
        asset_words = set(asset_normalized.split())
        common_words = fund_words & asset_words
        
        # Boost for matching important words
        important_words = {'direct', 'growth', 'dividend', 'regular', 'plan'}
        important_matches = common_words & important_words
        
        if important_matches:
            score += 0.1 * len(important_matches)
        
        if score > best_score:
            best_score = score
            best_match = asset_name
    
    return best_match, best_score


# Test function
if __name__ == "__main__":
    parser = ConsolidatedMFParser("../statements/mfs/MF-Holdings.xlsx")
    
    print("Parsing consolidated MF holdings file...\n")
    
    all_funds = parser.parse_all_funds()
    
    print(f"Found {len(all_funds)} funds:\n")
    
    for fund_name, holdings in all_funds.items():
        print(f"\n{fund_name}:")
        print(f"  Holdings: {len(holdings)}")
        
        if holdings:
            print(f"  Sample holdings:")
            for holding in holdings[:3]:
                print(f"    - {holding['name']}: {holding['percentage']}%")

# Made with Bob
