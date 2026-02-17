"""
PPF Statement Parser Service
Handles parsing of PPF (Public Provident Fund) statements from various banks
"""

import re
import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
import PyPDF2
import pandas as pd
from io import BytesIO

logger = logging.getLogger(__name__)


class PPFStatementParser:
    """Parser for PPF statements from various banks"""
    
    def __init__(self):
        self.supported_banks = [
            "SBI", "HDFC", "ICICI", "Axis", "PNB", "Bank of Baroda",
            "Canara Bank", "Union Bank", "Indian Bank", "Post Office"
        ]
    
    def parse_statement(self, file_path: str, password: Optional[str] = None) -> Dict:
        """
        Parse PPF statement and extract account details and transactions
        
        Args:
            file_path: Path to the statement file
            password: Password for encrypted PDFs
            
        Returns:
            Dictionary containing account details and transactions
        """
        try:
            file_extension = file_path.lower().split('.')[-1]
            
            if file_extension == 'pdf':
                return self._parse_pdf_statement(file_path, password)
            elif file_extension in ['xlsx', 'xls']:
                return self._parse_excel_statement(file_path)
            elif file_extension == 'csv':
                return self._parse_csv_statement(file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_extension}")
                
        except Exception as e:
            logger.error(f"Error parsing PPF statement: {str(e)}")
            raise
    
    def _parse_pdf_statement(self, file_path: str, password: Optional[str] = None) -> Dict:
        """Parse PDF PPF statement"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Handle password-protected PDFs
                if pdf_reader.is_encrypted:
                    if password:
                        pdf_reader.decrypt(password)
                    else:
                        raise ValueError("PDF is password-protected but no password provided")
                
                # Extract text from all pages
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text()
                
                # Parse the extracted text
                return self._parse_text_content(text)
                
        except Exception as e:
            logger.error(f"Error parsing PDF statement: {str(e)}")
            raise
    
    def _parse_excel_statement(self, file_path: str) -> Dict:
        """Parse Excel PPF statement"""
        try:
            # Try reading with different engines
            try:
                df = pd.read_excel(file_path, engine='openpyxl')
            except:
                df = pd.read_excel(file_path, engine='xlrd')
            
            return self._parse_dataframe(df)
            
        except Exception as e:
            logger.error(f"Error parsing Excel statement: {str(e)}")
            raise
    
    def _parse_csv_statement(self, file_path: str) -> Dict:
        """Parse CSV PPF statement"""
        try:
            df = pd.read_csv(file_path)
            return self._parse_dataframe(df)
            
        except Exception as e:
            logger.error(f"Error parsing CSV statement: {str(e)}")
            raise
    
    def _parse_text_content(self, text: str) -> Dict:
        """Parse text content extracted from PDF"""
        result = {
            'account_details': {},
            'transactions': [],
            'summary': {}
        }
        
        # Split into lines for easier processing
        lines = text.split('\n')
        
        # Extract account number - look for standalone number after "PPF Account"
        # Account number is typically 11 digits, phone is 10 digits
        for i, line in enumerate(lines):
            if 'PPF Account' in line:
                # Account number is usually a few lines before
                for j in range(max(0, i-5), min(i+5, len(lines))):
                    if lines[j].strip().isdigit():
                        num = lines[j].strip()
                        # PPF account numbers are typically 11 digits, phone is 10
                        if len(num) == 11:
                            result['account_details']['account_number'] = num
                            break
                        elif len(num) > 8 and 'account_number' not in result['account_details']:
                            # Fallback to any long number
                            result['account_details']['account_number'] = num
                if 'account_number' in result['account_details']:
                    break
        
        # Extract account holder name - line 3 typically
        if len(lines) > 3:
            name = lines[2].strip()
            if name and len(name) > 3 and len(name) < 100 and name.replace(' ', '').isalpha():
                result['account_details']['account_holder_name'] = name
        
        # Extract bank name
        for bank in self.supported_banks:
            if bank.upper() in text.upper():
                result['account_details']['bank_name'] = bank
                break
        
        # Extract opening date - look for line with "Account Open Date"
        for i, line in enumerate(lines):
            if 'Account Open Date' in line:
                # Date is usually on next line or same line
                date_match = re.search(r'(\d{2}-\d{2}-\d{4})', lines[i] if i < len(lines) else '')
                if not date_match and i+1 < len(lines):
                    date_match = re.search(r'(\d{2}-\d{2}-\d{4})', lines[i+1])
                if date_match:
                    result['account_details']['opening_date'] = self._parse_date(date_match.group(1))
                    break
        
        # Extract current balance - look for "Clear Balance" line
        for i, line in enumerate(lines):
            if 'Clear Balance' in line:
                # Balance is usually on next line with CR suffix
                if i+1 < len(lines):
                    balance_match = re.search(r'([\d,]+\.?\d*)CR', lines[i+1])
                    if balance_match:
                        result['account_details']['current_balance'] = float(balance_match.group(1).replace(',', ''))
                        break
        
        # Extract interest rate
        for i, line in enumerate(lines):
            if 'Interest Rate' in line:
                # Rate is usually on next line
                if i+1 < len(lines):
                    rate_match = re.search(r'([\d.]+)\s*%', lines[i+1])
                    if rate_match:
                        result['account_details']['interest_rate'] = float(rate_match.group(1))
                        break
        
        # Extract transactions - look for lines starting with date (DD/MM/YYYY)
        # Transactions span multiple lines, need to collect them
        i = 0
        while i < len(lines):
            line = lines[i]
            # Look for date pattern at start of line
            date_match = re.match(r'^(\d{2}/\d{2}/\d{4})', line)
            if date_match:
                trans_date = date_match.group(1)
                description_parts = [line[10:].strip()]  # Everything after date
                
                # Look ahead for the line with amounts (contains two numbers at end)
                j = i + 1
                amount = None
                balance = None
                while j < len(lines) and j < i + 10:  # Look up to 10 lines ahead
                    next_line = lines[j]
                    # Check if this line has the amounts (pattern: - - amount balance)
                    amount_match = re.search(r'[-\s]+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)$', next_line)
                    if amount_match:
                        amount = float(amount_match.group(1).replace(',', ''))
                        balance = float(amount_match.group(2).replace(',', ''))
                        # Add description part before amounts
                        desc_part = next_line[:amount_match.start()].strip()
                        if desc_part:
                            description_parts.append(desc_part)
                        break
                    else:
                        # This line is part of description
                        if next_line.strip() and not re.match(r'^\d{2}/\d{2}/\d{4}', next_line):
                            description_parts.append(next_line.strip())
                    j += 1
                
                if amount is not None and balance is not None:
                    description = ' '.join(description_parts)
                    
                    # Determine transaction type
                    trans_type = 'deposit'
                    if 'INTEREST' in description.upper():
                        trans_type = 'interest'
                    elif 'WITHDRAWAL' in description.upper() or 'DEBIT' in description.upper():
                        trans_type = 'withdrawal'
                    elif 'DEPOSIT' in description.upper() or 'DEP' in description.upper() or 'TFR' in description.upper():
                        trans_type = 'deposit'
                    
                    result['transactions'].append({
                        'transaction_date': self._parse_date(trans_date),
                        'transaction_type': trans_type,
                        'amount': amount,
                        'balance_after_transaction': balance,
                        'description': description
                    })
                    i = j  # Skip to the line after amounts
            i += 1
        
        return result
    
    def _parse_dataframe(self, df: pd.DataFrame) -> Dict:
        """Parse PPF data from DataFrame (Excel/CSV)"""
        result = {
            'account_details': {},
            'transactions': [],
            'summary': {}
        }
        
        # Normalize column names
        df.columns = df.columns.str.lower().str.strip()
        
        # Try to identify account details from first few rows or specific columns
        # This is a generic approach - would need customization for specific formats
        
        # Look for account number
        for col in df.columns:
            if 'account' in col and 'number' in col:
                if not df[col].isna().all():
                    result['account_details']['account_number'] = str(df[col].iloc[0])
                    break
        
        # Look for account holder name
        for col in df.columns:
            if 'name' in col or 'holder' in col:
                if not df[col].isna().all():
                    result['account_details']['account_holder_name'] = str(df[col].iloc[0])
                    break
        
        # Look for transactions
        date_col = None
        type_col = None
        amount_col = None
        balance_col = None
        
        for col in df.columns:
            if 'date' in col:
                date_col = col
            elif 'type' in col or 'particular' in col or 'description' in col:
                type_col = col
            elif 'amount' in col or 'deposit' in col or 'credit' in col:
                amount_col = col
            elif 'balance' in col:
                balance_col = col
        
        if date_col and amount_col:
            for _, row in df.iterrows():
                if pd.notna(row[date_col]) and pd.notna(row[amount_col]):
                    transaction = {
                        'transaction_date': self._parse_date(str(row[date_col])),
                        'amount': float(str(row[amount_col]).replace(',', ''))
                    }
                    
                    if type_col and pd.notna(row[type_col]):
                        trans_type = str(row[type_col]).lower()
                        if 'deposit' in trans_type or 'credit' in trans_type:
                            transaction['transaction_type'] = 'deposit'
                        elif 'interest' in trans_type:
                            transaction['transaction_type'] = 'interest'
                        elif 'withdrawal' in trans_type or 'debit' in trans_type:
                            transaction['transaction_type'] = 'withdrawal'
                        else:
                            transaction['transaction_type'] = 'deposit'
                    else:
                        transaction['transaction_type'] = 'deposit'
                    
                    if balance_col and pd.notna(row[balance_col]):
                        transaction['balance_after_transaction'] = float(str(row[balance_col]).replace(',', ''))
                    
                    result['transactions'].append(transaction)
        
        # Calculate summary if not already present
        if result['transactions']:
            result['account_details']['current_balance'] = result['transactions'][-1].get('balance_after_transaction', 0)
            result['account_details']['total_deposits'] = sum(
                t['amount'] for t in result['transactions'] if t['transaction_type'] == 'deposit'
            )
            result['account_details']['total_interest_earned'] = sum(
                t['amount'] for t in result['transactions'] if t['transaction_type'] == 'interest'
            )
        
        return result
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse date string to ISO format"""
        if not date_str:
            return None
        
        date_formats = [
            '%d-%m-%Y', '%d/%m/%Y', '%d-%m-%y', '%d/%m/%y',
            '%Y-%m-%d', '%Y/%m/%d',
            '%d %b %Y', '%d %B %Y',
            '%b %d, %Y', '%B %d, %Y'
        ]
        
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(str(date_str).strip(), fmt)
                return parsed_date.date().isoformat()
            except ValueError:
                continue
        
        logger.warning(f"Could not parse date: {date_str}")
        return None
    
    def validate_ppf_data(self, data: Dict) -> Tuple[bool, List[str]]:
        """
        Validate parsed PPF data
        
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        if not data.get('account_details'):
            errors.append("No account details found")
        else:
            account = data['account_details']
            
            if not account.get('account_number'):
                errors.append("Account number not found")
            
            if not account.get('account_holder_name'):
                errors.append("Account holder name not found")
            
            if not account.get('bank_name'):
                errors.append("Bank name not found")
        
        if not data.get('transactions'):
            errors.append("No transactions found")
        
        return (len(errors) == 0, errors)

# Made with Bob