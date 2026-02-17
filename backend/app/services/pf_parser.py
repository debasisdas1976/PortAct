"""
Provident Fund (EPF/PF) Statement Parser
Supports PDF statements from EPFO (Employees' Provident Fund Organisation)
"""
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import pdfplumber
import PyPDF2
from io import BytesIO


class PFStatementParser:
    """Parser for PF/EPF account statements"""
    
    def __init__(self, file_content: bytes, password: Optional[str] = None):
        self.file_content = file_content
        self.password = password or ""
        self.account_data = {}
        self.transactions = []
    
    def parse(self) -> Tuple[Dict, List[Dict]]:
        """
        Parse PF statement and extract account details and transactions
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
            raise ValueError(f"Failed to parse PF statement: {str(e)}")
    
    def _extract_text_from_pdf(self) -> str:
        """Extract text content from PDF using pdfplumber and PyPDF2 fallback"""
        try:
            pdf_file = BytesIO(self.file_content)
            text = ""
            pdfplumber_failed_pages = []
            
            # Try pdfplumber first
            try:
                with pdfplumber.open(pdf_file, password=self.password) as pdf:
                    total_pages = len(pdf.pages)
                    print(f"PDF has {total_pages} pages")
                    
                    # Extract text from all pages
                    for i in range(total_pages):
                        try:
                            page = pdf.pages[i]
                            page_text = page.extract_text(layout=False)
                            if page_text:
                                text += page_text + "\n"
                                print(f"Successfully extracted text from page {i+1} using pdfplumber")
                            else:
                                pdfplumber_failed_pages.append(i)
                        except Exception as e:
                            print(f"pdfplumber failed for page {i+1}: {e}")
                            pdfplumber_failed_pages.append(i)
            except Exception as e:
                print(f"pdfplumber failed: {e}")
                pdfplumber_failed_pages = list(range(12))  # Assume 12 pages
            
            # If pdfplumber failed on any pages, use PyPDF2 for ALL pages
            if pdfplumber_failed_pages:
                print(f"pdfplumber failed on {len(pdfplumber_failed_pages)} pages, using PyPDF2 for all pages...")
                pdf_file.seek(0)  # Reset file pointer
                text = ""  # Reset text to extract from all pages with PyPDF2
                
                try:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    
                    # Decrypt if needed
                    if pdf_reader.is_encrypted:
                        if self.password:
                            pdf_reader.decrypt(self.password)
                        else:
                            pdf_reader.decrypt("")  # Try empty password
                    
                    for i, page in enumerate(pdf_reader.pages):
                        try:
                            page_text = page.extract_text()
                            if page_text:
                                text += page_text + "\n"
                                print(f"Successfully extracted text from page {i+1} using PyPDF2")
                        except Exception as e:
                            print(f"PyPDF2 failed for page {i+1}: {e}")
                            continue
                except Exception as e:
                    print(f"PyPDF2 fallback failed: {e}")
            
            if not text.strip():
                raise ValueError("No text could be extracted from PDF")
            
            print(f"Total text extracted: {len(text)} characters")
            return text
            
        except Exception as e:
            raise ValueError(f"Failed to extract text from PDF: {str(e)}")
    
    def _parse_account_details(self, text: str) -> Dict:
        """Extract account details from statement text"""
        account_data = {}
        
        # Extract Member ID (PF Number) - Format: PYKRP00192140000069547
        # PyPDF2 format: 'सदस्य आईडी / नामPYKRP00192140000069547/' (no space before ID)
        # pdfplumber format: 'Member Id / Name PYKRP00192140000069547/' (with space)
        member_id_patterns = [
            r'सदस्य\s*आईडी\s*/\s*नाम([A-Z0-9]+)/',  # PyPDF2: Hindi text directly followed by ID
            r'Member\s*Id\s*/\s*Name\s+([A-Z0-9]+)/',  # pdfplumber: with space
            r'Member\s*ID\s*/\s*Name\s+([A-Z0-9]+)/',
        ]
        for pattern in member_id_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                member_id = match.group(1).strip()
                account_data['pf_number'] = member_id
                # Use last 12 digits as UAN if not found separately
                if len(member_id) >= 12:
                    account_data['uan_number'] = member_id[-12:]
                break
        
        # Extract Member Name - comes after Member ID
        # PyPDF2 format: 'सदस्य आईडी / नामPYKRP00192140000069547/\nDEBASIS DASEmployer'
        # The name is between the '/' and 'Employer' or 'िनयोक्ता'
        name_patterns = [
            r'सदस्य\s*आईडी\s*/\s*नाम[A-Z0-9]+/\s*([A-Z\s]+?)(?:Employer|िनयोक्ता)',  # PyPDF2 format
            r'Member\s*Id\s*/\s*Name\s+[A-Z0-9]+/\s*([A-Z\s]+?)(?:\s+Employer)',  # pdfplumber format
            r'Member\s*ID\s*/\s*Name\s+[A-Z0-9]+/\s*([A-Z\s]+?)(?:\s+Employer)',
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                name = match.group(1).strip()
                # Clean up name - remove newlines and extra spaces
                name = re.sub(r'[\n\r]+', ' ', name)
                name = re.sub(r'\s+', ' ', name).strip()
                if len(name) > 2:
                    account_data['account_holder_name'] = name
                    break
        
        # Extract Establishment ID and Name
        # PyPDF2 format: 'स्थापना आईडी / नामPYKRP0019214000/IBM \nINDIA PVT LTDEmployee'
        # The establishment name is between '/' and 'Employee' or 'कमर्चारी'
        establishment_patterns = [
            r'स्थापना\s*आईडी\s*/\s*नाम([A-Z0-9]+)/([A-Z0-9\s&\.\-,\n]+?)(?:Employee|कमर्चारी)',  # PyPDF2
            r'Establishment\s*Id\s*/\s*Name\s+([A-Z0-9]+)/([A-Z0-9\s&\.\-,]+?)(?:\s+Employee)',  # pdfplumber
        ]
        for pattern in establishment_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                establishment_id = match.group(1).strip()
                establishment_name = match.group(2).strip()
                # Clean up name - remove newlines and extra spaces
                establishment_name = re.sub(r'[\n\r]+', ' ', establishment_name)
                establishment_name = re.sub(r'\s+', ' ', establishment_name).strip()
                account_data['employer_name'] = establishment_name
                break
        
        # If we didn't find establishment name, try simpler pattern
        if 'employer_name' not in account_data:
            establishment_match = re.search(r'Establishment\s*Id\s*/\s*Name\s+([A-Z0-9]+)/([A-Z0-9\s&\.\-,]+?)(?:\s+Employee)', text, re.IGNORECASE)
            if establishment_match:
                est_id = establishment_match.group(1).strip()
                est_name_part1 = establishment_match.group(2).strip()
                
                # Look for continuation on next line (Hindi text)
                hindi_match = re.search(r'स्थापना\s*आईडी\s*/\s*नाम\s+([A-Z0-9\s&\.\-,]+?)(?:\s+कमर्चारी)', text)
                if hindi_match:
                    est_name_part2 = hindi_match.group(1).strip()
                    est_name = f"{est_name_part1} {est_name_part2}"
                else:
                    est_name = est_name_part1
                
                # Clean up establishment name
                est_name = re.sub(r'\s+', ' ', est_name).strip()
                if len(est_name) > 2:
                    account_data['employer_name'] = est_name
        
        # Extract Employee Share (total employee contribution)
        # PyPDF2 format: 'कमर्चारी शेयर8244732' (Hindi text + number concatenated)
        # pdfplumber format: 'Employee Share 8244732' (with space)
        employee_share_patterns = [
            r'कमर्चारी\s*शेयर(\d+)',  # PyPDF2: Hindi text directly followed by number
            r'Employee\s*[Ss]hare\s+(\d+)',  # pdfplumber: with space
        ]
        for pattern in employee_share_patterns:
            match = re.search(pattern, text)
            if match:
                account_data['employee_contribution'] = float(match.group(1))
                break
        
        # Extract Employer Share (total employer contribution)
        # PyPDF2 format: 'िनयोक्ता शेयर7318796' (Hindi text + number concatenated)
        # pdfplumber format: 'Employer Share 7318796' (with space)
        employer_share_patterns = [
            r'िनयोक्ता\s*शेयर(\d+)',  # PyPDF2: Hindi text directly followed by number
            r'Employer\s*[Ss]hare\s+(\d+)',  # pdfplumber: with space
        ]
        for pattern in employer_share_patterns:
            match = re.search(pattern, text)
            if match:
                account_data['employer_contribution'] = float(match.group(1))
                break
        
        # Calculate current balance (employee + employer)
        if 'employee_contribution' in account_data and 'employer_contribution' in account_data:
            account_data['current_balance'] = (
                account_data['employee_contribution'] + 
                account_data['employer_contribution']
            )
        
        # Extract pension contribution if present
        pension_match = re.search(r'Pension\s*contribution\s+(\d+)', text, re.IGNORECASE)
        if pension_match:
            account_data['pension_contribution'] = float(pension_match.group(1))
        else:
            account_data['pension_contribution'] = 0.0
        
        # Default interest rate for EPF
        account_data['interest_rate'] = 8.25
        
        # Default total interest earned to 0 (will be calculated from transactions)
        account_data['total_interest_earned'] = 0.0
        
        # Determine if account is active
        if re.search(r'(?:Inactive|Closed|Settled)', text, re.IGNORECASE):
            account_data['is_active'] = False
        else:
            account_data['is_active'] = True
        
        # Default date of joining if not found
        if 'date_of_joining' not in account_data:
            account_data['date_of_joining'] = datetime.now().strftime('%Y-%m-%d')
        
        return account_data
    
    def _parse_transactions(self, text: str) -> List[Dict]:
        """Extract transactions from statement text"""
        transactions = []
        
        # Look for transaction lines
        # Format: "Cont. For Due-Month" on one line, amounts on same line, month code on next line
        # Example:
        # Cont. For Due-Month 7098 6557 0 0 541
        # 042010
        
        lines = text.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Look for contribution or interest lines
            if 'Cont. For Due-Month' in line:
                # Check if month code is on same line or next line
                month_code = None
                amounts_line = line
                
                # Try to extract month code from current line first
                month_match = re.search(r'(\d{6})', line)
                if month_match:
                    month_code = month_match.group(1)
                    amounts_line = line
                elif i + 1 < len(lines):
                    # Month code might be on next line (PyPDF2 format)
                    next_line = lines[i + 1].strip()
                    # Format: MMYYYY followed by amounts (e.g., "04201170986557 00541")
                    month_match = re.match(r'^(\d{6})', next_line)
                    if month_match:
                        month_code = month_match.group(1)
                        amounts_line = next_line
                        i += 1  # Skip the next line since we processed it
                
                contribution_transactions = self._parse_contribution_line(amounts_line, month_code)
                if contribution_transactions:
                    transactions.extend(contribution_transactions)
            
            elif 'Int. Updated' in line or 'OB Int. Updated' in line:
                # Check if date is on same line or next line
                date_line = line
                if i + 1 < len(lines) and not re.search(r'\d{2}/\d{2}/\d{4}', line):
                    # Date might be on next line
                    date_line = line + ' ' + lines[i + 1].strip()
                    i += 1
                
                interest_transactions = self._parse_interest_line(date_line)
                if interest_transactions:
                    transactions.extend(interest_transactions)
            
            i += 1
        
        return transactions
    
    def _parse_contribution_line(self, line: str, month_code: Optional[str]) -> List[Dict]:
        """Parse a contribution transaction line and return both employee and employer transactions"""
        try:
            if not month_code:
                return []
            
            # Extract month and year from code (MMYYYY format)
            month = month_code[:2]
            year = month_code[2:]
            transaction_date = f"{year}-{month}-01"
            
            # Extract amounts from the line
            # PyPDF2 format: "MMYYYY" followed by concatenated amounts (e.g., "04201170986557 00541")
            # Remove month code from line to get amounts
            amounts_str = line.replace(month_code, '').strip()
            
            # Try to parse concatenated format first (PyPDF2)
            # Format: employee(5 digits)employer(5 digits) pension(6 digits with leading zeros)
            # Example: "2720125951 001250" means employee=27201, employer=25951, pension=1250
            if len(amounts_str) > 10 and ' ' in amounts_str:
                parts = amounts_str.split()
                if len(parts) >= 2:
                    # First part has employee+employer concatenated
                    concat = parts[0]
                    if len(concat) >= 10:
                        # 5 digits each for employee and employer
                        employee_share = float(concat[:5])
                        employer_share = float(concat[5:10])
                    elif len(concat) >= 8:
                        # Fallback: 4 digits each (older format)
                        employee_share = float(concat[:4])
                        employer_share = float(concat[4:8])
                    else:
                        employee_share = 0
                        employer_share = 0
                    
                    # Last part has pension (remove leading zeros)
                    pension_str = parts[-1].lstrip('0') or '0'
                    pension_contrib = float(pension_str)
                else:
                    return []
            else:
                # Try regular format (pdfplumber)
                amounts = re.findall(r'\b(\d+)\b', line)
                if len(amounts) < 3:
                    return []
                
                employee_share = float(amounts[0])
                employer_share = float(amounts[1])
                pension_contrib = float(amounts[4]) if len(amounts) > 4 else 0
            
            # Return both employee and employer transactions
            transactions_list = [
                {
                    'transaction_date': transaction_date,
                    'transaction_type': 'employee_contribution',
                    'amount': employee_share,
                    'balance_after_transaction': 0,
                    'contribution_type': 'epf',
                    'description': f'Employee contribution for {month}/{year}',
                    'financial_year': None
                },
                {
                    'transaction_date': transaction_date,
                    'transaction_type': 'employer_contribution',
                    'amount': employer_share,
                    'balance_after_transaction': 0,
                    'contribution_type': 'epf',
                    'description': f'Employer contribution for {month}/{year}',
                    'financial_year': None
                }
            ]
            
            return transactions_list
            
        except Exception as e:
            print(f"Error parsing contribution line: {e}")
            return []
    
    def _parse_interest_line(self, line: str) -> List[Dict]:
        """Parse an interest update line - returns TWO transactions (employee and employer interest)"""
        try:
            # Pattern: "Int. Updated upto 31/03/2025595330525989 000"
            # In PyPDF2 format, the amounts are concatenated without spaces
            date_match = re.search(r'upto\s+(\d{2}/\d{2}/\d{4})', line)
            if not date_match:
                return []
            
            transaction_date = self._parse_date(date_match.group(1))
            
            # After the date, look for a long number (10-12 digits) which contains both interest amounts
            # Format: YYYYMMDDEEEEEEAAAAAA where EEEEEE is employee interest, AAAAAA is employer interest
            # Extract everything after the date
            after_date = line[date_match.end():]
            
            # Look for a 10-12 digit number (two 5-6 digit amounts concatenated)
            long_number_match = re.search(r'(\d{10,12})', after_date)
            
            if not long_number_match:
                print(f"DEBUG: No long number found in: {after_date}")
                return []
            
            long_number = long_number_match.group(1)
            print(f"DEBUG: Interest line: {line}")
            print(f"DEBUG: Long number found: {long_number}")
            
            # Split the long number into two equal parts (each 5-6 digits)
            mid_point = len(long_number) // 2
            employee_interest = float(long_number[:mid_point])
            employer_interest = float(long_number[mid_point:])
            
            print(f"DEBUG: Employee interest: {employee_interest}, Employer interest: {employer_interest}")
            
            transactions = []
            
            # Employee interest transaction
            if employee_interest > 0:
                transactions.append({
                    'transaction_date': transaction_date,
                    'transaction_type': 'employee_interest',
                    'amount': employee_interest,
                    'balance_after_transaction': 0,
                    'contribution_type': None,
                    'description': 'Employee Interest',
                    'financial_year': None
                })
            
            # Employer interest transaction
            if employer_interest > 0:
                transactions.append({
                    'transaction_date': transaction_date,
                    'transaction_type': 'employer_interest',
                    'amount': employer_interest,
                    'balance_after_transaction': 0,
                    'contribution_type': None,
                    'description': 'Employer Interest',
                    'financial_year': None
                })
            
            return transactions
            
        except Exception as e:
            print(f"Error parsing interest line: {e}")
            return []
    
    def _parse_date(self, date_str: str) -> str:
        """Parse date string to YYYY-MM-DD format"""
        # Try different date formats
        formats = [
            '%d/%m/%Y',
            '%d-%m-%Y',
            '%d/%m/%y',
            '%d-%m-%y',
            '%Y-%m-%d',
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        # If all formats fail, return current date
        return datetime.now().strftime('%Y-%m-%d')

# Made with Bob
