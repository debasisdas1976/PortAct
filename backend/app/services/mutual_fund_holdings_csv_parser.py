"""
Service to parse mutual fund portfolio holdings from CSV files
"""
import csv
import io
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class MutualFundHoldingsCSVParser:
    """Parser for mutual fund portfolio holdings CSV files"""
    
    @staticmethod
    def parse_csv(file_content: bytes) -> List[Dict[str, Any]]:
        """
        Parse CSV file containing mutual fund portfolio holdings
        
        Expected CSV format:
        Stock Name, Symbol, ISIN, Holding %, Sector, Industry, Market Cap
        
        OR
        
        Stock Name, Holding %
        
        Returns:
            List of holdings dictionaries
        """
        holdings = []
        raw_holdings = []  # Store raw data first for validation
        
        try:
            # Decode bytes to string
            content = file_content.decode('utf-8-sig')  # utf-8-sig handles BOM
            
            # Parse CSV
            csv_reader = csv.DictReader(io.StringIO(content))
            
            for row in csv_reader:
                # Skip empty rows
                if not any(row.values()):
                    continue
                
                # Try to extract stock name and holding percentage
                stock_name = None
                holding_pct = 0.0
                raw_pct = 0.0
                has_percent_symbol = False
                
                # Look for stock name in various column names
                for key in ['Stock Name', 'stock_name', 'Name', 'name', 'Company', 'company', 'Holding', 'holding']:
                    if key in row and row[key]:
                        stock_name = row[key].strip()
                        break
                
                # Look for holding percentage
                for key in ['Holding %', 'holding_pct', 'Percentage', 'percentage', '% of AUM', 'Weight', 'weight']:
                    if key in row and row[key]:
                        try:
                            # Check if original value contains % symbol
                            original_str = str(row[key]).strip()
                            has_percent_symbol = '%' in original_str
                            
                            # Remove % sign and commas, convert to float
                            pct_str = original_str.replace('%', '').replace(',', '').strip()
                            holding_pct = float(pct_str)
                            raw_pct = holding_pct  # Store raw value
                            
                            # Apply different logic based on whether % symbol was present
                            if has_percent_symbol:
                                # Data has % symbol (e.g., "8.5%")
                                # The value is already in percentage format, use as-is
                                # If it's in decimal format (0.085%), multiply by 100
                                if 0 < holding_pct < 1:
                                    holding_pct = holding_pct * 100
                            else:
                                # Data does NOT have % symbol (e.g., "8.5" or "0.085")
                                if 0 < holding_pct < 1:
                                    # Decimal format without % symbol (0.085 means 8.5%)
                                    holding_pct = holding_pct * 100
                                # For values 1-100, keep as-is for now (will validate total later)
                                elif holding_pct > 100:
                                    # Likely in basis points (850 = 8.5%)
                                    if holding_pct <= 10000:
                                        holding_pct = holding_pct / 100
                                    else:
                                        logger.warning(f"Skipping holding with invalid percentage: {holding_pct}")
                                        holding_pct = 0
                            
                            # Skip if invalid
                            if holding_pct <= 0:
                                holding_pct = 0
                            
                            break
                        except (ValueError, AttributeError) as e:
                            logger.debug(f"Error parsing percentage: {e}")
                            continue
                
                if not stock_name or holding_pct <= 0:
                    continue
                
                # Store raw holding data
                raw_holdings.append({
                    'stock_name': stock_name,
                    'holding_percentage': holding_pct,
                    'raw_percentage': raw_pct,
                    'has_percent_symbol': has_percent_symbol,
                    'stock_symbol': row.get('Symbol') or row.get('symbol') or row.get('Ticker'),
                    'isin': row.get('ISIN') or row.get('isin'),
                    'sector': row.get('Sector') or row.get('sector'),
                    'industry': row.get('Industry') or row.get('industry'),
                    'market_cap': row.get('Market Cap') or row.get('market_cap') or row.get('Cap')
                })
            
            # Validate total percentage and adjust if needed
            if raw_holdings:
                total_pct = sum(h['holding_percentage'] for h in raw_holdings)
                
                # If total is way over 100% and data doesn't have % symbols, divide by 100
                if total_pct > 150:
                    # Check if most holdings don't have % symbol
                    no_percent_count = sum(1 for h in raw_holdings if not h['has_percent_symbol'])
                    if no_percent_count > len(raw_holdings) * 0.5:  # More than 50% without % symbol
                        logger.info(f"Total percentage is {total_pct:.2f}%, dividing all by 100")
                        for h in raw_holdings:
                            h['holding_percentage'] = h['holding_percentage'] / 100
                
                # Create final holdings list without metadata
                for h in raw_holdings:
                    holdings.append({
                        'stock_name': h['stock_name'],
                        'holding_percentage': h['holding_percentage'],
                        'stock_symbol': h['stock_symbol'],
                        'isin': h['isin'],
                        'sector': h['sector'],
                        'industry': h['industry'],
                        'market_cap': h['market_cap']
                    })
            
            logger.info(f"Parsed {len(holdings)} holdings from CSV")
            return holdings
            
        except Exception as e:
            logger.error(f"Error parsing CSV: {str(e)}")
            raise ValueError(f"Failed to parse CSV file: {str(e)}")
    
    @staticmethod
    def validate_holdings(holdings: List[Dict[str, Any]]) -> tuple[bool, str]:
        """
        Validate parsed holdings data
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not holdings:
            return False, "No holdings found in CSV file"
        
        # Check if total percentage is reasonable (should be close to 100% or less)
        total_pct = sum(h['holding_percentage'] for h in holdings)
        
        if total_pct > 150:
            return False, f"Total holding percentage ({total_pct:.2f}%) seems incorrect. Should be ≤ 100%"
        
        # Check for duplicate stock names
        stock_names = [h['stock_name'] for h in holdings]
        if len(stock_names) != len(set(stock_names)):
            return False, "Duplicate stock names found in CSV"
        
        return True, "Validation successful"
    
    @staticmethod
    def generate_sample_csv() -> str:
        """Generate a sample CSV template"""
        return """Stock Name,Symbol,ISIN,Holding %,Sector,Industry,Market Cap
Reliance Industries Ltd,RELIANCE,INE002A01018,8.5,Energy,Oil & Gas,Large Cap
HDFC Bank Ltd,HDFCBANK,INE040A01034,7.2,Financials,Banking,Large Cap
Infosys Ltd,INFY,INE009A01021,6.8,Information Technology,IT Services,Large Cap
ICICI Bank Ltd,ICICIBANK,INE090A01021,5.9,Financials,Banking,Large Cap
TCS Ltd,TCS,INE467B01029,5.5,Information Technology,IT Services,Large Cap"""


# Made with Bob