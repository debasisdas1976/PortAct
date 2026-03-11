"""
Expense Auto-Categorization Service
Automatically categorizes expenses based on merchant names and keywords
Includes fuzzy matching and learning from user corrections
"""
from typing import Optional, Dict, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.expense_category import ExpenseCategory
from app.models.expense import Expense
import difflib
import re
from collections import Counter


class ExpenseCategorizer:
    """Service to auto-categorize expenses based on keywords"""
    
    # Fallback keywords — keys MUST match seed_data.json category names exactly
    # so that _category_cache lookups succeed.  The canonical source of truth
    # for system categories is seed_data.json (synced to DB at startup).
    DEFAULT_KEYWORDS = {
        'Dining & Restaurants': [
            'swiggy', 'zomato', 'uber eats', 'dunzo', 'shadowfax', 'bundl technologies',
            'eatsure', 'box8', 'faasos', 'behrouz', 'oven story', 'magicpin',
            'dominos', 'pizza hut', 'kfc', 'mcdonald', 'burger king', 'subway',
            'starbucks', 'cafe coffee day', 'ccd', 'barista', 'costa coffee',
            'haldiram', 'bikanervala', 'sagar ratna', 'saravana bhavan',
            'paradise biryani', 'behrouz biryani', 'charcoal biryani',
            'taco bell', 'wow momo', 'chaayos', 'chai point', 'third wave coffee',
            'mtr', 'vidyarthi bhavan', 'mavalli tiffin room', 'brahmins coffee bar',
            'by 2 coffee', 'hole in the wall', 'toit', 'truffles', 'meghana foods',
            'empire', 'nandhini', 'udupi', 'darshini', 'veena stores',
            'airlines hotel', 'koshy', 'indian coffee house', 'corner house',
            'a2b', 'adyar ananda bhavan', 'shanti sagar', 'sukh sagar',
            'sangeetha', 'vasanta bhavan', 'junior kuppanna',
            'nagarjuna', 'rajdhani', 'mainland china',
            'bikano', 'chitale', 'gwalia', 'aggarwal', 'annapurna',
            'restaurant', 'cafe', 'coffee', 'food', 'dining', 'eatery',
            'meal', 'breakfast', 'lunch', 'dinner', 'bakery', 'sweet shop',
            'dhaba', 'tiffin', 'canteen', 'mess', 'biryani', 'thali',
            'dosa', 'idli', 'paratha'
        ],
        'Groceries': [
            'bigbasket', 'grofers', 'blinkit', 'zepto', 'dunzo', 'jiomart',
            'amazon fresh', 'amazon pantry', 'instamart', 'swiggy instamart',
            'milkbasket', 'supr daily', 'licious', 'freshtohome', 'meatigo',
            'country delight', 'ninjacart',
            'dmart', 'reliance fresh', 'reliance smart', 'more', 'spencer', 'star bazaar',
            'hypercity', 'big bazaar', 'easyday', 'nilgiris', '24 seven',
            'spar', 'nature basket', 'foodhall', 'le marche',
            'namdhari', 'namdhari fresh', 'hopcoms', 'namma basket',
            'total mall', 'ratnadeep', 'star market',
            'kirana', 'provision', 'general store', 'departmental store',
            'grocery', 'supermarket', 'vegetables', 'fruits', 'milk', 'bread',
            'food items', 'household', 'provisions', 'ration', 'sabzi', 'mandi'
        ],
        'Transportation': [
            'uber', 'ola', 'rapido', 'blu smart', 'meru', 'taxi',
            'namma yatri', 'auto', 'indriver',
            'indian oil', 'iocl', 'bharat petroleum', 'bpcl', 'hp petrol', 'hpcl',
            'shell', 'essar', 'reliance petrol',
            'petrol', 'diesel', 'fuel', 'cng', 'gas station', 'petrol pump', 'fuel station',
            'bmtc', 'namma metro', 'bangalore metro', 'bmrcl', 'purple line', 'green line',
            'metro', 'dmrc', 'best', 'bus', 'train', 'railway', 'local train',
            'mumbai metro', 'chennai metro', 'hyderabad metro', 'kolkata metro',
            'parking', 'toll', 'fastag', 'paytm fastag', 'netc fastag',
            'park plus', 'park+',
            'car wash', 'servicing', 'car service', 'bike service',
            'tyre', 'battery', 'mechanic', 'garage',
            'transport', 'cab', 'rickshaw', 'vehicle', 'commute'
        ],
        'Shopping & Clothing': [
            'amazon', 'amazonin', 'amzn', 'flipkart', 'myntra', 'ajio', 'meesho',
            'snapdeal', 'shopclues', 'tata cliq', 'nykaa', 'purplle',
            'jiomart', 'firstcry', 'lenskart', 'mamaearth', 'boat',
            'zara', 'h&m', 'max fashion', 'pantaloons', 'westside',
            'lifestyle', 'shoppers stop', 'central', 'reliance trends',
            'uniqlo', 'marks and spencer', 'mango', 'allen solly', 'peter england',
            'van heusen', 'louis philippe', 'raymond', 'arvind',
            'croma', 'reliance digital', 'vijay sales', 'poorvika',
            'sangeetha mobiles', 'lot mobiles', 'samsung store', 'apple store',
            'ikea', 'pepperfry', 'urban ladder', 'hometown', 'fabindia',
            'wakefit', 'sleepwell', 'duroflex', 'godrej interio',
            'orion mall', 'phoenix marketcity', 'forum mall', 'mantri mall',
            'garuda mall', 'royal meenakshi mall', 'vr bengaluru',
            'commercial street', 'brigade road', 'chickpet', 'avenue road',
            'jayanagar shopping', 'malleswaram shopping',
            'shopping', 'mall', 'store', 'retail', 'fashion', 'clothing',
            'shoes', 'electronics', 'mobile', 'laptop', 'accessories',
            'jewellery', 'tanishq', 'kalyan', 'malabar gold', 'joyalukkas'
        ],
        'Entertainment': [
            'netflix', 'amazon prime', 'prime video', 'hotstar', 'disney',
            'zee5', 'sony liv', 'voot', 'alt balaji', 'mx player',
            'spotify', 'youtube premium', 'gaana', 'jio saavn', 'wynk',
            'apple music', 'audible', 'kindle unlimited',
            'jio cinema', 'fancode', 'lionsgate',
            'pvr', 'inox', 'pvr inox', 'cinepolis', 'carnival', 'movie', 'cinema',
            'theatre', 'multiplex', 'bookmyshow', 'paytm movies',
            'innovative multiplex', 'gopalan cinemas', 'fun cinemas',
            'cubbon park', 'lalbagh', 'bannerghatta', 'wonderla',
            'nandi hills', 'innovative film city',
            'imagica', 'essel world', 'kingdom of dreams',
            'comic con', 'sunburn', 'nh7 weekender',
            'steam', 'playstation', 'xbox', 'nintendo', 'gaming',
            'epic games', 'riot games',
            'entertainment', 'subscription', 'ott', 'streaming',
            'concert', 'event', 'show', 'performance', 'ticket'
        ],
        'Utilities': [
            'airtel', 'jio', 'vodafone', 'vi', 'bsnl', 'mtnl',
            'mobile recharge', 'prepaid', 'postpaid', 'phone bill',
            'broadband', 'wifi', 'internet', 'fiber', 'act fibernet',
            'tata sky', 'dish tv', 'sun direct', 'dth', 'cable',
            'hathway', 'you broadband', 'excitel', 'tikona',
            'bescom', 'bwssb', 'bangalore water', 'bbmp',
            'kaveri', 'cauvery water',
            'electricity', 'power', 'msedcl', 'tata power', 'adani electricity',
            'torrent power', 'cesc',
            'water', 'water bill', 'gas', 'lpg', 'indane', 'bharat gas', 'hp gas',
            'piped gas', 'png', 'mahanagar gas', 'adani gas', 'gail gas',
            'bill payment', 'bbps', 'billdesk', 'utility', 'paytm bill',
            'cred bill', 'phonepe bill'
        ],
        'Healthcare & Medical': [
            'apollo', 'fortis', 'max', 'medanta', 'manipal', 'narayana',
            'hospital', 'clinic', 'doctor', 'medical', 'health',
            'aster', 'columbia asia', 'sakra', 'sparsh',
            'narayana hrudayalaya', 'manipal hospital', 'st johns', 'nimhans',
            'kidwai', 'victoria hospital', 'jayadeva', 'sagar hospital',
            'bangalore hospital', 'bgs global', 'ramaiah',
            'apollo pharmacy', 'medplus', 'netmeds', '1mg', 'pharmeasy',
            'pharmacy', 'medicine', 'chemist', 'drug store',
            'truemeds', 'wellness forever', 'frank ross',
            'thyrocare', 'dr lal pathlabs', 'metropolis', 'lab test',
            'diagnostic', 'pathology', 'x-ray', 'scan',
            'srl diagnostics', 'neuberg', 'orange health', 'redcliffe',
            'dental', 'dentist', 'clove dental', 'sabka dentist',
            'eye care', 'ophthalmologist', 'titan eye',
            'ayurveda', 'patanjali', 'himalaya', 'dabur',
            'ayurvedic', 'homeopathy', 'siddha'
        ],
        'Education': [
            'school', 'college', 'university', 'institute', 'academy',
            'tuition', 'coaching', 'classes',
            'iisc', 'iim bangalore', 'nls', 'christ university', 'jain university',
            'pes university', 'reva', 'nitte', 'dayananda sagar', 'bms college',
            'rv college', 'sir mvit',
            'udemy', 'coursera', 'byju', 'unacademy', 'vedantu',
            'toppr', 'white hat jr', 'upgrad', 'simplilearn',
            'skill share', 'linkedin learning', 'scaler', 'coding ninjas',
            'great learning', 'intellipaat', 'edureka', 'pluralsight',
            'allen', 'fiitjee', 'aakash', 'resonance', 'bansal',
            'ims', 'time institute', 'career launcher', 'test series',
            'amazon books', 'flipkart books', 'crossword', 'landmark',
            'books', 'stationery', 'notebook', 'pen',
            'sapna book house', 'gangaram', 'blossoms',
            'education', 'learning', 'course', 'training', 'exam fee',
            'certification', 'workshop', 'seminar', 'webinar'
        ],
        'Fitness & Gym': [
            'cult fit', 'cure fit', 'healthifyme', 'fitness', 'gym', 'yoga',
            'gold gym', 'anytime fitness', 'talwalkar', 'snap fitness',
            'workout', 'exercise', 'trainer', 'sports', 'health club',
            'crossfit', 'pilates', 'zumba'
        ],
        'Travel & Vacation': [
            'indigo', 'spicejet', 'air india', 'vistara', 'go air',
            'air asia', 'akasa air', 'flight', 'airline', 'airways',
            'star air', 'alliance air',
            'oyo', 'treebo', 'fab hotels', 'airbnb', 'booking.com',
            'makemytrip', 'goibibo', 'cleartrip', 'yatra', 'ixigo',
            'hotel', 'resort', 'accommodation', 'stay',
            'taj hotels', 'itc hotels', 'oberoi', 'lemon tree', 'ginger hotel',
            'zostel', 'hostel', 'homestay',
            'irctc', 'train', 'railway', 'redbus', 'abhibus', 'bus booking',
            'confirmtkt', 'railyatri', 'trainman',
            'kempegowda airport', 'blr airport', 'kia', 'bial',
            'ksrtc', 'bmtc volvo', 'shivajinagar bus', 'majestic bus',
            'mysore road', 'coorg', 'ooty', 'wayanad', 'chikmagalur',
            'travel', 'vacation', 'holiday', 'tour', 'trip',
            'visa', 'passport', 'forex', 'travel insurance', 'luggage'
        ],
        'Insurance': [
            'insurance', 'premium', 'policy', 'lic', 'hdfc life',
            'icici prudential', 'sbi life', 'max life', 'bajaj allianz',
            'tata aia', 'kotak life', 'birla sun life', 'aegon life',
            'star health', 'care health', 'acko', 'digit insurance',
            'vehicle insurance', 'car insurance', 'bike insurance',
            'niva bupa', 'manipal cigna', 'aditya birla health',
            'hdfc ergo', 'icici lombard', 'bajaj finserv', 'new india assurance',
            'united india insurance', 'national insurance',
            'term plan', 'endowment', 'ulip', 'term insurance'
        ],
        'Investments & Returns': [
            'zerodha', 'groww', 'upstox', 'angel one', 'paytm money',
            '5paisa', 'iifl', 'motilal oswal', 'sharekhan',
            'kite', 'coin by zerodha', 'dhan', 'fi money', 'ind money',
            'mutual fund', 'mf', 'sip', 'systematic investment',
            'amc', 'hdfc mf', 'icici mf', 'sbi mf',
            'nippon mf', 'axis mf', 'kotak mf', 'dsp mf', 'mirae asset',
            'ppfas', 'quant mf', 'parag parikh',
            'ppf', 'nsc', 'kvp', 'fixed deposit', 'fd', 'recurring deposit', 'rd',
            'post office', 'sukanya samriddhi', 'ssy',
            'bonds', 'sgb', 'sovereign gold bond', 'nps', 'atal pension',
            'stock', 'share', 'equity', 'investment', 'trading',
            'demat', 'portfolio', 'fund', 'dividend', 'ipo'
        ],
        'Rent & Mortgage': [
            'rent', 'lease', 'housing', 'apartment', 'flat',
            'maintenance', 'society', 'housing society', 'pg',
            'paying guest', 'accommodation', 'landlord',
            'cred rent', 'nobroker', 'magicbricks', 'housing.com',
            '99acres', 'nestaway', 'colive', 'zolo',
            'security deposit', 'brokerage', 'rental agreement',
            'mortgage', 'emi', 'home loan'
        ],
        'Personal Care': [
            'salon', 'spa', 'lakme', 'jawed habib', 'naturals',
            'green trends', 'toni and guy', 'looks salon',
            'urban company', 'urbanclap',
            'bounce salon', 'bodycraft', 'studio11',
            'beauty', 'grooming', 'haircut', 'parlour', 'facial',
            'manicure', 'pedicure', 'waxing', 'massage',
            'nykaa', 'purplle', 'mcaffeine', 'mamaearth', 'wow',
            'cosmetics', 'skincare', 'makeup', 'personal care',
            'bath and body works', 'the body shop', 'forest essentials',
            'plum', 'sugar cosmetics', 'myglamm', 'beardo', 'bombay shaving'
        ],
        'Subscriptions': [
            'subscription', 'membership', 'monthly', 'recurring',
            'netflix', 'spotify', 'amazon prime', 'youtube premium',
            'apple one', 'icloud', 'google one', 'microsoft 365',
            'adobe', 'notion', 'chatgpt', 'claude', 'cred', 'premium'
        ],
        'Gifts & Donations': [
            'gift', 'donation', 'charity', 'ngo', 'temple',
            'church', 'mosque', 'gurudwara', 'religious',
            'contribution', 'offering', 'dakshina', 'prasad',
            'ketto', 'milaap', 'give india', 'donatekart',
            'tirupati', 'iskcon', 'shirdi', 'vaishno devi'
        ],
        'Pet Care': [
            'pet', 'dog', 'cat', 'vet', 'veterinary',
            'pet food', 'pet supplies', 'supertails',
            'heads up for tails', 'petsy', 'mars petcare'
        ],
        'Home Maintenance': [
            'repair', 'maintenance', 'plumber', 'electrician', 'cleaning',
            'handyman', 'home improvement', 'urban company', 'urbanclap',
            'housejoy', 'carpenter', 'painter', 'pest control',
            'water purifier', 'ac service', 'appliance repair'
        ],
        'Fees & Charges': [
            'fee', 'charge', 'penalty', 'fine', 'late fee',
            'processing fee', 'service charge',
            'annual fee', 'membership fee', 'registration',
            'emi processing', 'foreclosure charge', 'bounce charge',
            'convenience fee', 'platform fee', 'delivery charge'
        ],
        'Taxes': [
            'tax', 'income tax', 'property tax', 'tds', 'gst',
            'advance tax', 'stamp duty', 'cess',
            'self assessment tax', 'challan', 'professional tax', 'municipal tax'
        ],
        'ATM Withdrawal': [
            'atm', 'cash withdrawal', 'withdrawal', 'cash',
            'atm cash', 'self withdrawal', 'cash deposit machine', 'cdm'
        ],
        'Transfer': [
            'transfer', 'neft', 'imps', 'rtgs', 'upi transfer',
            'fund transfer', 'money transfer', 'payment to',
            'sent to', 'transferred to',
            'upi', 'paytm', 'phonepe', 'gpay', 'google pay',
            'bhim', 'mobikwik', 'freecharge', 'amazon pay'
        ],
        'Salary & Income': [
            'salary', 'wages', 'income', 'payment received',
            'credit salary', 'sal credit', 'payroll', 'stipend',
            'bonus', 'incentive', 'commission', 'honorarium',
            'freelance', 'consulting fee', 'professional fee'
        ],
        'Refund': [
            'refund', 'reversal', 'cashback', 'reward',
            'credit adjustment', 'return', 'cancelled',
            'refunded', 'reversed',
            'chargeback', 'dispute', 'claim settled'
        ],
        'Domestic Help': [
            'maid', 'driver', 'laundry', 'car wash', 'nanny', 'snabbit',
            'housekeeper', 'cook', 'domestic help', 'house help', 'bai',
            'dhobi', 'ironing', 'pressing', 'dry cleaning', 'washerman',
            'gardener', 'watchman', 'security guard', 'ayah', 'caretaker',
            'babysitter', 'cleaner', 'sweeper', 'household staff'
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
        """Load categories from database into cache (only current user's + system categories)"""
        query = self.db.query(ExpenseCategory).filter(
            ExpenseCategory.is_active == True
        )
        if self.user_id:
            query = query.filter(
                or_(
                    ExpenseCategory.user_id == self.user_id,
                    ExpenseCategory.is_system == True
                )
            )
        categories = query.all()
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
        Perform fuzzy matching on text against keywords.
        Compares keyword against individual words/windows in the text
        (not the entire text string) so length differences don't kill the ratio.
        Returns the best matching keyword if similarity >= threshold.
        """
        text_lower = text.lower()
        text_words = text_lower.split()
        best_match = None
        best_ratio = 0.0

        for keyword in keywords:
            keyword_lower = keyword.lower()

            # First try exact substring match (fastest)
            if keyword_lower in text_lower:
                return keyword

            keyword_words = keyword_lower.split()

            if len(keyword_words) <= 1:
                # Single-word keyword: compare against each word in text
                for word in text_words:
                    ratio = difflib.SequenceMatcher(None, word, keyword_lower).ratio()
                    if ratio > best_ratio and ratio >= threshold:
                        best_ratio = ratio
                        best_match = keyword
            else:
                # Multi-word keyword: sliding window of same word count
                window_size = len(keyword_words)
                for i in range(max(1, len(text_words) - window_size + 1)):
                    window = ' '.join(text_words[i:i + window_size])
                    ratio = difflib.SequenceMatcher(None, window, keyword_lower).ratio()
                    if ratio > best_ratio and ratio >= threshold:
                        best_ratio = ratio
                        best_match = keyword

                # Also check if all keyword words appear in text (even non-adjacent)
                words_found = sum(1 for w in keyword_words if w in text_lower)
                word_ratio = words_found / len(keyword_words)
                if word_ratio > best_ratio and word_ratio >= threshold:
                    best_ratio = word_ratio
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
    
    @staticmethod
    def _keyword_matches(keyword: str, text: str) -> bool:
        """
        Check if keyword matches in text using word-boundary matching.
        Multi-word keywords use substring match (they're specific enough).
        Single-word keywords use word-boundary regex to avoid false positives
        (e.g. 'more' should NOT match inside 'anymore').
        """
        keyword = keyword.strip()
        if not keyword:
            return False
        if ' ' in keyword:
            # Multi-word keyword: substring match is fine (specific enough)
            return keyword in text
        # Single-word keyword: require word boundaries
        return bool(re.search(r'\b' + re.escape(keyword) + r'\b', text))

    def _find_best_keyword_match(self, text_to_match: str, categories, use_fuzzy: bool = True) -> Optional[int]:
        """
        Score all categories against the text and return the best match.
        Scoring: longer keyword matches score higher, so specific matches beat generic ones.
        Multi-word keyword matches get a bonus.
        """
        best_category_id = None
        best_score = 0

        for category in categories:
            if not category.keywords:
                continue
            keywords = [k.strip().lower() for k in category.keywords.split(',')]
            cat_score = 0
            for keyword in keywords:
                if not keyword:
                    continue
                if self._keyword_matches(keyword, text_to_match):
                    # Score by keyword length; multi-word keywords get a bonus
                    score = len(keyword)
                    if ' ' in keyword:
                        score += 10  # bonus for multi-word (more specific)
                    if score > cat_score:
                        cat_score = score
            if cat_score > best_score:
                best_score = cat_score
                best_category_id = category.id

        # If no exact match found, try fuzzy matching
        if not best_category_id and use_fuzzy:
            for category in categories:
                if not category.keywords:
                    continue
                keywords = [k.strip() for k in category.keywords.split(',')]
                fuzzy_match = self._fuzzy_match(text_to_match, keywords, threshold=0.75)
                if fuzzy_match:
                    return category.id

        return best_category_id

    def categorize(self, description: str, merchant_name: Optional[str] = None, use_fuzzy: bool = True) -> Optional[int]:
        """
        Categorize an expense based on description and merchant name
        Uses multiple strategies in order of priority:
        1. Learned patterns from user's past categorizations
        2. Best keyword match from database categories (scored by specificity)
        3. Best keyword match from default keywords (scored by specificity)
        4. Fuzzy keyword matching as fallback

        Returns category_id if found, None otherwise
        """
        # Strategy 1: Check learned patterns first (highest priority)
        if merchant_name:
            learned_category = self._get_learned_category(merchant_name)
            if learned_category:
                return learned_category

        # Combine description and merchant name for matching
        text_to_match = f"{description} {merchant_name or ''}".lower()

        # Strategy 2: Score-based matching with database categories (user's + system, active only)
        cat_query = self.db.query(ExpenseCategory).filter(
            ExpenseCategory.keywords.isnot(None),
            ExpenseCategory.is_active == True
        )
        if self.user_id:
            cat_query = cat_query.filter(
                or_(
                    ExpenseCategory.user_id == self.user_id,
                    ExpenseCategory.is_system == True
                )
            )
        # User-defined categories first so they take priority over system ones
        categories = cat_query.order_by(
            ExpenseCategory.is_system.asc()
        ).all()

        # Check user-defined categories first (non-system) with first-match priority
        user_categories = [c for c in categories if not c.is_system]
        if user_categories:
            result = self._find_best_keyword_match(text_to_match, user_categories, use_fuzzy=False)
            if result:
                return result

        # Score-based matching across all system categories — best match wins
        system_categories = [c for c in categories if c.is_system]
        result = self._find_best_keyword_match(text_to_match, system_categories, use_fuzzy=use_fuzzy)
        if result:
            return result

        # Strategy 3: Try default keywords with score-based matching
        # Build pseudo-category objects for scoring
        class _PseudoCategory:
            def __init__(self, cat_id, keywords_str):
                self.id = cat_id
                self.keywords = keywords_str
                self.is_system = True

        default_cats = []
        for category_name, keywords in self.DEFAULT_KEYWORDS.items():
            category_id = self._category_cache.get(category_name.lower())
            if category_id:
                default_cats.append(_PseudoCategory(category_id, ','.join(keywords)))

        if default_cats:
            result = self._find_best_keyword_match(text_to_match, default_cats, use_fuzzy=use_fuzzy)
            if result:
                return result

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

        # Score-based matching across default keywords
        best_name = None
        best_score = 0
        for category_name, keywords in self.DEFAULT_KEYWORDS.items():
            for keyword in keywords:
                if self._keyword_matches(keyword, text_to_match):
                    score = len(keyword) + (10 if ' ' in keyword else 0)
                    if score > best_score:
                        best_score = score
                        best_name = category_name

        return best_name
    
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
    

# Made with Bob