"""
Parag Parikh Mutual Fund Factsheet Parser
Extracts equity holdings from PPFAS factsheet PDFs
"""
import re
from typing import List, Dict, Optional
import PyPDF2


class PPFASFactsheetParser:
    """Parser for Parag Parikh Flexi Cap Fund factsheets"""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.holdings: List[Dict] = []
        
    def parse(self) -> List[Dict]:
        """
        Parse the factsheet and extract equity holdings
        
        Returns:
            List of dicts with keys: name, industry, percentage
        """
        try:
            with open(self.pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # PPFAS factsheets typically have portfolio on pages 8-12
                for page_num in range(min(len(pdf_reader.pages), 15)):
                    page = pdf_reader.pages[page_num]
                    text = page.extract_text()
                    
                    # Extract holdings from this page
                    self._extract_holdings_from_page(text)
                
                # Remove duplicates and sort by percentage
                seen = set()
                unique_holdings = []
                for holding in self.holdings:
                    if holding['name'] not in seen:
                        seen.add(holding['name'])
                        unique_holdings.append(holding)
                
                return sorted(unique_holdings, key=lambda x: x['percentage'], reverse=True)
                
        except Exception as e:
            raise Exception(f"Error parsing PPFAS factsheet: {str(e)}")
    
    def _extract_holdings_from_page(self, text: str):
        """Extract holdings from a page of text"""
        lines = text.split('\n')
        
        for line in lines:
            # Pattern 1: Company Limited/Ltd Industry X.XX%
            # This is the most reliable pattern for equity holdings
            match = re.match(
                r'^([A-Z][A-Za-z\s&\'\-\.]+(?:Limited|Ltd|Inc|Corp))\s+([A-Za-z\s&\-]+?)\s+(\d+\.\d+)%',
                line
            )
            
            if match:
                company_name = match.group(1).strip()
                industry = match.group(2).strip()
                percentage = float(match.group(3))
                
                # Skip if it looks like a debt instrument
                if self._is_debt_instrument(line):
                    continue
                
                # Skip if percentage is unreasonably high (likely a subtotal)
                if percentage > 15.0:
                    continue
                
                holding = {
                    'name': self._clean_company_name(company_name),
                    'industry': industry,
                    'percentage': percentage
                }
                
                self.holdings.append(holding)
                continue
            
            # Pattern 2: Company Name (without Limited/Ltd) Industry X.XX%
            # For companies that don't end with Limited/Ltd
            match2 = re.match(
                r'^([A-Z][A-Za-z\s&\'\-\.]+?)\s+((?:IT - Software|Banks|Finance|Automobiles|Telecom - Services|Pharmaceuticals & Biotechnology|Capital Markets|Auto Components|Food Products|Healthcare Services|Transport Services|Commercial Services & Supplies))\s+(\d+\.\d+)%',
                line
            )
            
            if match2:
                company_name = match2.group(1).strip()
                industry = match2.group(2).strip()
                percentage = float(match2.group(3))
                
                # Skip if it looks like a debt instrument
                if self._is_debt_instrument(line):
                    continue
                
                # Skip if percentage is unreasonably high
                if percentage > 15.0:
                    continue
                
                # Skip common false positives
                if any(word in company_name.lower() for word in ['expense', 'ratio', 'plan', 'fact sheet', 'risk']):
                    continue
                
                holding = {
                    'name': self._clean_company_name(company_name),
                    'industry': industry,
                    'percentage': percentage
                }
                
                self.holdings.append(holding)
    
    def _is_debt_instrument(self, line: str) -> bool:
        """Check if line represents a debt instrument"""
        debt_keywords = [
            'NCD', 'SDL', 'Tbill', 'T-Bill', 'CRISIL', 'ICRA', 'CARE',
            'IND A1', 'AAA', 'Sovereign', 'Bond', 'Debenture',
            'Certificate of Deposit', 'Commercial Paper', 'Treasury',
            'Government', 'REIT', 'InvIT', '(MD ', 'Liquid Fund'
        ]
        
        return any(keyword in line for keyword in debt_keywords)
    
    def _clean_company_name(self, name: str) -> str:
        """Clean up company name"""
        # Remove common suffixes for cleaner display
        name = re.sub(r'\s+(Limited|Ltd|Ltd\.|Corporation|Corp|Inc|Pvt)$', '', name, flags=re.IGNORECASE)
        
        # Remove extra whitespace
        name = ' '.join(name.split())
        
        return name.strip()


def parse_ppfas_factsheet(pdf_path: str) -> List[Dict]:
    """
    Convenience function to parse PPFAS factsheet
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        List of holdings with name, industry, and percentage
    """
    parser = PPFASFactsheetParser(pdf_path)
    return parser.parse()


# Test function
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        pdf_path = "../statements/mfs/ppfas-mf-factsheet-for-January-2026.pdf"
    
    print(f"Parsing: {pdf_path}\n")
    
    try:
        holdings = parse_ppfas_factsheet(pdf_path)
        
        print(f"Found {len(holdings)} equity holdings:\n")
        print(f"{'Company Name':<50} {'Industry':<35} {'%':<10}")
        print("=" * 95)
        
        total_percentage = 0
        for holding in holdings:
            print(f"{holding['name']:<50} {holding['industry']:<35} {holding['percentage']:>6.2f}%")
            total_percentage += holding['percentage']
        
        print("=" * 95)
        print(f"{'Total Equity Allocation':<85} {total_percentage:>6.2f}%")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

# Made with Bob
