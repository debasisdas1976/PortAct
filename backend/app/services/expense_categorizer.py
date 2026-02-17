"""
Expense Auto-Categorization Service
Automatically categorizes expenses based on merchant names and keywords
Includes fuzzy matching and learning from user corrections
"""
from typing import Optional, Dict, List, Tuple
from sqlalchemy.orm import Session
from app.models.expense_category import ExpenseCategory
from app.models.expense import Expense
import difflib
from collections import Counter


class ExpenseCategorizer:
    """Service to auto-categorize expenses based on keywords"""
    
    # Enhanced category keywords mapping with comprehensive Indian merchants
    DEFAULT_KEYWORDS = {
        'Food & Dining': [
            # Food Delivery
            'swiggy', 'zomato', 'uber eats', 'dunzo', 'shadowfax', 'bundl technologies',
            # Restaurants & Cafes
            'dominos', 'pizza hut', 'kfc', 'mcdonald', 'burger king', 'subway',
            'starbucks', 'cafe coffee day', 'barista', 'costa coffee',
            'haldiram', 'bikanervala', 'sagar ratna', 'saravana bhavan',
            # Generic
            'restaurant', 'cafe', 'coffee', 'food', 'dining', 'eatery',
            'meal', 'breakfast', 'lunch', 'dinner', 'bakery', 'sweet shop'
        ],
        'Groceries': [
            # Online Grocery
            'bigbasket', 'grofers', 'blinkit', 'zepto', 'dunzo', 'jiomart',
            'amazon fresh', 'amazon pantry', 'instamart', 'swiggy instamart',
            # Supermarkets
            'dmart', 'reliance fresh', 'more', 'spencer', 'star bazaar',
            'hypercity', 'big bazaar', 'easyday', 'nilgiris', '24 seven',
            # Local stores
            'kirana', 'provision', 'general store',
            # Generic
            'grocery', 'supermarket', 'vegetables', 'fruits', 'milk', 'bread',
            'food items', 'household', 'provisions'
        ],
        'Transportation': [
            # Ride-sharing
            'uber', 'ola', 'rapido', 'blu smart', 'meru', 'taxi',
            # Fuel
            'indian oil', 'bharat petroleum', 'hp petrol', 'shell', 'essar',
            'petrol', 'diesel', 'fuel', 'cng', 'gas station',
            # Public Transport
            'metro', 'dmrc', 'bmtc', 'best', 'bus', 'train', 'railway',
            # Parking & Tolls
            'parking', 'toll', 'fastag', 'paytm fastag',
            # Generic
            'transport', 'cab', 'auto', 'rickshaw', 'vehicle'
        ],
        'Shopping': [
            # E-commerce
            'amazon', 'amazonin', 'flipkart', 'myntra', 'ajio', 'meesho',
            'snapdeal', 'shopclues', 'tata cliq', 'nykaa', 'purplle',
            # Fashion
            'zara', 'h&m', 'max fashion', 'pantaloons', 'westside',
            'lifestyle', 'shoppers stop', 'central', 'reliance trends',
            # Electronics
            'croma', 'reliance digital', 'vijay sales', 'poorvika',
            # Furniture & Home
            'ikea', 'pepperfry', 'urban ladder', 'hometown', 'fabindia',
            # Generic
            'shopping', 'mall', 'store', 'retail', 'fashion', 'clothing',
            'shoes', 'electronics', 'mobile', 'laptop', 'accessories'
        ],
        'Entertainment': [
            # Streaming
            'netflix', 'amazon prime', 'prime video', 'hotstar', 'disney',
            'zee5', 'sony liv', 'voot', 'alt balaji', 'mx player',
            'spotify', 'youtube premium', 'gaana', 'jio saavn', 'wynk',
            # Movies & Theater
            'pvr', 'inox', 'cinepolis', 'carnival', 'movie', 'cinema',
            'theatre', 'multiplex', 'bookmyshow', 'paytm movies',
            # Gaming
            'steam', 'playstation', 'xbox', 'nintendo', 'gaming',
            # Generic
            'entertainment', 'subscription', 'ott', 'streaming'
        ],
        'Utilities': [
            # Telecom
            'airtel', 'jio', 'vodafone', 'vi', 'bsnl', 'mtnl',
            'mobile recharge', 'prepaid', 'postpaid', 'phone bill',
            # Internet & DTH
            'broadband', 'wifi', 'internet', 'fiber', 'act fibernet',
            'tata sky', 'dish tv', 'sun direct', 'dth', 'cable',
            # Utilities
            'electricity', 'power', 'bescom', 'msedcl', 'tata power',
            'water', 'water bill', 'gas', 'lpg', 'indane', 'bharat gas',
            # Bill Payment
            'bill payment', 'bbps', 'billdesk', 'utility', 'paytm bill'
        ],
        'Healthcare': [
            # Hospitals & Clinics
            'apollo', 'fortis', 'max', 'medanta', 'manipal', 'narayana',
            'hospital', 'clinic', 'doctor', 'medical', 'health',
            # Pharmacy
            'apollo pharmacy', 'medplus', 'netmeds', '1mg', 'pharmeasy',
            'pharmacy', 'medicine', 'chemist', 'drug store',
            # Diagnostics
            'thyrocare', 'dr lal pathlabs', 'metropolis', 'lab test',
            'diagnostic', 'pathology', 'x-ray', 'scan',
            # Insurance
            'health insurance', 'mediclaim', 'star health', 'care health',
            # Fitness
            'cult fit', 'healthifyme', 'fitness', 'gym', 'yoga'
        ],
        'Education': [
            # Schools & Colleges
            'school', 'college', 'university', 'institute', 'academy',
            'tuition', 'coaching', 'classes',
            # Online Learning
            'udemy', 'coursera', 'byju', 'unacademy', 'vedantu',
            'toppr', 'white hat jr', 'upgrad', 'simplilearn',
            # Books & Stationery
            'amazon books', 'flipkart books', 'crossword', 'landmark',
            'books', 'stationery', 'notebook', 'pen',
            # Generic
            'education', 'learning', 'course', 'training', 'exam fee'
        ],
        'Travel': [
            # Airlines
            'indigo', 'spicejet', 'air india', 'vistara', 'go air',
            'air asia', 'flight', 'airline', 'airways',
            # Hotels & Stays
            'oyo', 'treebo', 'fab hotels', 'airbnb', 'booking.com',
            'makemytrip', 'goibibo', 'cleartrip', 'yatra', 'ixigo',
            'hotel', 'resort', 'accommodation', 'stay',
            # Transport
            'irctc', 'train', 'railway', 'redbus', 'abhibus', 'bus booking',
            # Generic
            'travel', 'vacation', 'holiday', 'tour', 'trip'
        ],
        'Insurance': [
            'insurance', 'premium', 'policy', 'lic', 'hdfc life',
            'icici prudential', 'sbi life', 'max life', 'bajaj allianz',
            'tata aia', 'kotak life', 'birla sun life', 'aegon life',
            'star health', 'care health', 'acko', 'digit insurance',
            'vehicle insurance', 'car insurance', 'bike insurance'
        ],
        'Investment': [
            # Trading Platforms
            'zerodha', 'groww', 'upstox', 'angel one', 'paytm money',
            '5paisa', 'iifl', 'motilal oswal', 'sharekhan',
            # Mutual Funds
            'mutual fund', 'mf', 'sip', 'systematic investment',
            'amc', 'hdfc mf', 'icici mf', 'sbi mf',
            # Generic
            'stock', 'share', 'equity', 'investment', 'trading',
            'demat', 'portfolio', 'fund'
        ],
        'Rent': [
            'rent', 'lease', 'housing', 'apartment', 'flat',
            'maintenance', 'society', 'housing society', 'pg',
            'paying guest', 'accommodation', 'landlord'
        ],
        'Personal Care': [
            # Salons & Spas
            'salon', 'spa', 'lakme', 'jawed habib', 'naturals',
            'green trends', 'toni and guy', 'looks salon',
            # Beauty & Grooming
            'beauty', 'grooming', 'haircut', 'parlour', 'facial',
            'manicure', 'pedicure', 'waxing', 'massage',
            # Products
            'nykaa', 'purplle', 'mcaffeine', 'mamaearth', 'wow',
            'cosmetics', 'skincare', 'makeup', 'personal care'
        ],
        'Gifts & Donations': [
            'gift', 'donation', 'charity', 'ngo', 'temple',
            'church', 'mosque', 'gurudwara', 'religious',
            'contribution', 'offering', 'dakshina', 'prasad'
        ],
        'Fees & Charges': [
            'fee', 'charge', 'penalty', 'fine', 'late fee',
            'processing fee', 'service charge', 'gst', 'tax',
            'annual fee', 'membership fee', 'registration'
        ],
        'ATM Withdrawal': [
            'atm', 'cash withdrawal', 'withdrawal', 'cash'
        ],
        'Transfer': [
            'transfer', 'neft', 'imps', 'rtgs', 'upi transfer',
            'fund transfer', 'money transfer', 'payment to',
            'sent to', 'transferred to'
        ],
        'Salary': [
            'salary', 'wages', 'income', 'payment received',
            'credit salary', 'sal credit', 'payroll', 'stipend'
        ],
        'Refund': [
            'refund', 'reversal', 'cashback', 'reward',
            'credit adjustment', 'return', 'cancelled',
            'refunded', 'reversed'
        ]
    }
    
    def __init__(self, db: Session, user_id: Optional[int] = None):
        self.db = db
        self.user_id = user_id
        self._category_cache: Dict[str, int] = {}
        self._learned_patterns: Dict[str, Dict[int, int]] = {}  # merchant -> {category_id: count}
        self._load_categories()
        if user_id:
            self._load_learned_patterns()
    
    def _load_categories(self):
        """Load categories from database into cache"""
        categories = self.db.query(ExpenseCategory).all()
        for category in categories:
            self._category_cache[category.name.lower()] = category.id
    
    def _load_learned_patterns(self):
        """
        Learn from user's past categorizations
        Analyzes manually categorized expenses to identify patterns
        """
        if not self.user_id:
            return
        
        # Get all manually categorized expenses for this user
        categorized_expenses = self.db.query(Expense).filter(
            Expense.user_id == self.user_id,
            Expense.category_id.isnot(None),
            Expense.is_categorized == True
        ).all()
        
        # Build pattern dictionary: merchant_name -> category_id frequency
        for expense in categorized_expenses:
            if expense.merchant_name:
                merchant_key = expense.merchant_name.lower().strip()
                if merchant_key not in self._learned_patterns:
                    self._learned_patterns[merchant_key] = Counter()
                self._learned_patterns[merchant_key][expense.category_id] += 1
    
    def _fuzzy_match(self, text: str, keywords: List[str], threshold: float = 0.8) -> Optional[str]:
        """
        Perform fuzzy matching on text against keywords
        Returns the best matching keyword if similarity > threshold
        """
        text_lower = text.lower()
        best_match = None
        best_ratio = 0.0
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            
            # First try exact substring match (fastest)
            if keyword_lower in text_lower:
                return keyword
            
            # Then try fuzzy matching for partial matches
            # Use SequenceMatcher for similarity ratio
            ratio = difflib.SequenceMatcher(None, text_lower, keyword_lower).ratio()
            
            # Also check if keyword words are in text (for multi-word keywords)
            keyword_words = keyword_lower.split()
            if len(keyword_words) > 1:
                words_found = sum(1 for word in keyword_words if word in text_lower)
                word_ratio = words_found / len(keyword_words)
                ratio = max(ratio, word_ratio)
            
            if ratio > best_ratio and ratio >= threshold:
                best_ratio = ratio
                best_match = keyword
        
        return best_match
    
    def _get_learned_category(self, merchant_name: str) -> Optional[int]:
        """
        Get category based on learned patterns from user's past categorizations
        Returns the most frequently used category for this merchant
        """
        if not merchant_name or not self._learned_patterns:
            return None
        
        merchant_key = merchant_name.lower().strip()
        
        # Exact match
        if merchant_key in self._learned_patterns:
            # Return the category with highest frequency
            category_counts = self._learned_patterns[merchant_key]
            if category_counts:
                return category_counts.most_common(1)[0][0]
        
        # Fuzzy match on learned merchants
        for learned_merchant, category_counts in self._learned_patterns.items():
            ratio = difflib.SequenceMatcher(None, merchant_key, learned_merchant).ratio()
            if ratio >= 0.85:  # High threshold for learned patterns
                return category_counts.most_common(1)[0][0]
        
        return None
    
    def categorize(self, description: str, merchant_name: Optional[str] = None, use_fuzzy: bool = True) -> Optional[int]:
        """
        Categorize an expense based on description and merchant name
        Uses multiple strategies in order of priority:
        1. Learned patterns from user's past categorizations
        2. Exact keyword matching from database categories
        3. Fuzzy keyword matching
        4. Default keywords with fuzzy matching
        
        Returns category_id if found, None otherwise
        """
        # Strategy 1: Check learned patterns first (highest priority)
        if merchant_name:
            learned_category = self._get_learned_category(merchant_name)
            if learned_category:
                return learned_category
        
        # Combine description and merchant name for matching
        text_to_match = f"{description} {merchant_name or ''}".lower()
        
        # Strategy 2: Try exact matching with database categories
        categories = self.db.query(ExpenseCategory).filter(
            ExpenseCategory.keywords.isnot(None)
        ).all()
        
        for category in categories:
            if category.keywords:
                keywords = [k.strip().lower() for k in category.keywords.split(',')]
                # Exact substring match
                if any(keyword in text_to_match for keyword in keywords):
                    return category.id
        
        # Strategy 3: Try fuzzy matching with database categories (if enabled)
        if use_fuzzy:
            for category in categories:
                if category.keywords:
                    keywords = [k.strip() for k in category.keywords.split(',')]
                    fuzzy_match = self._fuzzy_match(text_to_match, keywords, threshold=0.75)
                    if fuzzy_match:
                        return category.id
        
        # Strategy 4: Try default keywords with exact and fuzzy matching
        for category_name, keywords in self.DEFAULT_KEYWORDS.items():
            # Exact match
            if any(keyword in text_to_match for keyword in keywords):
                category_id = self._category_cache.get(category_name.lower())
                if category_id:
                    return category_id
            
            # Fuzzy match (if enabled)
            if use_fuzzy:
                fuzzy_match = self._fuzzy_match(text_to_match, keywords, threshold=0.75)
                if fuzzy_match:
                    category_id = self._category_cache.get(category_name.lower())
                    if category_id:
                        return category_id
        
        return None
    
    def learn_from_categorization(self, merchant_name: str, category_id: int):
        """
        Learn from a user's manual categorization
        Updates the learned patterns for future auto-categorization
        """
        if not merchant_name:
            return
        
        merchant_key = merchant_name.lower().strip()
        if merchant_key not in self._learned_patterns:
            self._learned_patterns[merchant_key] = Counter()
        
        self._learned_patterns[merchant_key][category_id] += 1
    
    def get_suggested_category(self, description: str, merchant_name: Optional[str] = None) -> Optional[str]:
        """
        Get suggested category name (not ID) for an expense
        Useful for displaying suggestions to users
        """
        text_to_match = f"{description} {merchant_name or ''}".lower()
        
        # Try default keywords
        for category_name, keywords in self.DEFAULT_KEYWORDS.items():
            if any(keyword in text_to_match for keyword in keywords):
                return category_name
        
        return None
    
    def bulk_categorize(self, expenses: List[Dict]) -> List[Dict]:
        """
        Categorize multiple expenses at once
        Returns list of expenses with category_id added
        """
        for expense in expenses:
            if not expense.get('category_id'):
                category_id = self.categorize(
                    expense.get('description', ''),
                    expense.get('merchant_name')
                )
                if category_id:
                    expense['category_id'] = category_id
                    expense['is_categorized'] = True
        
        return expenses
    
    def create_default_categories(self, user_id: int) -> List[ExpenseCategory]:
        """
        Create default expense categories for a new user
        """
        default_categories = [
            {
                'name': 'Food & Dining',
                'description': 'Restaurants, food delivery, dining out',
                'keywords': ','.join(self.DEFAULT_KEYWORDS['Food & Dining']),
                'color': '#FF6B6B',
                'icon': '🍽️'
            },
            {
                'name': 'Groceries',
                'description': 'Supermarket, grocery shopping',
                'keywords': ','.join(self.DEFAULT_KEYWORDS['Groceries']),
                'color': '#4ECDC4',
                'icon': '🛒'
            },
            {
                'name': 'Transportation',
                'description': 'Fuel, cab, metro, parking',
                'keywords': ','.join(self.DEFAULT_KEYWORDS['Transportation']),
                'color': '#45B7D1',
                'icon': '🚗'
            },
            {
                'name': 'Shopping',
                'description': 'Online shopping, retail stores',
                'keywords': ','.join(self.DEFAULT_KEYWORDS['Shopping']),
                'color': '#96CEB4',
                'icon': '🛍️'
            },
            {
                'name': 'Entertainment',
                'description': 'Movies, streaming, games',
                'keywords': ','.join(self.DEFAULT_KEYWORDS['Entertainment']),
                'color': '#FFEAA7',
                'icon': '🎬'
            },
            {
                'name': 'Utilities',
                'description': 'Electricity, water, internet, mobile',
                'keywords': ','.join(self.DEFAULT_KEYWORDS['Utilities']),
                'color': '#DFE6E9',
                'icon': '💡'
            },
            {
                'name': 'Healthcare',
                'description': 'Medical, pharmacy, insurance',
                'keywords': ','.join(self.DEFAULT_KEYWORDS['Healthcare']),
                'color': '#74B9FF',
                'icon': '🏥'
            },
            {
                'name': 'Education',
                'description': 'School, courses, books',
                'keywords': ','.join(self.DEFAULT_KEYWORDS['Education']),
                'color': '#A29BFE',
                'icon': '📚'
            },
            {
                'name': 'Travel',
                'description': 'Flights, hotels, vacation',
                'keywords': ','.join(self.DEFAULT_KEYWORDS['Travel']),
                'color': '#FD79A8',
                'icon': '✈️'
            },
            {
                'name': 'Insurance',
                'description': 'Life, health, vehicle insurance',
                'keywords': ','.join(self.DEFAULT_KEYWORDS['Insurance']),
                'color': '#636E72',
                'icon': '🛡️'
            },
            {
                'name': 'Investment',
                'description': 'Mutual funds, stocks, SIP',
                'keywords': ','.join(self.DEFAULT_KEYWORDS['Investment']),
                'color': '#00B894',
                'icon': '📈'
            },
            {
                'name': 'Rent',
                'description': 'House rent, maintenance',
                'keywords': ','.join(self.DEFAULT_KEYWORDS['Rent']),
                'color': '#FDCB6E',
                'icon': '🏠'
            },
            {
                'name': 'Personal Care',
                'description': 'Salon, spa, grooming',
                'keywords': ','.join(self.DEFAULT_KEYWORDS['Personal Care']),
                'color': '#E17055',
                'icon': '💇'
            },
            {
                'name': 'Gifts & Donations',
                'description': 'Gifts, charity, donations',
                'keywords': ','.join(self.DEFAULT_KEYWORDS['Gifts & Donations']),
                'color': '#F8A5C2',
                'icon': '🎁'
            },
            {
                'name': 'Fees & Charges',
                'description': 'Bank fees, penalties, taxes',
                'keywords': ','.join(self.DEFAULT_KEYWORDS['Fees & Charges']),
                'color': '#B2BEC3',
                'icon': '💳'
            },
            {
                'name': 'ATM Withdrawal',
                'description': 'Cash withdrawals',
                'keywords': ','.join(self.DEFAULT_KEYWORDS['ATM Withdrawal']),
                'color': '#2D3436',
                'icon': '🏧'
            },
            {
                'name': 'Transfer',
                'description': 'Money transfers, NEFT, IMPS',
                'keywords': ','.join(self.DEFAULT_KEYWORDS['Transfer']),
                'color': '#6C5CE7',
                'icon': '💸'
            },
            {
                'name': 'Salary',
                'description': 'Salary income',
                'keywords': ','.join(self.DEFAULT_KEYWORDS['Salary']),
                'color': '#00B894',
                'icon': '💰',
                'is_income': True
            },
            {
                'name': 'Refund',
                'description': 'Refunds, cashback, rewards',
                'keywords': ','.join(self.DEFAULT_KEYWORDS['Refund']),
                'color': '#55EFC4',
                'icon': '↩️',
                'is_income': True
            },
            {
                'name': 'Other Income',
                'description': 'Other income sources',
                'keywords': 'income,credit,received',
                'color': '#81ECEC',
                'icon': '💵',
                'is_income': True
            },
            {
                'name': 'Other Expenses',
                'description': 'Miscellaneous expenses',
                'keywords': 'other,misc,miscellaneous',
                'color': '#B2BEC3',
                'icon': '📦'
            }
        ]
        
        created_categories = []
        for cat_data in default_categories:
            # Check if category already exists
            existing = self.db.query(ExpenseCategory).filter(
                ExpenseCategory.user_id == user_id,
                ExpenseCategory.name == cat_data['name']
            ).first()
            
            if not existing:
                category = ExpenseCategory(
                    user_id=user_id,
                    name=cat_data['name'],
                    description=cat_data.get('description'),
                    keywords=cat_data.get('keywords'),
                    color=cat_data.get('color'),
                    icon=cat_data.get('icon'),
                    is_system=True,
                    is_active=True
                )
                self.db.add(category)
                created_categories.append(category)
        
        self.db.commit()
        
        # Reload cache
        self._load_categories()
        
        return created_categories

# Made with Bob