"""
Sukanya Samriddhi Yojana (SSY) Statement Parser
Supports PDF statements from Post Offices and Banks
"""
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import PyPDF2
from io import BytesIO


class SSYStatementParser:
    """Parser for SSY account statements"""
    
    def __init__(self, file_content: bytes, password: Optional[str] = None):
        self.file_content = file_content
        self.password = password
        self.account_data = {}
        self.transactions = []
    
    def parse(self) -> Tuple[Dict, List[Dict]]:
        """
        Parse SSY statement and extract account details and transactions
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
            raise ValueError(f"Failed to parse SSY statement: {str(e)}")
    
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
        
        # Extract account number (typically 14 digits for SSY)
        account_match = re.search(r'Account\s*(?:No|Number)[:\s]*([A-Z0-9]{10,20})', text, re.IGNORECASE)
        if account_match:
            account_data['account_number'] = account_match.group(1).strip()
        
        # Extract girl's name
        girl_name_patterns = [
            r'(?:Girl\'?s?\s*Name|Account\s*Holder|Beneficiary)[:\s]*([A-Z\s\.]+?)(?:\n|Date|DOB)',
            r'Name\s*of\s*Girl\s*Child[:\s]*([A-Z\s\.]+?)(?:\n|Date)',
        ]
        for pattern in girl_name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                account_data['girl_name'] = match.group(1).strip()
                break
        
        # Extract girl's date of birth
        dob_patterns = [
            r'(?:Date\s*of\s*Birth|DOB|Birth\s*Date)[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'Girl\'?s?\s*DOB[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        ]
        for pattern in dob_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                dob_str = match.group(1)
                account_data['girl_dob'] = self._parse_date(dob_str)
                break
        
        # Extract guardian name
        guardian_patterns = [
            r'(?:Guardian|Parent|Father|Mother)\'?s?\s*Name[:\s]*([A-Z\s\.]+?)(?:\n|Date|Address)',
            r'Depositor\'?s?\s*Name[:\s]*([A-Z\s\.]+?)(?:\n|Date)',
        ]
        for pattern in guardian_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                account_data['guardian_name'] = match.group(1).strip()
                break
        
        # Extract bank/post office name
        bank_patterns = [
            r'(?:Bank|Post\s*Office)[:\s]*([A-Z\s&]+?)(?:\n|Branch)',
            r'Branch[:\s]*([A-Z\s&]+?)(?:\n|Address)',
        ]
        for pattern in bank_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                account_data['bank_name'] = match.group(1).strip()
                break
        
        # Extract post office name if different from bank
        po_match = re.search(r'Post\s*Office[:\s]*([A-Z\s]+?)(?:\n|,)', text, re.IGNORECASE)
        if po_match:
            account_data['post_office_name'] = po_match.group(1).strip()
        
        # Extract opening date
        opening_patterns = [
            r'(?:Opening|Account\s*Opening)\s*Date[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'Date\s*of\s*Opening[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        ]
        for pattern in opening_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                opening_str = match.group(1)
                account_data['opening_date'] = self._parse_date(opening_str)
                break
        
        # Extract maturity date
        maturity_match = re.search(r'Maturity\s*Date[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', text, re.IGNORECASE)
        if maturity_match:
            maturity_str = maturity_match.group(1)
            account_data['maturity_date'] = self._parse_date(maturity_str)
        
        # Extract interest rate
        interest_match = re.search(r'Interest\s*Rate[:\s]*([\d.]+)\s*%', text, re.IGNORECASE)
        if interest_match:
            account_data['interest_rate'] = float(interest_match.group(1))
        else:
            account_data['interest_rate'] = 8.2  # Default SSY rate
        
        # Extract current balance
        balance_patterns = [
            r'(?:Current|Closing|Total)\s*Balance[:\s]*(?:Rs\.?|INR)?\s*([\d,]+\.?\d*)',
            r'Balance\s*as\s*on[:\s]*\d{1,2}[-/]\d{1,2}[-/]\d{2,4}[:\s]*(?:Rs\.?|INR)?\s*([\d,]+\.?\d*)',
        ]
        for pattern in balance_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                balance_str = match.group(1).replace(',', '')
                account_data['current_balance'] = float(balance_str)
                break
        
        # Extract total deposits
        deposits_match = re.search(r'Total\s*Deposits?[:\s]*(?:Rs\.?|INR)?\s*([\d,]+\.?\d*)', text, re.IGNORECASE)
        if deposits_match:
            deposits_str = deposits_match.group(1).replace(',', '')
            account_data['total_deposits'] = float(deposits_str)
        
        # Extract total interest
        interest_earned_match = re.search(r'(?:Total\s*Interest|Interest\s*Earned)[:\s]*(?:Rs\.?|INR)?\s*([\d,]+\.?\d*)', text, re.IGNORECASE)
        if interest_earned_match:
            interest_str = interest_earned_match.group(1).replace(',', '')
            account_data['total_interest_earned'] = float(interest_str)
        
        # Extract financial year
        fy_match = re.search(r'(?:Financial\s*Year|FY)[:\s]*(\d{4}[-/]\d{2,4})', text, re.IGNORECASE)
        if fy_match:
            account_data['financial_year'] = fy_match.group(1)
        
        return account_data
    
    def _parse_transactions(self, text: str) -> List[Dict]:
        """Extract transactions from statement text"""
        transactions = []
        
        # Look for transaction table
        # Common patterns: Date | Description | Deposit | Withdrawal | Interest | Balance
        lines = text.split('\n')
        
        in_transaction_section = False
        for i, line in enumerate(lines):
            # Detect transaction section start
            if re.search(r'(?:Date|Transaction|Particulars).*(?:Deposit|Credit|Debit|Balance)', line, re.IGNORECASE):
                in_transaction_section = True
                continue
            
            if not in_transaction_section:
                continue
            
            # Stop at summary or footer
            if re.search(r'(?:Total|Summary|Closing|Page\s*\d+)', line, re.IGNORECASE):
                in_transaction_section = False
                continue
            
            # Parse transaction line
            transaction = self._parse_transaction_line(line)
            if transaction:
                transactions.append(transaction)
        
        return transactions
    
    def _parse_transaction_line(self, line: str) -> Optional[Dict]:
        """Parse a single transaction line"""
        # Pattern: Date Amount Description Balance
        # Example: 01/04/2024  5000.00  Deposit  5000.00
        # Example: 31/03/2024  410.00  Interest Credited  5410.00
        
        # Try to extract date
        date_match = re.search(r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', line)
        if not date_match:
            return None
        
        transaction_date = self._parse_date(date_match.group(1))
        
        # Extract amounts (look for numbers with optional decimals)
        amounts = re.findall(r'([\d,]+\.?\d*)', line)
        if len(amounts) < 2:
            return None
        
        # Clean amounts
        amounts = [float(amt.replace(',', '')) for amt in amounts]
        
        # Determine transaction type from description
        line_lower = line.lower()
        if 'deposit' in line_lower or 'credit' in line_lower:
            trans_type = 'deposit'
            amount = amounts[0] if len(amounts) >= 2 else amounts[0]
            balance = amounts[-1]
        elif 'interest' in line_lower:
            trans_type = 'interest'
            amount = amounts[0] if len(amounts) >= 2 else amounts[0]
            balance = amounts[-1]
        elif 'withdrawal' in line_lower or 'debit' in line_lower:
            trans_type = 'withdrawal'
            amount = amounts[0] if len(amounts) >= 2 else amounts[0]
            balance = amounts[-1]
        elif 'maturity' in line_lower:
            trans_type = 'maturity'
            amount = amounts[0] if len(amounts) >= 2 else amounts[0]
            balance = amounts[-1]
        else:
            # Default to deposit
            trans_type = 'deposit'
            amount = amounts[0] if len(amounts) >= 2 else amounts[0]
            balance = amounts[-1]
        
        # Extract description (text between date and first amount)
        desc_match = re.search(r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\s+(.+?)\s+[\d,]+', line)
        description = desc_match.group(1).strip() if desc_match else ''
        
        # Extract financial year if present
        fy_match = re.search(r'FY\s*(\d{4}[-/]\d{2,4})', line, re.IGNORECASE)
        financial_year = fy_match.group(1) if fy_match else None
        
        return {
            'transaction_date': transaction_date,
            'transaction_type': trans_type,
            'amount': amount,
            'balance_after_transaction': balance,
            'description': description,
            'financial_year': financial_year
        }
    
    def _parse_date(self, date_str: str) -> str:
        """Parse date string to ISO format (YYYY-MM-DD)"""
        # Try different date formats
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
        
        # If all formats fail, return as-is
        return date_str

# Made with Bob
