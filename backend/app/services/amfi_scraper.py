"""
AMFI Scraper Service
Scrapes AMFI website to get AMC portfolio disclosure URLs
"""
import requests
import re
from typing import Dict, Optional, List
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


class AMFIScraper:
    """Scraper for AMFI portfolio disclosure page"""
    
    AMFI_URL = "https://www.amfiindia.com/online-center/portfolio-disclosure"
    
    # AMC name mappings (fund name → AMC identifier)
    AMC_MAPPINGS = {
        # HDFC
        'hdfc': 'hdfc',
        # ICICI
        'icici': 'icici',
        'icici prudential': 'icici',
        # SBI
        'sbi': 'sbi',
        # Axis
        'axis': 'axis',
        # Kotak
        'kotak': 'kotak',
        # Aditya Birla
        'aditya birla': 'aditya',
        'birla': 'aditya',
        'aditya': 'aditya',
        'absl': 'aditya',
        # Nippon
        'nippon': 'nippon',
        'reliance': 'nippon',  # Reliance became Nippon
        # PPFAS
        'ppfas': 'ppfas',
        'parag parikh': 'ppfas',
        # DSP
        'dsp': 'dsp',
        # Franklin
        'franklin': 'franklin',
        'templeton': 'franklin',
        # Mirae
        'mirae': 'mirae',
        # Motilal
        'motilal': 'motilal',
        # UTI
        'uti': 'uti',
        # Tata
        'tata': 'tata',
        # Sundaram
        'sundaram': 'sundaram',
        # Quantum
        'quantum': 'quantum',
        # Quant
        'quant': 'quant',
        # 360 ONE / IIFL
        '360': '360',
        'iifl': '360',
        # Invesco
        'invesco': 'invesco',
        # PGIM
        'pgim': 'pgim',
        # Bandhan
        'bandhan': 'bandhan',
        # Navi
        'navi': 'navi',
        # Groww
        'groww': 'groww',
        # Union
        'union': 'union',
        # Old Bridge
        'old bridge': 'oldbridge',
        'oldbridge': 'oldbridge',
        # White Oak
        'white oak': 'whiteoakmf',
        # Taurus
        'taurus': 'taurus',
        # Capital Mind
        'capital mind': 'capitalmind',
        # Choice
        'choice': 'choice',
        # UNIFI
        'unifi': 'unifi',
        # Abakkus
        'abakkus': 'abakkus',
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self._amc_urls_cache = None
    
    def get_amc_urls(self, force_refresh: bool = False) -> Dict[str, List[str]]:
        """
        Get all AMC portfolio disclosure URLs from AMFI
        
        Args:
            force_refresh: Force refresh even if cached
            
        Returns:
            Dict mapping AMC identifier to list of portfolio URLs
        """
        if self._amc_urls_cache and not force_refresh:
            return self._amc_urls_cache
        
        try:
            logger.info(f"Fetching AMC URLs from AMFI: {self.AMFI_URL}")
            
            response = self.session.get(self.AMFI_URL, timeout=15)
            response.raise_for_status()
            
            html = response.text
            
            # Extract all portfolio/disclosure URLs
            portfolio_urls = re.findall(
                r'https?://[^\s<>"\']+(?:portfolio|disclosure|statutory)[^\s<>"\']*',
                html,
                re.IGNORECASE
            )
            
            # Clean and deduplicate
            unique_urls = set()
            for url in portfolio_urls:
                # Remove trailing backslash and fragments
                url = url.rstrip('\\').split('#')[0].split('?')[0]
                if url and len(url) > 20:
                    unique_urls.add(url)
            
            # Group by AMC
            amc_urls = {}
            
            for url in unique_urls:
                # Extract domain
                domain = url.split('//')[1].split('/')[0].lower()
                
                # Identify AMC
                amc_id = self._identify_amc(domain)
                
                if amc_id:
                    if amc_id not in amc_urls:
                        amc_urls[amc_id] = []
                    amc_urls[amc_id].append(url)
            
            self._amc_urls_cache = amc_urls
            logger.info(f"Found portfolio URLs for {len(amc_urls)} AMCs")
            
            return amc_urls
            
        except Exception as e:
            logger.error(f"Error fetching AMC URLs from AMFI: {e}")
            return {}
    
    def _identify_amc(self, domain: str) -> Optional[str]:
        """Identify AMC from domain name"""
        domain_lower = domain.lower()
        
        # Check each AMC identifier
        if 'hdfc' in domain_lower:
            return 'hdfc'
        elif 'icici' in domain_lower:
            return 'icici'
        elif 'sbi' in domain_lower:
            return 'sbi'
        elif 'axis' in domain_lower:
            return 'axis'
        elif 'kotak' in domain_lower:
            return 'kotak'
        elif 'nippon' in domain_lower:
            return 'nippon'
        elif 'aditya' in domain_lower or 'birla' in domain_lower:
            return 'aditya'
        elif 'franklin' in domain_lower:
            return 'franklin'
        elif 'dsp' in domain_lower:
            return 'dsp'
        elif 'ppfas' in domain_lower:
            return 'ppfas'
        elif 'quantum' in domain_lower:
            return 'quantum'
        elif 'mirae' in domain_lower:
            return 'mirae'
        elif 'motilal' in domain_lower:
            return 'motilal'
        elif 'uti' in domain_lower:
            return 'uti'
        elif 'tata' in domain_lower:
            return 'tata'
        elif 'sundaram' in domain_lower:
            return 'sundaram'
        elif 'invesco' in domain_lower:
            return 'invesco'
        elif 'pgim' in domain_lower:
            return 'pgim'
        elif 'quant' in domain_lower and 'quantum' not in domain_lower:
            return 'quant'
        elif '360' in domain_lower or 'iifl' in domain_lower:
            return '360'
        elif 'bandhan' in domain_lower:
            return 'bandhan'
        elif 'navi' in domain_lower:
            return 'navi'
        elif 'groww' in domain_lower:
            return 'groww'
        elif 'union' in domain_lower:
            return 'union'
        elif 'oldbridge' in domain_lower:
            return 'oldbridge'
        elif 'whiteoakmf' in domain_lower or 'whiteoakamc' in domain_lower:
            return 'whiteoakmf'
        elif 'taurus' in domain_lower:
            return 'taurus'
        elif 'capitalmind' in domain_lower:
            return 'capitalmind'
        elif 'choice' in domain_lower:
            return 'choice'
        elif 'unifi' in domain_lower:
            return 'unifi'
        elif 'abakkus' in domain_lower:
            return 'abakkus'
        
        return None
    
    def get_amc_url_for_fund(self, fund_name: str) -> Optional[str]:
        """
        Get AMC portfolio disclosure URL for a specific fund
        
        Args:
            fund_name: Name of the mutual fund
            
        Returns:
            Portfolio disclosure URL or None
        """
        # Identify AMC from fund name
        fund_lower = fund_name.lower()
        
        amc_id = None
        for keyword, amc in self.AMC_MAPPINGS.items():
            if keyword in fund_lower:
                amc_id = amc
                break
        
        if not amc_id:
            logger.warning(f"Could not identify AMC for fund: {fund_name}")
            return None
        
        # Get URLs for this AMC
        amc_urls = self.get_amc_urls()
        
        if amc_id not in amc_urls:
            logger.warning(f"No portfolio URL found for AMC: {amc_id}")
            return None
        
        # Return the first URL (usually the main portfolio page)
        urls = amc_urls[amc_id]
        
        # Prefer URLs with 'portfolio' in them
        portfolio_urls = [url for url in urls if 'portfolio' in url.lower()]
        
        if portfolio_urls:
            return portfolio_urls[0]
        
        return urls[0] if urls else None
    
    def find_latest_excel_url(self, amc_portfolio_url: str) -> Optional[str]:
        """
        Try to find the latest Excel file URL from an AMC portfolio page
        
        Args:
            amc_portfolio_url: URL of the AMC's portfolio disclosure page
            
        Returns:
            Direct Excel file URL or None
        """
        try:
            logger.info(f"Searching for Excel files at: {amc_portfolio_url}")
            
            response = self.session.get(amc_portfolio_url, timeout=15)
            response.raise_for_status()
            
            html = response.text
            
            # Look for Excel file links
            excel_pattern = r'https?://[^\s<>"\']+\.xls[x]?(?:\?[^\s<>"\']*)?'
            excel_urls = re.findall(excel_pattern, html, re.IGNORECASE)
            
            if excel_urls:
                # Clean URLs
                cleaned_urls = []
                for url in excel_urls:
                    url = url.rstrip('\\')
                    cleaned_urls.append(url)
                
                # Try to find the most recent one (look for dates in filename)
                # Prefer URLs with current year/month
                from datetime import datetime
                current_year = datetime.now().year
                current_month = datetime.now().strftime('%B')
                
                # First try: URLs with current year and month
                for url in cleaned_urls:
                    if str(current_year) in url and current_month in url:
                        logger.info(f"Found recent Excel file: {url}")
                        return url
                
                # Second try: URLs with current year
                for url in cleaned_urls:
                    if str(current_year) in url:
                        logger.info(f"Found Excel file from current year: {url}")
                        return url
                
                # Fallback: Return first Excel URL
                logger.info(f"Found Excel file: {cleaned_urls[0]}")
                return cleaned_urls[0]
            
            logger.warning(f"No Excel files found at: {amc_portfolio_url}")
            return None
            
        except Exception as e:
            logger.error(f"Error finding Excel URL: {e}")
            return None


# Singleton instance
_amfi_scraper = None

def get_amfi_scraper() -> AMFIScraper:
    """Get singleton AMFI scraper instance"""
    global _amfi_scraper
    if _amfi_scraper is None:
        _amfi_scraper = AMFIScraper()
    return _amfi_scraper


# Test function
if __name__ == "__main__":
    scraper = AMFIScraper()
    
    # Test getting all AMC URLs
    print("Fetching AMC URLs from AMFI...\n")
    amc_urls = scraper.get_amc_urls()
    
    print(f"Found {len(amc_urls)} AMCs:\n")
    for amc_id, urls in sorted(amc_urls.items()):
        print(f"{amc_id.upper()}:")
        for url in urls[:2]:  # Show first 2 URLs
            print(f"  - {url}")
        if len(urls) > 2:
            print(f"  ... and {len(urls) - 2} more")
        print()
    
    # Test finding URL for specific funds
    test_funds = [
        "Parag Parikh Flexi Cap Fund",
        "HDFC Flexi Cap Fund",
        "ICICI Prudential Bluechip Fund",
        "SBI Bluechip Fund"
    ]
    
    print("\nTesting fund URL lookup:\n")
    for fund_name in test_funds:
        url = scraper.get_amc_url_for_fund(fund_name)
        print(f"{fund_name}:")
        print(f"  URL: {url}\n")

# Made with Bob
