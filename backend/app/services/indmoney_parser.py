"""
Parser for INDMoney broker statements (US stocks)
Supports CSV and Excel formats from INDMoney
"""
import pandas as pd
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class INDMoneyParser:
    """Parser for INDMoney broker statements"""
    
    @staticmethod
    def parse_statement(file_path: str) -> Tuple[List[Dict], float]:
        """
        Parse INDMoney statement file
        
        Args:
            file_path: Path to the statement file
            
        Returns:
            Tuple of (list of holdings, cash balance in USD)
        """
        file_ext = file_path.lower().split('.')[-1]
        
        if file_ext == 'csv':
            return INDMoneyParser._parse_csv(file_path)
        elif file_ext in ['xlsx', 'xls']:
            return INDMoneyParser._parse_excel(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")
    
    @staticmethod
    def _parse_csv(file_path: str) -> Tuple[List[Dict], float]:
        """
        Parse INDMoney CSV statement
        
        Expected format:
        - Holdings section with columns: Symbol, Name, Quantity, Average Price, Current Price, Market Value, etc.
        - Cash balance information
        
        Returns:
            Tuple of (list of holdings, cash balance in USD)
        """
        holdings = []
        cash_balance = 0.0
        
        try:
            # Read CSV file
            df = pd.read_csv(file_path)
            
            # Clean column names
            df.columns = df.columns.str.strip()
            
            # Look for cash balance
            cash_balance = INDMoneyParser._extract_cash_balance(df)
            
            # Parse holdings
            # Common column names in INDMoney statements
            symbol_col = INDMoneyParser._find_column(df, ['Symbol', 'Ticker', 'Stock Symbol', 'Stock'])
            name_col = INDMoneyParser._find_column(df, ['Name', 'Company Name', 'Stock Name', 'Company'])
            quantity_col = INDMoneyParser._find_column(df, ['Quantity', 'Shares', 'Qty', 'Units'])
            avg_price_col = INDMoneyParser._find_column(df, ['Average Price', 'Avg Price', 'Buy Price', 'Purchase Price', 'Cost'])
            current_price_col = INDMoneyParser._find_column(df, ['Current Price', 'Market Price', 'LTP', 'Last Price', 'Price'])
            market_value_col = INDMoneyParser._find_column(df, ['Market Value', 'Current Value', 'Value', 'Total Value'])
            
            if not symbol_col or not quantity_col:
                logger.warning("Could not find required columns in INDMoney CSV")
                return holdings, cash_balance
            
            # Process each row
            for idx, row in df.iterrows():
                try:
                    symbol = str(row[symbol_col]).strip()
                    
                    # Skip empty rows or summary rows
                    if pd.isna(symbol) or symbol.upper() in ['TOTAL', 'CASH', 'BALANCE', '', 'SUMMARY']:
                        continue
                    
                    quantity = float(row[quantity_col]) if pd.notna(row[quantity_col]) else 0.0
                    
                    if quantity <= 0:
                        continue
                    
                    # Extract other fields
                    name = str(row[name_col]).strip() if name_col and pd.notna(row[name_col]) else symbol
                    avg_price = float(row[avg_price_col]) if avg_price_col and pd.notna(row[avg_price_col]) else 0.0
                    current_price = float(row[current_price_col]) if current_price_col and pd.notna(row[current_price_col]) else 0.0
                    market_value = float(row[market_value_col]) if market_value_col and pd.notna(row[market_value_col]) else (quantity * current_price)
                    
                    holding = {
                        'symbol': symbol,
                        'name': name,
                        'quantity': quantity,
                        'average_cost_usd': avg_price,
                        'current_price_usd': current_price,
                        'market_value_usd': market_value,
                        'total_invested_usd': quantity * avg_price if avg_price > 0 else market_value
                    }
                    
                    holdings.append(holding)
                    logger.info(f"Parsed INDMoney holding: {symbol} - {quantity} shares")
                    
                except Exception as e:
                    logger.error(f"Error parsing row {idx}: {str(e)}")
                    continue
            
        except Exception as e:
            logger.error(f"Error parsing INDMoney CSV: {str(e)}")
            raise
        
        return holdings, cash_balance
    
    @staticmethod
    def _parse_excel(file_path: str) -> Tuple[List[Dict], float]:
        """
        Parse INDMoney Excel statement
        
        Returns:
            Tuple of (list of holdings, cash balance in USD)
        """
        holdings = []
        cash_balance = 0.0
        
        try:
            # Try to read the first sheet
            df = pd.read_excel(file_path, sheet_name=0)
            
            # Clean column names
            df.columns = df.columns.str.strip()
            
            # Extract cash balance
            cash_balance = INDMoneyParser._extract_cash_balance(df)
            
            # Parse holdings (similar to CSV)
            symbol_col = INDMoneyParser._find_column(df, ['Symbol', 'Ticker', 'Stock Symbol', 'Stock'])
            name_col = INDMoneyParser._find_column(df, ['Name', 'Company Name', 'Stock Name', 'Company'])
            quantity_col = INDMoneyParser._find_column(df, ['Quantity', 'Shares', 'Qty', 'Units'])
            avg_price_col = INDMoneyParser._find_column(df, ['Average Price', 'Avg Price', 'Buy Price', 'Purchase Price', 'Cost'])
            current_price_col = INDMoneyParser._find_column(df, ['Current Price', 'Market Price', 'LTP', 'Last Price', 'Price'])
            market_value_col = INDMoneyParser._find_column(df, ['Market Value', 'Current Value', 'Value', 'Total Value'])
            
            if not symbol_col or not quantity_col:
                logger.warning("Could not find required columns in INDMoney Excel")
                return holdings, cash_balance
            
            # Process each row
            for idx, row in df.iterrows():
                try:
                    symbol = str(row[symbol_col]).strip()
                    
                    if pd.isna(symbol) or symbol.upper() in ['TOTAL', 'CASH', 'BALANCE', '', 'SUMMARY']:
                        continue
                    
                    quantity = float(row[quantity_col]) if pd.notna(row[quantity_col]) else 0.0
                    
                    if quantity <= 0:
                        continue
                    
                    name = str(row[name_col]).strip() if name_col and pd.notna(row[name_col]) else symbol
                    avg_price = float(row[avg_price_col]) if avg_price_col and pd.notna(row[avg_price_col]) else 0.0
                    current_price = float(row[current_price_col]) if current_price_col and pd.notna(row[current_price_col]) else 0.0
                    market_value = float(row[market_value_col]) if market_value_col and pd.notna(row[market_value_col]) else (quantity * current_price)
                    
                    holding = {
                        'symbol': symbol,
                        'name': name,
                        'quantity': quantity,
                        'average_cost_usd': avg_price,
                        'current_price_usd': current_price,
                        'market_value_usd': market_value,
                        'total_invested_usd': quantity * avg_price if avg_price > 0 else market_value
                    }
                    
                    holdings.append(holding)
                    logger.info(f"Parsed INDMoney holding: {symbol} - {quantity} shares")
                    
                except Exception as e:
                    logger.error(f"Error parsing row {idx}: {str(e)}")
                    continue
            
        except Exception as e:
            logger.error(f"Error parsing INDMoney Excel: {str(e)}")
            raise
        
        return holdings, cash_balance
    
    @staticmethod
    def _find_column(df: pd.DataFrame, possible_names: List[str]) -> Optional[str]:
        """Find column by checking multiple possible names"""
        for col in df.columns:
            col_lower = col.lower().strip()
            for name in possible_names:
                if name.lower() in col_lower:
                    return col
        return None
    
    @staticmethod
    def _extract_cash_balance(df: pd.DataFrame) -> float:
        """
        Extract cash balance from the dataframe
        Looks for rows with 'Cash', 'Balance', 'Available', etc.
        """
        cash_balance = 0.0
        
        try:
            # Look for cash-related keywords in the dataframe
            for idx, row in df.iterrows():
                row_str = ' '.join([str(val).lower() for val in row.values if pd.notna(val)])
                
                if any(keyword in row_str for keyword in ['cash balance', 'available cash', 'cash:', 'balance:', 'available balance', 'wallet']):
                    # Try to extract numeric value
                    for val in row.values:
                        if pd.notna(val):
                            try:
                                # Remove currency symbols and commas
                                val_str = str(val).replace('$', '').replace('₹', '').replace(',', '').strip()
                                cash_val = float(val_str)
                                if cash_val > 0:
                                    cash_balance = cash_val
                                    logger.info(f"Found cash balance: ${cash_balance}")
                                    break
                            except (ValueError, TypeError):
                                continue
                
                if cash_balance > 0:
                    break
            
        except Exception as e:
            logger.error(f"Error extracting cash balance: {str(e)}")
        
        return cash_balance


# Made with Bob