"""
National Pension System (NPS) Statement Parser
Supports PDF statements from CRA (Central Recordkeeping Agency)
"""
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import PyPDF2
from io import BytesIO


class NPSStatementParser:
    """Parser for NPS account statements"""
    
    def __init__(self, file_content: bytes, password: Optional[str] = None):
        self.file_content = file_content
        self.password = password
        self.account_data = {}
        self.transactions = []
    
    def parse(self) -> Tuple[Dict, List[Dict]]:
        """
        Parse NPS statement and extract account details and transactions
        Returns: (account_data, transactions)
        """
        try:
            # Extract text from PDF
            text = self._extract_text_from_pdf()
            
            # Parse account details
            self.account_data = self._parse_account_details(text)
            
            # Parse transactions
            self.transactions = self._parse_transactions(text)
            
            return self.account_data, self.transactions
            
        except Exception as e:
            raise ValueError(f"Failed to parse NPS statement: {str(e)}")
    
    def _extract_text_from_pdf(self) -> str:
        """Extract text content from PDF"""
        try:
            pdf_file = BytesIO(self.file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            # Unlock if password protected
            if pdf_reader.is_encrypted:
                if self.password:
                    pdf_reader.decrypt(self.password)
                else:
                    raise ValueError("PDF is password protected. Please provide password.")
            
            # Extract text from all pages
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return text
            
        except Exception as e:
            raise ValueError(f"Failed to extract text from PDF: {str(e)}")
    
    def _parse_account_details(self, text: str) -> Dict:
        """Extract account details from statement text"""
        account_data = {}
        
        # Extract PRAN (Permanent Retirement Account Number) - 12 digits
        pran_match = re.search(r'PRAN[:\s]*(\d{12})', text, re.IGNORECASE)
        if pran_match:
            account_data['pran_number'] = pran_match.group(1)
        
        # Extract account holder name
        name_patterns = [
            r'(?:Subscriber|Account\s*Holder|Name)[:\s]*([A-Z\s\.]+?)(?:\n|PRAN|Date)',
            r'Name\s*of\s*Subscriber[:\s]*([A-Z\s\.]+?)(?:\n|PRAN)',
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                account_data['account_holder_name'] = match.group(1).strip()
                break
        
        # Extract date of birth
        dob_patterns = [
            r'(?:Date\s*of\s*Birth|DOB)[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        ]
        for pattern in dob_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                dob_str = match.group(1)
                account_data['date_of_birth'] = self._parse_date(dob_str)
                break
        
        # Extract sector type
        if re.search(r'Government\s*Sector', text, re.IGNORECASE):
            account_data['sector_type'] = 'government'
        elif re.search(r'Corporate\s*Sector', text, re.IGNORECASE):
            account_data['sector_type'] = 'corporate'
        else:
            account_data['sector_type'] = 'all_citizen'
        
        # Extract tier type
        if re.search(r'Tier\s*[:-]?\s*II', text, re.IGNORECASE):
            account_data['tier_type'] = 'tier_2'
        else:
            account_data['tier_type'] = 'tier_1'  # Default to Tier 1
        
        # Extract opening date
        opening_patterns = [
            r'(?:Account\s*Opening|Registration)\s*Date[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'Date\s*of\s*Joining[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        ]
        for pattern in opening_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                opening_str = match.group(1)
                account_data['opening_date'] = self._parse_date(opening_str)
                break
        
        # Extract retirement age
        retirement_match = re.search(r'Retirement\s*Age[:\s]*(\d{2})', text, re.IGNORECASE)
        if retirement_match:
            account_data['retirement_age'] = int(retirement_match.group(1))
        else:
            account_data['retirement_age'] = 60  # Default
        
        # Extract current balance/corpus
        balance_patterns = [
            r'(?:Total\s*Corpus|Current\s*Balance|Account\s*Balance)[:\s]*(?:Rs\.?|INR)?\s*([\d,]+\.?\d*)',
            r'Balance\s*as\s*on[:\s]*\d{1,2}[-/]\d{1,2}[-/]\d{2,4}[:\s]*(?:Rs\.?|INR)?\s*([\d,]+\.?\d*)',
        ]
        for pattern in balance_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                balance_str = match.group(1).replace(',', '')
                account_data['current_balance'] = float(balance_str)
                break
        
        # Extract total contributions
        contrib_patterns = [
            r'(?:Total\s*Contribution|Your\s*Contribution)[:\s]*(?:Rs\.?|INR)?\s*([\d,]+\.?\d*)',
            r'Employee\s*Contribution[:\s]*(?:Rs\.?|INR)?\s*([\d,]+\.?\d*)',
        ]
        for pattern in contrib_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                contrib_str = match.group(1).replace(',', '')
                account_data['total_contributions'] = float(contrib_str)
                break
        
        # Extract employer contributions
        employer_match = re.search(r'Employer\s*Contribution[:\s]*(?:Rs\.?|INR)?\s*([\d,]+\.?\d*)', text, re.IGNORECASE)
        if employer_match:
            employer_str = employer_match.group(1).replace(',', '')
            account_data['employer_contributions'] = float(employer_str)
        
        # Extract total returns
        returns_patterns = [
            r'(?:Total\s*Returns?|Investment\s*Returns?|Gains?)[:\s]*(?:Rs\.?|INR)?\s*([\d,]+\.?\d*)',
        ]
        for pattern in returns_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                returns_str = match.group(1).replace(',', '')
                account_data['total_returns'] = float(returns_str)
                break
        
        # Extract scheme preference
        if re.search(r'Active\s*Choice', text, re.IGNORECASE):
            account_data['scheme_preference'] = 'Active'
        elif re.search(r'Auto\s*Choice', text, re.IGNORECASE):
            account_data['scheme_preference'] = 'Auto'
        elif re.search(r'Conservative', text, re.IGNORECASE):
            account_data['scheme_preference'] = 'Conservative'
        
        # Extract fund manager
        fm_patterns = [
            r'(?:Pension\s*Fund|Fund\s*Manager)[:\s]*([A-Z\s&]+?)(?:\n|Scheme)',
        ]
        for pattern in fm_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                account_data['fund_manager'] = match.group(1).strip()
                break
        
        return account_data
    
    def _parse_transactions(self, text: str) -> List[Dict]:
        """Extract transactions from statement text"""
        transactions = []
        
        # Look for transaction table
        lines = text.split('\n')
        
        in_transaction_section = False
        for i, line in enumerate(lines):
            # Detect transaction section start
            if re.search(r'(?:Date|Transaction|Particulars).*(?:Amount|Contribution|NAV|Units)', line, re.IGNORECASE):
                in_transaction_section = True
                continue
            
            if not in_transaction_section:
                continue
            
            # Stop at summary or footer
            if re.search(r'(?:Total|Summary|Closing|Page\s*\d+|Disclaimer)', line, re.IGNORECASE):
                in_transaction_section = False
                continue
            
            # Parse transaction line
            transaction = self._parse_transaction_line(line)
            if transaction:
                transactions.append(transaction)
        
        return transactions
    
    def _parse_transaction_line(self, line: str) -> Optional[Dict]:
        """Parse a single transaction line"""
        # Pattern: Date Type Amount NAV Units Scheme
        # Example: 01/04/2024  Contribution  5000.00  52.45  95.33  E
        
        # Try to extract date
        date_match = re.search(r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', line)
        if not date_match:
            return None
        
        transaction_date = self._parse_date(date_match.group(1))
        
        # Extract amounts and NAV
        amounts = re.findall(r'([\d,]+\.?\d*)', line)
        if len(amounts) < 1:
            return None
        
        # Clean amounts
        amounts = [float(amt.replace(',', '')) for amt in amounts]
        
        # Determine transaction type from description
        line_lower = line.lower()
        if 'contribution' in line_lower or 'deposit' in line_lower:
            if 'employer' in line_lower:
                trans_type = 'employer_contribution'
            else:
                trans_type = 'contribution'
        elif 'return' in line_lower or 'gain' in line_lower or 'profit' in line_lower:
            trans_type = 'returns'
        elif 'withdrawal' in line_lower or 'redemption' in line_lower:
            trans_type = 'withdrawal'
        elif 'switch' in line_lower or 'transfer' in line_lower:
            trans_type = 'switch'
        else:
            trans_type = 'contribution'  # Default
        
        amount = amounts[0]
        nav = amounts[1] if len(amounts) > 1 else None
        units = amounts[2] if len(amounts) > 2 else None
        
        # Extract scheme (E/C/G/A)
        scheme_match = re.search(r'\b([ECGA])\b', line)
        scheme = scheme_match.group(1) if scheme_match else None
        
        # Extract description
        desc_match = re.search(r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\s+(.+?)\s+[\d,]+', line)
        description = desc_match.group(1).strip() if desc_match else ''
        
        # Extract financial year if present
        fy_match = re.search(r'FY\s*(\d{4}[-/]\d{2,4})', line, re.IGNORECASE)
        financial_year = fy_match.group(1) if fy_match else None
        
        return {
            'transaction_date': transaction_date,
            'transaction_type': trans_type,
            'amount': amount,
            'nav': nav,
            'units': units,
            'scheme': scheme,
            'description': description,
            'financial_year': financial_year
        }
    
    def _parse_date(self, date_str: str) -> str:
        """Parse date string to ISO format (YYYY-MM-DD)"""
        formats = [
            '%d/%m/%Y', '%d-%m-%Y',
            '%d/%m/%y', '%d-%m-%y',
            '%Y-%m-%d', '%Y/%m/%d',
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        return date_str

# Made with Bob
