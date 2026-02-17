"""
Portfolio Downloader Service
Downloads mutual fund portfolio Excel files from AMC websites
"""
import requests
import tempfile
import os
from typing import Optional, Dict
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class PortfolioDownloader:
    """Download portfolio Excel files from mutual fund websites"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def download_from_url(self, url: str, save_path: Optional[str] = None) -> str:
        """
        Download Excel file from URL
        
        Args:
            url: Direct URL to the Excel file
            save_path: Optional path to save the file. If None, saves to temp directory
            
        Returns:
            Path to the downloaded file
        """
        try:
            logger.info(f"Downloading portfolio from: {url}")
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # Determine save path
            if save_path is None:
                # Create temp file
                suffix = '.xls' if '.xls' in url.lower() else '.xlsx'
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                save_path = temp_file.name
                temp_file.close()
            
            # Save the file
            with open(save_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Downloaded portfolio to: {save_path}")
            return save_path
            
        except requests.RequestException as e:
            logger.error(f"Error downloading portfolio: {e}")
            raise Exception(f"Failed to download portfolio: {str(e)}")
    
    def download_ppfas_portfolio(
        self, 
        fund_code: str = 'PPFCF',
        month: Optional[str] = None,
        year: Optional[int] = None,
        save_path: Optional[str] = None
    ) -> str:
        """
        Download PPFAS portfolio for a specific fund
        
        Args:
            fund_code: Fund code (PPFCF, PPTSF, PPCHF, PPAF, PPDAAF, PPLF)
            month: Month name (e.g., 'January'). If None, uses latest
            year: Year (e.g., 2026). If None, uses current year
            save_path: Optional path to save the file
            
        Returns:
            Path to the downloaded file
        """
        from datetime import datetime
        
        if year is None:
            year = datetime.now().year
        
        if month is None:
            # Use current or previous month
            current_month = datetime.now().strftime('%B')
            month = current_month
        
        # Construct URL
        # Format: https://amc.ppfas.com/downloads/portfolio-disclosure/YEAR/FUNDCODE_PPFAS_Monthly_Portfolio_Report_MONTH_DAY_YEAR.xls
        
        # Get last day of month (approximate)
        month_days = {
            'January': 31, 'February': 28, 'March': 31, 'April': 30,
            'May': 31, 'June': 30, 'July': 31, 'August': 31,
            'September': 30, 'October': 31, 'November': 30, 'December': 31
        }
        
        day = month_days.get(month, 31)
        
        # Try different URL patterns
        url_patterns = [
            f"https://amc.ppfas.com/downloads/portfolio-disclosure/{year}/{fund_code}_PPFAS_Monthly_Portfolio_Report_{month}_{day}_{year}.xls",
            f"https://amc.ppfas.com/downloads/portfolio-disclosure/{year}/{fund_code}_PPFAS_Monthly_Portfolio_Report_{month}_{day}_{year}.xls?{day:02d}{datetime.now().strftime('%m%Y')}_1",
        ]
        
        last_error = None
        for url in url_patterns:
            try:
                return self.download_from_url(url, save_path)
            except Exception as e:
                last_error = e
                continue
        
        raise Exception(f"Failed to download PPFAS portfolio: {last_error}")
    
    def get_ppfas_latest_url(self, fund_code: str = 'PPFCF') -> Optional[str]:
        """
        Scrape PPFAS website to get the latest portfolio URL
        
        Args:
            fund_code: Fund code (PPFCF, PPTSF, etc.)
            
        Returns:
            URL of the latest portfolio file, or None if not found
        """
        try:
            from bs4 import BeautifulSoup
            
            url = 'https://amc.ppfas.com/downloads/portfolio-disclosure/'
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all Excel links
            links = soup.find_all('a', href=True)
            
            # Look for the fund code in the link
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                if fund_code in href and '.xls' in href.lower():
                    # Found a match
                    if href.startswith('http'):
                        return href
                    else:
                        return f"https://amc.ppfas.com{href}"
            
            return None
            
        except Exception as e:
            logger.error(f"Error scraping PPFAS website: {e}")
            return None


def download_portfolio(url: str, save_path: Optional[str] = None) -> str:
    """
    Convenience function to download portfolio from URL
    
    Args:
        url: Direct URL to the Excel file
        save_path: Optional path to save the file
        
    Returns:
        Path to the downloaded file
    """
    downloader = PortfolioDownloader()
    return downloader.download_from_url(url, save_path)


# Test function
if __name__ == "__main__":
    import sys
    
    downloader = PortfolioDownloader()
    
    if len(sys.argv) > 1:
        # Download from provided URL
        url = sys.argv[1]
        print(f"Downloading from URL: {url}")
        file_path = downloader.download_from_url(url)
        print(f"Downloaded to: {file_path}")
    else:
        # Try to get latest PPFCF portfolio
        print("Getting latest PPFCF portfolio URL...")
        url = downloader.get_ppfas_latest_url('PPFCF')
        
        if url:
            print(f"Found URL: {url}")
            print("Downloading...")
            file_path = downloader.download_from_url(url)
            print(f"Downloaded to: {file_path}")
            
            # Test parsing
            print("\nTesting parser...")
            from ppfas_excel_parser import parse_ppfas_excel
            holdings = parse_ppfas_excel(file_path)
            print(f"Successfully parsed {len(holdings)} holdings")
            
            # Cleanup
            os.unlink(file_path)
            print("Cleaned up temp file")
        else:
            print("Could not find latest portfolio URL")

# Made with Bob
