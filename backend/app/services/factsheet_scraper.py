"""
Service to automatically download and parse mutual fund factsheets
"""
import requests
import re
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import PyPDF2
import io

logger = logging.getLogger(__name__)


class FactsheetScraper:
    """Scraper for mutual fund factsheets from various AMC websites"""
    
    # AMC website patterns and factsheet URL templates
    AMC_PATTERNS = {
        'HDFC': {
            'keywords': ['hdfc', 'housing development finance'],
            'base_url': 'https://www.hdfcfund.com',
            'factsheet_pattern': '/sites/default/files/factsheets/{scheme_code}_Factsheet.pdf'
        },
        'ICICI Prudential': {
            'keywords': ['icici', 'prudential'],
            'base_url': 'https://www.icicipruamc.com',
            'factsheet_pattern': '/downloads/factsheet/{scheme_name}.pdf'
        },
        'SBI': {
            'keywords': ['sbi', 'state bank'],
            'base_url': 'https://www.sbimf.com',
            'factsheet_pattern': '/docs/factsheets/{scheme_code}.pdf'
        },
        'Axis': {
            'keywords': ['axis'],
            'base_url': 'https://www.axismf.com',
            'factsheet_pattern': '/factsheet/{scheme_code}.pdf'
        },
        'Kotak': {
            'keywords': ['kotak', 'kotak mahindra'],
            'base_url': 'https://www.kotakmf.com',
            'factsheet_pattern': '/downloads/factsheet/{scheme_name}.pdf'
        },
        'Aditya Birla': {
            'keywords': ['aditya birla', 'birla sun life', 'absl'],
            'base_url': 'https://mutualfund.adityabirlacapital.com',
            'factsheet_pattern': '/Documents/Factsheet/{scheme_code}.pdf'
        },
        'Nippon India': {
            'keywords': ['nippon', 'reliance nippon'],
            'base_url': 'https://mf.nipponindiaim.com',
            'factsheet_pattern': '/InvestorServices/FactSheet/{scheme_code}.pdf'
        },
        'UTI': {
            'keywords': ['uti', 'unit trust'],
            'base_url': 'https://www.utimf.com',
            'factsheet_pattern': '/factsheet/{scheme_code}.pdf'
        },
        'Parag Parikh': {
            'keywords': ['parag parikh', 'ppfas'],
            'base_url': 'https://www.ppfas.com',
            'factsheet_pattern': '/downloads/factsheet/{scheme_name}.pdf'
        },
        'Mirae Asset': {
            'keywords': ['mirae', 'mirae asset'],
            'base_url': 'https://www.miraeassetmf.co.in',
            'factsheet_pattern': '/downloads/factsheet/{scheme_code}.pdf'
        },
        'DSP': {
            'keywords': ['dsp', 'dsp blackrock'],
            'base_url': 'https://www.dspim.com',
            'factsheet_pattern': '/factsheet/{scheme_code}.pdf'
        },
        'Franklin Templeton': {
            'keywords': ['franklin', 'templeton'],
            'base_url': 'https://www.franklintempletonindia.com',
            'factsheet_pattern': '/downloadsServlet/pdf/factsheet-{scheme_code}.pdf'
        },
        'Tata': {
            'keywords': ['tata'],
            'base_url': 'https://www.tatamutualfund.com',
            'factsheet_pattern': '/factsheet/{scheme_code}.pdf'
        },
        'Motilal Oswal': {
            'keywords': ['motilal', 'oswal'],
            'base_url': 'https://www.motilaloswalmf.com',
            'factsheet_pattern': '/mf/factsheet/{scheme_code}.pdf'
        },
        'Canara Robeco': {
            'keywords': ['canara', 'robeco'],
            'base_url': 'https://www.canararobeco.com',
            'factsheet_pattern': '/factsheet/{scheme_code}.pdf'
        },
        'IDFC': {
            'keywords': ['idfc'],
            'base_url': 'https://www.idfcmf.com',
            'factsheet_pattern': '/factsheet/{scheme_code}.pdf'
        },
        'L&T': {
            'keywords': ['l&t', 'larsen', 'toubro'],
            'base_url': 'https://www.ltfs.com',
            'factsheet_pattern': '/mutual-fund/factsheet/{scheme_code}.pdf'
        },
        'Sundaram': {
            'keywords': ['sundaram'],
            'base_url': 'https://www.sundarammutual.com',
            'factsheet_pattern': '/factsheet/{scheme_code}.pdf'
        },
        'Edelweiss': {
            'keywords': ['edelweiss'],
            'base_url': 'https://www.edelweissmf.com',
            'factsheet_pattern': '/factsheet/{scheme_code}.pdf'
        },
        'PGIM India': {
            'keywords': ['pgim', 'dhfl pramerica'],
            'base_url': 'https://www.pgimindiamf.com',
            'factsheet_pattern': '/factsheet/{scheme_code}.pdf'
        }
    }
    
    @staticmethod
    def identify_amc(fund_name: str) -> Optional[str]:
        """
        Identify the AMC from fund name
        
        Args:
            fund_name: Name of the mutual fund
            
        Returns:
            AMC name or None if not found
        """
        fund_name_lower = fund_name.lower()
        
        for amc_name, amc_info in FactsheetScraper.AMC_PATTERNS.items():
            for keyword in amc_info['keywords']:
                if keyword in fund_name_lower:
                    return amc_name
        
        return None
    
    @staticmethod
    def download_factsheet(fund_name: str, scheme_code: Optional[str] = None) -> Optional[bytes]:
        """
        Download factsheet PDF for a mutual fund
        
        Args:
            fund_name: Name of the mutual fund
            scheme_code: Optional scheme code
            
        Returns:
            PDF content as bytes or None if failed
        """
        amc = FactsheetScraper.identify_amc(fund_name)
        if not amc:
            logger.warning(f"Could not identify AMC for fund: {fund_name}")
            return None
        
        amc_info = FactsheetScraper.AMC_PATTERNS[amc]
        
        # Try different URL patterns
        urls_to_try = []
        
        if scheme_code:
            # Try with scheme code
            url = amc_info['base_url'] + amc_info['factsheet_pattern'].format(
                scheme_code=scheme_code,
                scheme_name=fund_name.replace(' ', '-').lower()
            )
            urls_to_try.append(url)
        
        # Try with fund name
        clean_name = re.sub(r'[^\w\s-]', '', fund_name).replace(' ', '-').lower()
        url = amc_info['base_url'] + amc_info['factsheet_pattern'].format(
            scheme_code=scheme_code or 'unknown',
            scheme_name=clean_name
        )
        urls_to_try.append(url)
        
        # Try downloading from each URL
        for url in urls_to_try:
            try:
                logger.info(f"Attempting to download factsheet from: {url}")
                response = requests.get(url, timeout=30, allow_redirects=True)
                
                if response.status_code == 200 and response.content:
                    # Verify it's a PDF
                    if response.content[:4] == b'%PDF':
                        logger.info(f"Successfully downloaded factsheet from {url}")
                        return response.content
                    
            except Exception as e:
                logger.debug(f"Failed to download from {url}: {str(e)}")
                continue
        
        logger.warning(f"Could not download factsheet for {fund_name}")
        return None
    
    @staticmethod
    def extract_holdings_from_pdf(pdf_content: bytes) -> List[Dict[str, Any]]:
        """
        Extract portfolio holdings from factsheet PDF
        
        Args:
            pdf_content: PDF file content as bytes
            
        Returns:
            List of holdings dictionaries
        """
        holdings = []
        
        try:
            # Read PDF
            pdf_file = io.BytesIO(pdf_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            # Extract text from all pages
            full_text = ""
            for page in pdf_reader.pages:
                full_text += page.extract_text() + "\n"
            
            # Look for portfolio/holdings section
            holdings_section = FactsheetScraper._find_holdings_section(full_text)
            
            if holdings_section:
                holdings = FactsheetScraper._parse_holdings_text(holdings_section)
            
            logger.info(f"Extracted {len(holdings)} holdings from PDF")
            return holdings
            
        except Exception as e:
            logger.error(f"Error extracting holdings from PDF: {str(e)}")
            return []
    
    @staticmethod
    def _find_holdings_section(text: str) -> Optional[str]:
        """Find the portfolio holdings section in factsheet text"""
        
        # Common section headers
        section_patterns = [
            r'(?i)portfolio\s+holdings?',
            r'(?i)top\s+\d+\s+holdings?',
            r'(?i)equity\s+holdings?',
            r'(?i)stock\s+holdings?',
            r'(?i)sectoral\s+allocation',
        ]
        
        for pattern in section_patterns:
            match = re.search(pattern, text)
            if match:
                # Extract text after the header (next 2000 characters)
                start_pos = match.end()
                section_text = text[start_pos:start_pos + 2000]
                return section_text
        
        return None
    
    @staticmethod
    def _parse_holdings_text(text: str) -> List[Dict[str, Any]]:
        """Parse holdings from extracted text"""
        holdings = []
        
        # Pattern to match: Stock Name followed by percentage
        # Examples:
        # "Reliance Industries Ltd 8.5%"
        # "HDFC Bank Ltd. 7.2"
        # "Infosys Limited 6.8 %"
        
        patterns = [
            # Pattern 1: Name followed by percentage with %
            r'([A-Z][A-Za-z\s&\.\-]+?)\s+(\d+\.?\d*)\s*%',
            # Pattern 2: Name followed by percentage without %
            r'([A-Z][A-Za-z\s&\.\-]+?)\s+(\d+\.\d+)(?!\d)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                stock_name = match[0].strip()
                try:
                    percentage = float(match[1])
                    
                    # Filter out invalid entries
                    if percentage > 0 and percentage < 50 and len(stock_name) > 3:
                        # Check if not already added
                        if not any(h['stock_name'] == stock_name for h in holdings):
                            holdings.append({
                                'stock_name': stock_name,
                                'holding_percentage': percentage
                            })
                except ValueError:
                    continue
        
        # Sort by percentage descending
        holdings.sort(key=lambda x: x['holding_percentage'], reverse=True)
        
        # Take top 20 holdings
        return holdings[:20]
    
    @staticmethod
    def scrape_fund_holdings(fund_name: str, scheme_code: Optional[str] = None) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """
        Complete workflow to scrape holdings for a fund
        
        Args:
            fund_name: Name of the mutual fund
            scheme_code: Optional scheme code
            
        Returns:
            Tuple of (success, message, holdings_list)
        """
        # Step 1: Identify AMC
        amc = FactsheetScraper.identify_amc(fund_name)
        if not amc:
            return False, f"Could not identify AMC for fund: {fund_name}", []
        
        logger.info(f"Identified AMC: {amc} for fund: {fund_name}")
        
        # Step 2: Download factsheet
        pdf_content = FactsheetScraper.download_factsheet(fund_name, scheme_code)
        if not pdf_content:
            return False, f"Could not download factsheet for {fund_name}. Please upload CSV manually.", []
        
        # Step 3: Extract holdings
        holdings = FactsheetScraper.extract_holdings_from_pdf(pdf_content)
        if not holdings:
            return False, "Could not extract holdings from factsheet. Please upload CSV manually.", []
        
        return True, f"Successfully extracted {len(holdings)} holdings from factsheet", holdings


# Made with Bob