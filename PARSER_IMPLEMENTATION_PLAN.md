# Bank Statement Parser Implementation Plan

## Executive Summary

This document outlines a comprehensive plan for implementing parsers for all bank statement formats found in the PortAct application. The goal is to create robust, maintainable parsers that can extract transaction data from various bank statement formats (PDF, Excel, CSV) with high accuracy.

---

## 📊 Current Status

### ✅ Completed
- **ICICI Bank Savings Account Parser** (.xls format)
  - Successfully parsing 27 transactions
  - Auto-detects header row
  - Handles old Excel format with xlrd
  - Status: **Production Ready**

- **Base Parser Infrastructure**
  - `BankStatementParser` base class
  - Common utilities (date parsing, amount cleaning, payment method detection)
  - Auto-categorization service with 21 categories
  - Database models and API endpoints

### 🔄 Existing Parsers (Need Testing/Updates)
- HDFCBankParser
- IDFCFirstBankParser  
- SBIBankParser

---

## 📁 Files to Process

### 1. OpTransactionHistory08-01-2026.xls
- **Bank**: ICICI Bank
- **Type**: Savings Account
- **Format**: Excel (.xls - old format)
- **Status**: ✅ **Working** (27 transactions parsed)
- **Action**: None required

### 2. IDFCFIRSTBankstatement_10054824432.xlsx
- **Bank**: IDFC First Bank
- **Type**: Savings Account
- **Format**: Excel (.xlsx - new format)
- **Status**: 🔄 Parser exists, needs testing
- **Priority**: High
- **Estimated Effort**: 2-3 hours

### 3. IDFCFIRSTBankstatement_10059280790.xlsx
- **Bank**: IDFC First Bank
- **Type**: Savings Account
- **Format**: Excel (.xlsx - new format)
- **Status**: 🔄 Parser exists, needs testing
- **Priority**: High
- **Estimated Effort**: 1 hour (same format as #2)

### 4. CCStatement_Past29-12-2025.xls
- **Bank**: Unknown (likely ICICI or HDFC)
- **Type**: Credit Card
- **Format**: Excel (.xls - old format)
- **Status**: ❌ No parser
- **Priority**: High
- **Estimated Effort**: 4-5 hours

### 5. Card_Statement_25Nov2025-24Dec2025.pdf
- **Bank**: Unknown
- **Type**: Credit Card
- **Format**: PDF (7 pages)
- **Status**: ❌ No parser
- **Priority**: Medium
- **Estimated Effort**: 5-6 hours

### 6. IDFC FIRST Bank_Credit Card_Statement_24122025.pdf
- **Bank**: IDFC First Bank
- **Type**: Credit Card
- **Format**: PDF
- **Status**: ❌ No parser
- **Priority**: Medium
- **Estimated Effort**: 5-6 hours

---

## 🏗️ Architecture Design

### Current Structure
```
backend/app/services/
├── bank_statement_parser.py
│   ├── BankStatementParser (base class)
│   ├── ICICIBankParser
│   ├── HDFCBankParser
│   ├── IDFCFirstBankParser
│   └── SBIBankParser
├── expense_categorizer.py
└── scheduler.py
```

### Proposed Enhanced Structure
```
backend/app/services/
├── parsers/
│   ├── __init__.py
│   ├── base_parser.py (BankStatementParser)
│   ├── savings_account/
│   │   ├── __init__.py
│   │   ├── icici_parser.py
│   │   ├── hdfc_parser.py
│   │   ├── idfc_parser.py
│   │   └── sbi_parser.py
│   ├── credit_card/
│   │   ├── __init__.py
│   │   ├── icici_cc_parser.py
│   │   ├── hdfc_cc_parser.py
│   │   └── idfc_cc_parser.py
│   └── utils/
│       ├── __init__.py
│       ├── pdf_utils.py
│       ├── excel_utils.py
│       └── date_utils.py
├── expense_categorizer.py
└── scheduler.py
```

---

## 📋 Implementation Phases

### Phase 1: Foundation & Testing (Week 1)
**Goal**: Validate existing parsers and establish testing framework

#### Tasks:
1. **Create Test Framework** (4 hours)
   - Create `backend/tests/test_parsers.py`
   - Add fixtures for sample statements
   - Implement assertion helpers
   - Set up CI/CD integration

2. **Test ICICI Bank Parser** (2 hours)
   - Verify OpTransactionHistory08-01-2026.xls parsing
   - Document expected output format
   - Create regression tests
   - Validate edge cases

3. **Test IDFC First Bank Parser** (4 hours)
   - Test with IDFCFIRSTBankstatement_10054824432.xlsx
   - Test with IDFCFIRSTBankstatement_10059280790.xlsx
   - Fix any issues found
   - Document column mappings

4. **Test HDFC & SBI Parsers** (4 hours)
   - Create sample test files or use existing
   - Validate parsing logic
   - Fix bugs if any

**Deliverables**:
- ✅ Working test suite
- ✅ Validated ICICI parser
- ✅ Validated IDFC parser
- ✅ Documentation of parser behavior

---

### Phase 2: Credit Card Excel Parser (Week 2)
**Goal**: Implement parser for CCStatement_Past29-12-2025.xls

#### Analysis Steps:
1. **File Analysis** (1 hour)
   ```python
   # Create analysis script
   import pandas as pd
   
   # Read with xlrd
   df = pd.read_excel('CCStatement_Past29-12-2025.xls', engine='xlrd')
   
   # Analyze structure
   print(f"Shape: {df.shape}")
   print(f"Columns: {df.columns.tolist()}")
   print(f"First 10 rows:\n{df.head(10)}")
   print(f"Data types:\n{df.dtypes}")
   ```

2. **Identify Bank** (30 mins)
   - Look for bank name in header
   - Check card number format
   - Identify statement structure

3. **Map Columns** (1 hour)
   - Transaction date
   - Posting date
   - Description/Merchant
   - Amount (debit/credit)
   - Category (if present)
   - Reference number

#### Implementation:
1. **Create CreditCardParser Base Class** (2 hours)
   ```python
   class CreditCardParser(BankStatementParser):
       """Base class for credit card statement parsers"""
       
       def __init__(self, file_path: str):
           super().__init__(file_path)
           self.statement_type = 'credit_card'
       
       def _detect_transaction_type(self, description: str, 
                                    debit: float, credit: float) -> str:
           # Credit cards: debit = expense, credit = payment/refund
           if debit > 0:
               return 'debit'
           elif credit > 0:
               return 'credit'
           return 'transfer'
   ```

2. **Implement Specific Parser** (2 hours)
   - Extend CreditCardParser
   - Implement _parse_excel method
   - Handle credit card specific fields
   - Map to standard transaction format

3. **Testing** (1 hour)
   - Parse CCStatement_Past29-12-2025.xls
   - Validate all transactions extracted
   - Check amount calculations
   - Verify date parsing

**Deliverables**:
- ✅ CreditCardParser base class
- ✅ Working credit card Excel parser
- ✅ Test cases
- ✅ Documentation

---

### Phase 3: Credit Card PDF Parsers (Week 3-4)
**Goal**: Implement parsers for PDF credit card statements

#### Challenges:
- PDF text extraction can be inconsistent
- Tables may not have clear boundaries
- Multi-page statements
- Different layouts per bank

#### Approach:

##### Option A: PyPDF2 + Regex (Current)
```python
def _parse_pdf(self) -> List[Dict[str, Any]]:
    transactions = []
    with open(self.file_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        
        for page in pdf_reader.pages:
            text = page.extract_text()
            # Use regex to extract transactions
            pattern = r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\d,]+\.\d{2})'
            matches = re.findall(pattern, text)
            
            for match in matches:
                # Process each transaction
                pass
    
    return transactions
```

**Pros**: Simple, no extra dependencies
**Cons**: Fragile, hard to maintain, may miss data

##### Option B: pdfplumber (Recommended)
```python
import pdfplumber

def _parse_pdf(self) -> List[Dict[str, Any]]:
    transactions = []
    
    with pdfplumber.open(self.file_path) as pdf:
        for page in pdf.pages:
            # Extract tables
            tables = page.extract_tables()
            
            for table in tables:
                # Process table rows
                for row in table[1:]:  # Skip header
                    if self._is_transaction_row(row):
                        transaction = self._parse_transaction_row(row)
                        transactions.append(transaction)
    
    return transactions
```

**Pros**: Better table extraction, more reliable
**Cons**: Additional dependency (already in requirements.txt)

#### Implementation Steps:

1. **Card_Statement_25Nov2025-24Dec2025.pdf** (6 hours)
   - Analyze PDF structure
   - Identify bank from header
   - Extract transaction table
   - Handle multi-page statements
   - Test thoroughly

2. **IDFC FIRST Bank_Credit Card_Statement_24122025.pdf** (5 hours)
   - Similar to above
   - May reuse IDFC-specific logic
   - Test with existing IDFC parser patterns

**Deliverables**:
- ✅ PDF parsing utilities
- ✅ 2 credit card PDF parsers
- ✅ Comprehensive tests
- ✅ Error handling

---

## 🔧 Technical Implementation Details

### 1. Enhanced Base Parser

```python
class BankStatementParser(ABC):
    """Enhanced base class with better error handling"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.transactions: List[Dict[str, Any]] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def parse(self) -> Dict[str, Any]:
        """Parse and return results with metadata"""
        try:
            transactions = self._parse_file()
            
            return {
                'success': True,
                'transactions': transactions,
                'count': len(transactions),
                'errors': self.errors,
                'warnings': self.warnings,
                'metadata': self._get_metadata()
            }
        except Exception as e:
            return {
                'success': False,
                'transactions': [],
                'count': 0,
                'errors': [str(e)],
                'warnings': self.warnings,
                'metadata': {}
            }
    
    @abstractmethod
    def _parse_file(self) -> List[Dict[str, Any]]:
        """Implement in subclass"""
        pass
    
    def _get_metadata(self) -> Dict[str, Any]:
        """Extract statement metadata"""
        return {
            'file_name': os.path.basename(self.file_path),
            'file_size': os.path.getsize(self.file_path),
            'parsed_at': datetime.now().isoformat(),
            'parser_version': '1.0'
        }
```

### 2. Parser Registry

```python
# backend/app/services/parsers/__init__.py

from typing import Dict, Type
from .base_parser import BankStatementParser
from .savings_account.icici_parser import ICICIBankParser
from .savings_account.hdfc_parser import HDFCBankParser
from .savings_account.idfc_parser import IDFCFirstBankParser
from .credit_card.icici_cc_parser import ICICICreditCardParser

PARSER_REGISTRY: Dict[str, Type[BankStatementParser]] = {
    'icici_bank': ICICIBankParser,
    'hdfc_bank': HDFCBankParser,
    'idfc_first_bank': IDFCFirstBankParser,
    'icici_credit_card': ICICICreditCardParser,
    # Add more as implemented
}

def get_parser(bank_name: str, account_type: str = 'savings') -> Type[BankStatementParser]:
    """Get appropriate parser for bank and account type"""
    key = f"{bank_name}_{account_type}" if account_type != 'savings' else bank_name
    
    if key in PARSER_REGISTRY:
        return PARSER_REGISTRY[key]
    
    # Fallback to generic parser
    return BankStatementParser
```

### 3. Validation Framework

```python
class TransactionValidator:
    """Validate parsed transactions"""
    
    @staticmethod
    def validate_transaction(transaction: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate a single transaction"""
        errors = []
        
        # Required fields
        required = ['transaction_date', 'description', 'amount']
        for field in required:
            if field not in transaction or not transaction[field]:
                errors.append(f"Missing required field: {field}")
        
        # Date validation
        if 'transaction_date' in transaction:
            if not isinstance(transaction['transaction_date'], datetime):
                errors.append("Invalid transaction_date type")
        
        # Amount validation
        if 'amount' in transaction:
            if not isinstance(transaction['amount'], (int, float)):
                errors.append("Invalid amount type")
            elif transaction['amount'] < 0:
                errors.append("Amount cannot be negative")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_batch(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate a batch of transactions"""
        valid = []
        invalid = []
        
        for i, txn in enumerate(transactions):
            is_valid, errors = TransactionValidator.validate_transaction(txn)
            if is_valid:
                valid.append(txn)
            else:
                invalid.append({
                    'index': i,
                    'transaction': txn,
                    'errors': errors
                })
        
        return {
            'valid_count': len(valid),
            'invalid_count': len(invalid),
            'valid_transactions': valid,
            'invalid_transactions': invalid
        }
```

---

## 🧪 Testing Strategy

### 1. Unit Tests

```python
# backend/tests/test_parsers.py

import pytest
from app.services.parsers import ICICIBankParser, get_parser

class TestICICIBankParser:
    
    @pytest.fixture
    def sample_statement(self):
        return "/path/to/OpTransactionHistory08-01-2026.xls"
    
    def test_parse_success(self, sample_statement):
        parser = ICICIBankParser(sample_statement)
        result = parser.parse()
        
        assert result['success'] is True
        assert result['count'] == 27
        assert len(result['transactions']) == 27
    
    def test_transaction_structure(self, sample_statement):
        parser = ICICIBankParser(sample_statement)
        result = parser.parse()
        
        txn = result['transactions'][0]
        assert 'transaction_date' in txn
        assert 'description' in txn
        assert 'amount' in txn
        assert 'transaction_type' in txn
    
    def test_amount_calculation(self, sample_statement):
        parser = ICICIBankParser(sample_statement)
        result = parser.parse()
        
        total_credits = sum(t['amount'] for t in result['transactions'] 
                          if t['transaction_type'] == 'credit')
        total_debits = sum(t['amount'] for t in result['transactions'] 
                         if t['transaction_type'] == 'debit')
        
        assert total_credits > 0
        assert total_debits > 0
```

### 2. Integration Tests

```python
class TestParserIntegration:
    
    def test_upload_and_parse(self, client, auth_headers):
        """Test full upload and parse flow"""
        
        with open('test_statement.xls', 'rb') as f:
            response = client.post(
                '/api/v1/bank-statements/upload',
                files={'file': f},
                data={
                    'bank_account_id': 1,
                    'auto_categorize': True
                },
                headers=auth_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data['transactions_processed'] > 0
```

### 3. Regression Tests

```python
class TestParserRegression:
    """Ensure parsers don't break with updates"""
    
    def test_known_good_statements(self):
        """Test against known good statements"""
        
        test_cases = [
            ('icici_statement_v1.xls', 27),
            ('idfc_statement_v1.xlsx', 45),
            # Add more
        ]
        
        for file_path, expected_count in test_cases:
            parser = get_parser_for_file(file_path)
            result = parser.parse()
            
            assert result['success'] is True
            assert result['count'] == expected_count
```

---

## 📊 Progress Tracking

### Metrics to Track:
1. **Parser Coverage**
   - Number of banks supported
   - Number of statement formats supported
   - Percentage of user statements successfully parsed

2. **Accuracy Metrics**
   - Transaction extraction rate (% of transactions found)
   - Field accuracy (% of fields correctly extracted)
   - Error rate (% of statements that fail to parse)

3. **Performance Metrics**
   - Average parse time per statement
   - Memory usage
   - Success rate over time

### Dashboard:
```python
# Add to admin panel
{
    'total_statements_uploaded': 1234,
    'successfully_parsed': 1180,
    'failed_to_parse': 54,
    'success_rate': '95.6%',
    'parsers': {
        'icici_bank': {'count': 450, 'success_rate': '98%'},
        'hdfc_bank': {'count': 320, 'success_rate': '94%'},
        'idfc_first_bank': {'count': 280, 'success_rate': '96%'},
        'credit_cards': {'count': 184, 'success_rate': '89%'}
    }
}
```

---

## 🚀 Deployment Plan

### Phase 1: Staging (Week 5)
1. Deploy updated parsers to staging
2. Run tests against production-like data
3. Monitor error rates
4. Fix any issues found

### Phase 2: Gradual Rollout (Week 6)
1. Enable for 10% of users
2. Monitor metrics closely
3. Increase to 50% if stable
4. Full rollout if no issues

### Phase 3: Monitoring (Ongoing)
1. Set up alerts for parse failures
2. Weekly review of error logs
3. Monthly parser performance review
4. Quarterly feature improvements

---

## 📚 Documentation Requirements

### 1. Developer Documentation
- Parser architecture overview
- How to add a new parser
- Testing guidelines
- Debugging tips

### 2. User Documentation
- Supported banks and formats
- How to upload statements
- Troubleshooting guide
- FAQ

### 3. API Documentation
- Parser endpoints
- Request/response formats
- Error codes
- Examples

---

## 🔒 Security Considerations

### 1. File Upload Security
- Validate file types
- Scan for malware
- Limit file size (max 10MB)
- Sanitize file names

### 2. Data Privacy
- Encrypt statements at rest
- Delete after processing (optional)
- Mask sensitive data in logs
- Comply with data protection regulations

### 3. Error Handling
- Don't expose internal paths in errors
- Log errors securely
- Rate limit upload attempts
- Implement CAPTCHA if needed

---

## 💰 Cost Estimation

### Development Time:
- **Phase 1** (Foundation): 14 hours
- **Phase 2** (Credit Card Excel): 8 hours
- **Phase 3** (Credit Card PDFs): 11 hours
- **Testing & QA**: 10 hours
- **Documentation**: 5 hours
- **Deployment & Monitoring**: 4 hours

**Total**: ~52 hours

### Infrastructure:
- Storage for statements: ~$5/month
- Additional compute: ~$10/month
- Monitoring tools: ~$5/month

**Total**: ~$20/month

---

## 🎯 Success Criteria

### Must Have:
- ✅ All 6 statement files parse successfully
- ✅ 95%+ transaction extraction accuracy
- ✅ Comprehensive test coverage (>80%)
- ✅ Error handling for edge cases
- ✅ Documentation complete

### Nice to Have:
- ✅ Parser performance <2 seconds per statement
- ✅ Automatic bank detection
- ✅ Support for additional formats
- ✅ Admin dashboard for monitoring
- ✅ User feedback mechanism

---

## 📞 Support & Maintenance

### Ongoing Tasks:
1. **Monthly**: Review parser performance metrics
2. **Quarterly**: Update parsers for bank format changes
3. **As Needed**: Add support for new banks
4. **Continuous**: Monitor error logs and fix issues

### Escalation Path:
1. **Level 1**: Automated error detection
2. **Level 2**: Developer review of failed parses
3. **Level 3**: Manual intervention for complex cases
4. **Level 4**: Contact bank for format clarification

---

## 🔄 Future Enhancements

### Short Term (3-6 months):
1. Add 10 more bank parsers
2. Implement OCR for scanned PDFs
3. Add statement validation rules
4. Create parser configuration UI

### Medium Term (6-12 months):
1. Machine learning for format detection
2. Automatic parser generation
3. Multi-language support
4. Mobile app integration

### Long Term (12+ months):
1. AI-powered transaction categorization
2. Predictive analytics
3. Integration with accounting software
4. Open API for third-party integrations

---

## 📋 Appendix

### A. File Format Specifications

#### ICICI Bank Savings (.xls)
```
Row 11: Headers (S No., Value Date, Transaction Date, Cheque Number, 
                 Transaction Remarks, Withdrawal Amount(INR), 
                 Deposit Amount(INR), Balance(INR))
Row 12+: Transaction data
```

#### IDFC First Bank (.xlsx)
```
TBD - Need to analyze actual file
```

#### Credit Card Statements
```
TBD - Need to analyze actual files
```

### B. Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Header row not found | Implement fuzzy matching for header detection |
| Date format varies | Support multiple date formats |
| Amount has currency symbols | Clean with regex before parsing |
| Multi-page PDFs | Process all pages sequentially |
| Merged cells in Excel | Use openpyxl to handle merged cells |

### C. Useful Resources

- [PyPDF2 Documentation](https://pypdf2.readthedocs.io/)
- [pdfplumber Documentation](https://github.com/jsvine/pdfplumber)
- [pandas Excel Documentation](https://pandas.pydata.org/docs/reference/api/pandas.read_excel.html)
- [openpyxl Documentation](https://openpyxl.readthedocs.io/)

---

## ✅ Next Steps

1. **Review this plan** with stakeholders
2. **Prioritize** which parsers to implement first
3. **Allocate resources** (developer time, budget)
4. **Set timeline** for each phase
5. **Begin Phase 1** implementation

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-14  
**Author**: Bob (AI Assistant)  
**Status**: Draft - Awaiting Approval