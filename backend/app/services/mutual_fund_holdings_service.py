"""
Service to fetch and manage mutual fund holdings data
"""
import requests
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.models.mutual_fund_holding import MutualFundHolding
from app.models.asset import Asset, AssetType
from app.services.factsheet_scraper import FactsheetScraper
import logging

logger = logging.getLogger(__name__)


class MutualFundHoldingsService:
    """Service to fetch mutual fund portfolio holdings"""
    
    # MFApi endpoint for scheme details (includes holdings)
    MFAPI_BASE_URL = "https://api.mfapi.in/mf"
    
    @staticmethod
    def get_scheme_code_from_isin(isin: str) -> Optional[str]:
        """
        Get scheme code from ISIN using AMFI data
        Note: This is a simplified version. In production, you'd want to maintain
        a mapping database or use a more robust API.
        """
        try:
            # Try to fetch from AMFI NAV file
            response = requests.get("https://www.amfiindia.com/spages/NAVAll.txt", timeout=10)
            if response.status_code == 200:
                lines = response.text.split('\n')
                for line in lines:
                    if isin in line:
                        parts = line.split(';')
                        if len(parts) > 0:
                            return parts[0].strip()
        except Exception as e:
            logger.error(f"Error fetching scheme code for ISIN {isin}: {str(e)}")
        
        return None
    
    @staticmethod
    def fetch_fund_holdings(scheme_code: str) -> Optional[Dict[str, Any]]:
        """
        Fetch mutual fund holdings from MFApi
        
        Args:
            scheme_code: The scheme code of the mutual fund
            
        Returns:
            Dictionary containing fund details and holdings, or None if failed
        """
        try:
            url = f"{MutualFundHoldingsService.MFAPI_BASE_URL}/{scheme_code}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data
            else:
                logger.error(f"Failed to fetch holdings for scheme {scheme_code}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching holdings for scheme {scheme_code}: {str(e)}")
            return None
    
    @staticmethod
    def parse_holdings_data(fund_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse holdings data from MFApi response
        
        Args:
            fund_data: Raw data from MFApi
            
        Returns:
            List of parsed holdings
        """
        holdings = []
        
        # MFApi returns data in 'data' field with portfolio holdings
        if 'data' in fund_data and isinstance(fund_data['data'], list):
            for item in fund_data['data']:
                # Look for portfolio data (usually the first item with holding details)
                if isinstance(item, dict) and 'holding' in item:
                    holding_name = item.get('holding', '')
                    nature = item.get('nature', '')
                    percentage = item.get('value', 0)
                    
                    # Try to parse percentage
                    try:
                        if isinstance(percentage, str):
                            percentage = float(percentage.replace('%', '').strip())
                        else:
                            percentage = float(percentage)
                    except (ValueError, AttributeError):
                        percentage = 0.0
                    
                    # Only include equity holdings (skip debt, cash, etc.)
                    if nature and 'equity' in nature.lower():
                        holdings.append({
                            'stock_name': holding_name,
                            'holding_percentage': percentage,
                            'nature': nature
                        })
        
        return holdings
    
    @staticmethod
    def update_fund_holdings(
        db: Session,
        asset: Asset,
        user_id: int,
        force_refresh: bool = False
    ) -> tuple[bool, str]:
        """
        Update holdings for a mutual fund asset
        
        Tries multiple methods in order:
        1. Automatic factsheet download and parsing
        2. MFApi (if available)
        3. Returns message to upload CSV manually
        
        Args:
            db: Database session
            asset: The mutual fund asset
            user_id: User ID
            force_refresh: Force refresh even if data exists
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        # Verify this is an equity mutual fund
        if asset.asset_type != AssetType.EQUITY_MUTUAL_FUND:
            return False, "Holdings tracking is only available for Equity Mutual Funds"
        
        # Check if we already have holdings and not forcing refresh
        if not force_refresh:
            existing_count = db.query(MutualFundHolding).filter(
                MutualFundHolding.asset_id == asset.id
            ).count()
            if existing_count > 0:
                return True, f"Holdings already exist ({existing_count} stocks)"
        
        # Method 1: Try automatic factsheet scraping
        logger.info(f"Attempting to scrape factsheet for {asset.name}")
        success, message, holdings_data = FactsheetScraper.scrape_fund_holdings(
            asset.name,
            scheme_code=None  # We'll extract from ISIN if needed
        )
        
        if success and holdings_data:
            logger.info(f"Successfully scraped {len(holdings_data)} holdings from factsheet")
            
            # Delete existing holdings if force refresh
            if force_refresh:
                db.query(MutualFundHolding).filter(
                    MutualFundHolding.asset_id == asset.id
                ).delete()
            
            # Create new holdings
            created_count = 0
            for holding_data in holdings_data:
                holding = MutualFundHolding(
                    asset_id=asset.id,
                    user_id=user_id,
                    stock_name=holding_data['stock_name'],
                    holding_percentage=holding_data['holding_percentage'],
                    stock_symbol=holding_data.get('stock_symbol'),
                    sector=holding_data.get('sector'),
                    data_source='factsheet_auto'
                )
                
                # Calculate holding value based on user's MF units
                if asset.quantity and asset.current_price:
                    holding.calculate_holding_value(asset.quantity, asset.current_price)
                
                db.add(holding)
                created_count += 1
            
            db.commit()
            
            return True, f"Successfully auto-fetched {created_count} holdings from factsheet"
        
        # Method 2: Try MFApi (legacy, usually doesn't have holdings)
        logger.info("Factsheet scraping failed, trying MFApi...")
        if asset.isin:
            scheme_code = MutualFundHoldingsService.get_scheme_code_from_isin(asset.isin)
            if scheme_code:
                fund_data = MutualFundHoldingsService.fetch_fund_holdings(scheme_code)
                if fund_data:
                    holdings = MutualFundHoldingsService.parse_holdings_data(fund_data)
                    if holdings:
                        # Delete existing holdings if force refresh
                        if force_refresh:
                            db.query(MutualFundHolding).filter(
                                MutualFundHolding.asset_id == asset.id
                            ).delete()
                        
                        # Create new holdings
                        created_count = 0
                        for holding_data in holdings:
                            holding = MutualFundHolding(
                                asset_id=asset.id,
                                user_id=user_id,
                                stock_name=holding_data['stock_name'],
                                holding_percentage=holding_data['holding_percentage'],
                                data_source='mfapi'
                            )
                            
                            if asset.quantity and asset.current_price:
                                holding.calculate_holding_value(asset.quantity, asset.current_price)
                            
                            db.add(holding)
                            created_count += 1
                        
                        db.commit()
                        return True, f"Successfully updated {created_count} holdings from MFApi"
        
        # Method 3: Return message to upload CSV
        return False, "Could not auto-fetch holdings. Please upload a CSV file with portfolio data from the fund's factsheet."
    
    @staticmethod
    def get_fund_holdings(
        db: Session,
        asset_id: int,
        user_id: int
    ) -> List[MutualFundHolding]:
        """
        Get all holdings for a mutual fund
        
        Args:
            db: Database session
            asset_id: Asset ID
            user_id: User ID
            
        Returns:
            List of holdings
        """
        return db.query(MutualFundHolding).filter(
            MutualFundHolding.asset_id == asset_id,
            MutualFundHolding.user_id == user_id
        ).order_by(MutualFundHolding.holding_percentage.desc()).all()
    
    @staticmethod
    def recalculate_holding_values(
        db: Session,
        asset: Asset
    ) -> int:
        """
        Recalculate holding values for a mutual fund when units or NAV changes
        
        Args:
            db: Database session
            asset: The mutual fund asset
            
        Returns:
            Number of holdings updated
        """
        holdings = db.query(MutualFundHolding).filter(
            MutualFundHolding.asset_id == asset.id
        ).all()
        
        for holding in holdings:
            holding.calculate_holding_value(asset.quantity, asset.current_price)
        
        db.commit()
        
        return len(holdings)


# Made with Bob