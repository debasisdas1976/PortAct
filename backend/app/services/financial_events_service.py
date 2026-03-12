"""
Financial Events Service — provides:
1. Upcoming financial calendar events (India + Global), dynamically filtered to future dates.
2. Top global financial news from curated RSS feeds (Reuters, CNBC, MarketWatch, etc.)
   with relevance scoring and category detection — no API key required.
"""

from calendar import timegm
from datetime import date, datetime, timedelta, timezone
from html import unescape
from typing import List, Dict, Any, Tuple
import asyncio
import feedparser
import httpx
import logging
import re
import threading

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(10.0, connect=5.0)
_RSS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}

# ── Curated RSS feed sources ──────────────────────────────────────────────────
# Global feeds — macro/market/sector level news
_GLOBAL_NEWS_FEEDS: List[Dict[str, str]] = [
    {"name": "Reuters",          "url": "https://feeds.reuters.com/reuters/businessNews"},
    {"name": "Reuters Markets",  "url": "https://feeds.reuters.com/reuters/marketsNews"},
    {"name": "CNBC",             "url": "https://search.cnbc.com/rs/search/combinedcombined/view/rss.html?tag=topnews"},
    {"name": "MarketWatch",      "url": "https://feeds.content.dowjones.io/public/rss/mw_topstories"},
    {"name": "Yahoo Finance",    "url": "https://finance.yahoo.com/rss/topstories"},
    {"name": "Investing.com",    "url": "https://www.investing.com/rss/news.rss"},
]

# India-specific feeds — ET, LiveMint, MoneyControl
_INDIA_NEWS_FEEDS: List[Dict[str, str]] = [
    {"name": "Economic Times",   "url": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"},
    {"name": "LiveMint",         "url": "https://www.livemint.com/rss/markets"},
    {"name": "MoneyControl",     "url": "https://www.moneycontrol.com/rss/marketreports.xml"},
]

# Minimum guaranteed India articles in the final result
_MIN_INDIA_NEWS = 4

# ── Relevance: category keyword sets ─────────────────────────────────────────
_CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "central_bank":  ["fed", "fomc", "federal reserve", "ecb", "rbi", "bank of england",
                      "rate cut", "rate hike", "interest rate", "monetary policy",
                      "repo rate", "yield curve", "quantitative easing", "taper"],
    "markets":       ["stock", "equity", "nasdaq", "s&p 500", "s&p500", "nifty", "sensex",
                      "dow jones", "rally", "correction", "bull market", "bear market",
                      "wall street", "nse", "bse", "ftse", "dax", "nikkei"],
    "economy":       ["gdp", "inflation", "cpi", "unemployment", "recession",
                      "economic growth", "fiscal deficit", "trade balance", "current account",
                      "pmi", "non-farm payroll", "nfp", "jobs report"],
    "commodities":   ["gold", "silver", "oil", "crude", "brent", "wti", "copper",
                      "natural gas", "commodity", "metal", "platinum", "palladium"],
    "crypto":        ["bitcoin", "ethereum", "crypto", "blockchain", "defi",
                      "stablecoin", "binance", "coinbase", "btc", "eth"],
    "corporate":     ["earnings", "revenue", "profit", "loss", "merger", "acquisition",
                      "ipo", "dividend", "buyback", "quarterly results", "guidance"],
    "india":         ["india", "indian", "rupee", "sebi", "rbi", "sensex", "nifty",
                      "union budget", "modi", "nse", "bse", "fii", "dii"],
    "policy":        ["tariff", "trade war", "sanction", "regulation", "g7", "g20",
                      "imf", "world bank", "wto", "trade deal", "fiscal policy"],
}

# Articles mentioning these terms are likely not financial news
_IRRELEVANT_TERMS = frozenset([
    "nfl", "nba", "nhl", "mlb", "soccer", "cricket score", "celebrity",
    "oscar", "grammy", "recipe", "movie review", "gaming", "esports",
    "box office", "album", "fashion week",
])

# Signals that an article is about a specific company's stock/earnings performance.
# Uses both past and present tense to catch headline variations.
_INDIVIDUAL_STOCK_SIGNALS = frozenset([
    # Earnings / results
    "quarterly earnings", "quarterly results", "quarterly profit", "quarterly revenue",
    "q1 earnings", "q2 earnings", "q3 earnings", "q4 earnings",
    "q1 results", "q2 results", "q3 results", "q4 results",
    "annual results", "full-year results", "full year results",
    "earnings beat", "earnings miss", "eps beat", "eps miss",
    # Revenue
    "revenue beats", "revenue misses", "revenue fell", "revenue falls",
    "revenue rose", "revenue rises", "revenue jumps", "revenue surges",
    "revenue slumps", "revenue declines",
    # Profit / net income
    "profit beats", "profit misses",
    "profit fell", "profit falls", "profit rose", "profit rises",
    "profit jumps", "profit surges", "profit soars", "profit climbs",
    "profit slumps", "profit declines", "profit drops",
    "net income fell", "net income falls", "net income rose", "net income rises",
    # Share price movements
    "shares jumped", "shares surged", "shares fell", "shares falls",
    "shares dropped", "shares drops", "shares rose", "shares rises",
    "shares gained", "shares gains", "shares plunged", "shares rallied",
    "shares slide", "shares slump", "shares soar", "shares tumble",
    "shares climb", "shares rally",
    # Stock price movements
    "stock jumped", "stock surged", "stock fell", "stock falls",
    "stock dropped", "stock drops", "stock rose", "stock rises",
    "stock gained", "stock gains", "stock plunged", "stock rallied",
    "stock slides", "stock soars", "stock tumbles", "stock climbs",
    "stock slips", "stock tanks", "stock rallies", "stock bounces",
    "stock surge", "stock plunge", "stock drop",
    # Corporate actions
    "announces dividend", "declares dividend", "announces buyback",
    "buy back", "ipo filing", "goes public",
    "raises guidance", "cuts guidance", "lowers guidance", "withdraws guidance",
    "surprise profit", "surprise loss", "surprise earnings",
])

# Well-known foreign (non-India) company names — individual stock/corporate news
# about these will be filtered out; only macro/market-wide stories are kept.
_FOREIGN_LARGE_CAPS = frozenset([
    # US tech
    "apple", "microsoft", "google", "alphabet", "amazon", "meta", "tesla",
    "nvidia", "netflix", "uber", "airbnb", "palantir", "salesforce", "oracle",
    "intel", "amd", "qualcomm", "broadcom", "cisco", "ibm", "dell", "hp",
    "snapchat", "snap inc", "twitter", "x corp", "spotify", "dropbox",
    "workday", "servicenow", "autodesk", "adobe", "zoom", "crowdstrike",
    # US finance
    "jpmorgan", "jp morgan", "goldman sachs", "morgan stanley", "citigroup",
    "bank of america", "wells fargo", "blackrock", "berkshire hathaway",
    "american express", "visa inc", "mastercard", "charles schwab",
    "fidelity", "vanguard",
    # US retail / consumer
    "walmart", "target", "costco", "home depot", "lowe's", "macy's",
    "nordstrom", "kroger", "dollar general", "dollar tree",
    # US industrials / energy / pharma
    "exxon", "chevron", "boeing", "johnson & johnson", "pfizer", "moderna",
    "merck", "abbvie", "eli lilly", "disney", "ford motor", "general motors",
    "starbucks", "mcdonald's", "nike", "caterpillar", "ge healthcare",
    "raytheon", "lockheed", "halliburton", "conocophillips",
    # European
    "volkswagen", "bmw", "mercedes-benz", "stellantis",
    "shell plc", "shell plc", "bp plc", "equinor",
    "hsbc", "barclays", "lloyds", "natwest", "standard chartered",
    "deutsche bank", "ubs", "credit suisse", "bnp paribas", "societe generale",
    "lvmh", "kering", "hermes", "nestle", "novartis", "roche", "astrazeneca",
    "glaxosmithkline", "gsk", "sanofi", "bayer",
    "sap se", "siemens", "asml", "asm international", "philips",
    "totalenergies", "airbus", "unilever", "diageo", "reckitt",
    "adecco", "randstad", "abb ltd", "bachem", "lonza", "givaudan",
    "richemont", "swatch", "zurich insurance", "swiss re",
    # Asian (non-India)
    "samsung", "toyota", "honda", "sony", "softbank", "panasonic", "sharp",
    "alibaba", "tencent", "baidu", "jd.com", "jd com", "byd", "xiaomi",
    "huawei", "bytedance", "tiktok", "nio", "li auto", "xpeng",
    "taiwan semiconductor", "tsmc", "sk hynix", "lg electronics",
    "hyundai", "kia", "posco", "kb financial", "shinhan",
    "mitsui", "mitsubishi", "sumitomo", "nomura", "mizuho",
    "rakuten", "ntt", "kddi", "sharp",
    # Latin America / other
    "rio tinto", "bhp group", "glencore", "vale sa", "petrobras",
    "itau", "bradesco", "banco brasil",
])

# India company/entity names — individual stock news about these is always kept
_INDIA_COMPANY_TERMS = frozenset([
    "india", "indian", "rupee", "rbi", "sebi", "nse", "bse", "sensex", "nifty",
    "reliance", "tata", "infosys", "wipro", "hdfc", "icici", "sbi", "kotak",
    "adani", "bajaj", "mahindra", "maruti", "itc", "hcl", "ril", "tcs",
    "l&t", "larsen", "ongc", "ntpc", "power grid", "bhel", "sail",
    "coal india", "gail", "axis bank", "yes bank", "indusind", "bandhan",
    "paytm", "zomato", "swiggy", "flipkart", "nykaa", "policybazaar",
    "tech mahindra", "sun pharma", "dr reddy", "cipla", "lupin", "divi",
    "ultratech", "jsw", "vedanta", "hindalco", "tata steel", "tata motors",
    "hero motocorp", "bajaj auto", "eicher motors", "m&m", "irfc", "irctc",
    "hindustan unilever", "hul", "nestle india", "britannia", "dabur",
    "godrej", "pidilite", "asian paints", "berger paints", "havells",
    "dixon technologies", "amber enterprises", "voltas",
])

# Company action verbs — if a foreign company name appears in the TITLE alongside
# these, the article is about that company specifically (not broad market news).
_COMPANY_ACTION_IN_TITLE = frozenset([
    "signs ", "launches ", "unveils ", "acquires ", "buys ", "sells ",
    "announces ", "reports ", "posts ", " stock ", " shares ",
    "profit", "revenue", "earnings", "results", "guidance", "dividend",
    "ipo", "buyback", "buy back", "merger", "acquisition", "deal",
])


# Pre-compile word-boundary patterns for short India acronyms (≤4 chars) to avoid
# false-positive substring matches like "nse" inside "license", "ril" inside "April"
_INDIA_SHORT_PATTERNS = [
    re.compile(r'(?<!\w)' + re.escape(t) + r'(?!\w)')
    for t in _INDIA_COMPANY_TERMS if len(t) <= 4
]
_INDIA_LONG_TERMS = frozenset(t for t in _INDIA_COMPANY_TERMS if len(t) > 4)


def _mentions_india(text: str) -> bool:
    """True if text mentions India or a known Indian company/entity."""
    return (
        any(t in text for t in _INDIA_LONG_TERMS) or
        any(p.search(text) for p in _INDIA_SHORT_PATTERNS)
    )


def _is_individual_foreign_stock(title: str, summary: str, category: str) -> bool:
    """
    Returns True if the article is about a specific foreign (non-India) company's
    stock / earnings / corporate news. Such articles are filtered out — we prefer
    macro/market-wide news and India-specific corporate news.
    """
    text = (title + " " + summary).lower()
    title_lower = title.lower()

    # If it mentions India or a known Indian company, always keep it
    if _mentions_india(text):
        return False

    in_foreign_caps = any(c in text for c in _FOREIGN_LARGE_CAPS)
    has_stock_signal = any(s in text for s in _INDIVIDUAL_STOCK_SIGNALS)

    # Corporate category + any stock signal → filter
    if category == "corporate" and has_stock_signal:
        return True

    # Foreign company appears in title + company action word in title → filter
    if in_foreign_caps:
        if any(a in title_lower for a in _COMPANY_ACTION_IN_TITLE):
            return True
        # Foreign company + stock movement signal anywhere in text
        if has_stock_signal:
            return True

    return False

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", unescape(_HTML_TAG_RE.sub("", text))).strip()


def _score_and_categorize(title: str, summary: str) -> Tuple[int, str]:
    """
    Score financial relevance and detect the primary category.
    Returns (score, category). Score < 0 means the article should be filtered out.
    """
    text = (title + " " + summary).lower()

    # Filter out clearly irrelevant content
    for term in _IRRELEVANT_TERMS:
        if term in text:
            return -1, "other"

    category_scores: Dict[str, int] = {}
    for category, keywords in _CATEGORY_KEYWORDS.items():
        hits = sum(2 for kw in keywords if kw in text)
        if hits:
            category_scores[category] = hits

    total_score = sum(category_scores.values())

    if not category_scores:
        # Not category-matched — check for general finance relevance
        general_terms = [
            "market", "economy", "finance", "invest", "bank", "fund",
            "asset", "capital", "currency", "dollar", "euro", "yen",
            "share", "profit", "loss", "bond", "debt", "growth",
        ]
        total_score = sum(1 for t in general_terms if t in text)
        return total_score, "markets"

    best_category = max(category_scores, key=lambda c: category_scores[c])
    return total_score, best_category


# ── Helpers ───────────────────────────────────────────────────────────────────

def _last_thursday(year: int, month: int) -> date:
    """Return the last Thursday of the given month (NSE/BSE F&O monthly expiry)."""
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)
    days_back = (last_day.weekday() - 3) % 7  # Thursday = weekday 3
    return last_day - timedelta(days=days_back)


def _first_friday(year: int, month: int) -> date:
    """Return the first Friday of the given month (approx US Non-Farm Payrolls)."""
    first = date(year, month, 1)
    days_ahead = (4 - first.weekday()) % 7  # Friday = weekday 4
    return first + timedelta(days=days_ahead)


# ── Static Calendar ───────────────────────────────────────────────────────────

_STATIC_EVENTS: List[Dict[str, Any]] = [
    # ── RBI MPC Meetings 2026 ─────────────────────────────────────────────
    {"title": "RBI MPC Meeting", "subtitle": "Apr 7–9, 2026",  "date": "2026-04-07", "category": "central_bank", "region": "IN", "flag": "🇮🇳", "description": "RBI Monetary Policy Committee — interest rate decision", "importance": "high"},
    {"title": "RBI MPC Meeting", "subtitle": "Jun 4–6, 2026",  "date": "2026-06-04", "category": "central_bank", "region": "IN", "flag": "🇮🇳", "description": "RBI Monetary Policy Committee — interest rate decision", "importance": "high"},
    {"title": "RBI MPC Meeting", "subtitle": "Aug 4–6, 2026",  "date": "2026-08-04", "category": "central_bank", "region": "IN", "flag": "🇮🇳", "description": "RBI Monetary Policy Committee — interest rate decision", "importance": "high"},
    {"title": "RBI MPC Meeting", "subtitle": "Oct 6–8, 2026",  "date": "2026-10-06", "category": "central_bank", "region": "IN", "flag": "🇮🇳", "description": "RBI Monetary Policy Committee — interest rate decision", "importance": "high"},
    {"title": "RBI MPC Meeting", "subtitle": "Dec 3–5, 2026",  "date": "2026-12-03", "category": "central_bank", "region": "IN", "flag": "🇮🇳", "description": "RBI Monetary Policy Committee — interest rate decision", "importance": "high"},
    # RBI MPC 2027 (approx bimonthly — Feb, Apr, Jun, Aug, Oct, Dec)
    {"title": "RBI MPC Meeting", "subtitle": "Feb 3–5, 2027",  "date": "2027-02-03", "category": "central_bank", "region": "IN", "flag": "🇮🇳", "description": "RBI Monetary Policy Committee — interest rate decision", "importance": "high"},

    # ── FOMC Meetings 2026 ────────────────────────────────────────────────
    {"title": "Fed FOMC Meeting", "subtitle": "Mar 17–18, 2026", "date": "2026-03-17", "category": "central_bank", "region": "US", "flag": "🇺🇸", "description": "Federal Open Market Committee — US interest rate decision", "importance": "high"},
    {"title": "Fed FOMC Meeting", "subtitle": "May 5–6, 2026",   "date": "2026-05-05", "category": "central_bank", "region": "US", "flag": "🇺🇸", "description": "Federal Open Market Committee — US interest rate decision", "importance": "high"},
    {"title": "Fed FOMC Meeting", "subtitle": "Jun 16–17, 2026", "date": "2026-06-16", "category": "central_bank", "region": "US", "flag": "🇺🇸", "description": "Federal Open Market Committee — US interest rate decision", "importance": "high"},
    {"title": "Fed FOMC Meeting", "subtitle": "Jul 28–29, 2026", "date": "2026-07-28", "category": "central_bank", "region": "US", "flag": "🇺🇸", "description": "Federal Open Market Committee — US interest rate decision", "importance": "high"},
    {"title": "Fed FOMC Meeting", "subtitle": "Sep 15–16, 2026", "date": "2026-09-15", "category": "central_bank", "region": "US", "flag": "🇺🇸", "description": "Federal Open Market Committee — US interest rate decision", "importance": "high"},
    {"title": "Fed FOMC Meeting", "subtitle": "Oct 27–28, 2026", "date": "2026-10-27", "category": "central_bank", "region": "US", "flag": "🇺🇸", "description": "Federal Open Market Committee — US interest rate decision", "importance": "high"},
    {"title": "Fed FOMC Meeting", "subtitle": "Dec 8–9, 2026",   "date": "2026-12-08", "category": "central_bank", "region": "US", "flag": "🇺🇸", "description": "Federal Open Market Committee — US interest rate decision", "importance": "high"},

    # ── ECB Meetings 2026 ─────────────────────────────────────────────────
    {"title": "ECB Policy Meeting", "subtitle": "Apr 17, 2026",  "date": "2026-04-17", "category": "central_bank", "region": "EU", "flag": "🇪🇺", "description": "European Central Bank interest rate decision", "importance": "high"},
    {"title": "ECB Policy Meeting", "subtitle": "Jun 5, 2026",   "date": "2026-06-05", "category": "central_bank", "region": "EU", "flag": "🇪🇺", "description": "European Central Bank interest rate decision", "importance": "high"},
    {"title": "ECB Policy Meeting", "subtitle": "Jul 24, 2026",  "date": "2026-07-24", "category": "central_bank", "region": "EU", "flag": "🇪🇺", "description": "European Central Bank interest rate decision", "importance": "high"},
    {"title": "ECB Policy Meeting", "subtitle": "Sep 11, 2026",  "date": "2026-09-11", "category": "central_bank", "region": "EU", "flag": "🇪🇺", "description": "European Central Bank interest rate decision", "importance": "high"},
    {"title": "ECB Policy Meeting", "subtitle": "Oct 30, 2026",  "date": "2026-10-30", "category": "central_bank", "region": "EU", "flag": "🇪🇺", "description": "European Central Bank interest rate decision", "importance": "high"},
    {"title": "ECB Policy Meeting", "subtitle": "Dec 18, 2026",  "date": "2026-12-18", "category": "central_bank", "region": "EU", "flag": "🇪🇺", "description": "European Central Bank interest rate decision", "importance": "high"},

    # ── Bank of England 2026 ──────────────────────────────────────────────
    {"title": "Bank of England MPC", "subtitle": "Mar 20, 2026",  "date": "2026-03-20", "category": "central_bank", "region": "UK", "flag": "🇬🇧", "description": "Bank of England Monetary Policy Committee — interest rate decision", "importance": "high"},
    {"title": "Bank of England MPC", "subtitle": "May 7, 2026",   "date": "2026-05-07", "category": "central_bank", "region": "UK", "flag": "🇬🇧", "description": "Bank of England Monetary Policy Committee — interest rate decision", "importance": "high"},
    {"title": "Bank of England MPC", "subtitle": "Jun 18, 2026",  "date": "2026-06-18", "category": "central_bank", "region": "UK", "flag": "🇬🇧", "description": "Bank of England Monetary Policy Committee — interest rate decision", "importance": "high"},
    {"title": "Bank of England MPC", "subtitle": "Aug 6, 2026",   "date": "2026-08-06", "category": "central_bank", "region": "UK", "flag": "🇬🇧", "description": "Bank of England Monetary Policy Committee — interest rate decision", "importance": "high"},
    {"title": "Bank of England MPC", "subtitle": "Sep 17, 2026",  "date": "2026-09-17", "category": "central_bank", "region": "UK", "flag": "🇬🇧", "description": "Bank of England Monetary Policy Committee — interest rate decision", "importance": "high"},
    {"title": "Bank of England MPC", "subtitle": "Nov 5, 2026",   "date": "2026-11-05", "category": "central_bank", "region": "UK", "flag": "🇬🇧", "description": "Bank of England Monetary Policy Committee — interest rate decision", "importance": "high"},
    {"title": "Bank of England MPC", "subtitle": "Dec 17, 2026",  "date": "2026-12-17", "category": "central_bank", "region": "UK", "flag": "🇬🇧", "description": "Bank of England Monetary Policy Committee — interest rate decision", "importance": "high"},

    # ── India Advance Tax 2026 ────────────────────────────────────────────
    {"title": "Advance Tax Deadline", "subtitle": "Jun 15, 2026 (45%)",  "date": "2026-06-15", "category": "tax", "region": "IN", "flag": "🇮🇳", "description": "India advance tax — 2nd instalment (cumulative 45%)", "importance": "medium"},
    {"title": "Advance Tax Deadline", "subtitle": "Sep 15, 2026 (75%)",  "date": "2026-09-15", "category": "tax", "region": "IN", "flag": "🇮🇳", "description": "India advance tax — 3rd instalment (cumulative 75%)", "importance": "medium"},
    {"title": "Advance Tax Deadline", "subtitle": "Dec 15, 2026 (100%)", "date": "2026-12-15", "category": "tax", "region": "IN", "flag": "🇮🇳", "description": "India advance tax — 4th instalment (cumulative 100%)", "importance": "medium"},
    {"title": "Advance Tax Deadline", "subtitle": "Mar 15, 2027 (100%)", "date": "2027-03-15", "category": "tax", "region": "IN", "flag": "🇮🇳", "description": "India advance tax — final instalment (100%)", "importance": "medium"},

    # ── India ITR ─────────────────────────────────────────────────────────
    {"title": "ITR Filing Deadline",     "subtitle": "Jul 31, 2026",      "date": "2026-07-31", "category": "tax",    "region": "IN", "flag": "🇮🇳", "description": "Income Tax Return filing deadline (non-audit cases)", "importance": "high"},
    {"title": "ITR Filing (Audit)",      "subtitle": "Oct 31, 2026",      "date": "2026-10-31", "category": "tax",    "region": "IN", "flag": "🇮🇳", "description": "Income Tax Return filing deadline (audit cases)", "importance": "medium"},

    # ── India Union Budget ────────────────────────────────────────────────
    {"title": "India Union Budget 2027", "subtitle": "Feb 1, 2027",       "date": "2027-02-01", "category": "policy", "region": "IN", "flag": "🇮🇳", "description": "Annual Union Budget presentation to Parliament", "importance": "high"},

    # ── US CPI Releases 2026 ──────────────────────────────────────────────
    {"title": "US CPI Inflation Data",   "subtitle": "Mar 12, 2026",      "date": "2026-03-12", "category": "economic_data", "region": "US", "flag": "🇺🇸", "description": "US Consumer Price Index — key inflation indicator", "importance": "high"},
    {"title": "US CPI Inflation Data",   "subtitle": "Apr 10, 2026",      "date": "2026-04-10", "category": "economic_data", "region": "US", "flag": "🇺🇸", "description": "US Consumer Price Index — key inflation indicator", "importance": "high"},
    {"title": "US CPI Inflation Data",   "subtitle": "May 13, 2026",      "date": "2026-05-13", "category": "economic_data", "region": "US", "flag": "🇺🇸", "description": "US Consumer Price Index — key inflation indicator", "importance": "high"},
    {"title": "US CPI Inflation Data",   "subtitle": "Jun 11, 2026",      "date": "2026-06-11", "category": "economic_data", "region": "US", "flag": "🇺🇸", "description": "US Consumer Price Index — key inflation indicator", "importance": "high"},
    {"title": "US CPI Inflation Data",   "subtitle": "Jul 14, 2026",      "date": "2026-07-14", "category": "economic_data", "region": "US", "flag": "🇺🇸", "description": "US Consumer Price Index — key inflation indicator", "importance": "high"},
    {"title": "US CPI Inflation Data",   "subtitle": "Aug 12, 2026",      "date": "2026-08-12", "category": "economic_data", "region": "US", "flag": "🇺🇸", "description": "US Consumer Price Index — key inflation indicator", "importance": "high"},
    {"title": "US CPI Inflation Data",   "subtitle": "Sep 11, 2026",      "date": "2026-09-11", "category": "economic_data", "region": "US", "flag": "🇺🇸", "description": "US Consumer Price Index — key inflation indicator", "importance": "high"},
    {"title": "US CPI Inflation Data",   "subtitle": "Oct 13, 2026",      "date": "2026-10-13", "category": "economic_data", "region": "US", "flag": "🇺🇸", "description": "US Consumer Price Index — key inflation indicator", "importance": "high"},

    # ── India GST Quarterly (GSTR-1 quarterly filers) ─────────────────────
    {"title": "GST Return (GSTR-1)",     "subtitle": "Apr 13, 2026",      "date": "2026-04-13", "category": "tax",    "region": "IN", "flag": "🇮🇳", "description": "GSTR-1 quarterly filing deadline (Jan–Mar quarter)", "importance": "medium"},
    {"title": "GST Return (GSTR-1)",     "subtitle": "Jul 13, 2026",      "date": "2026-07-13", "category": "tax",    "region": "IN", "flag": "🇮🇳", "description": "GSTR-1 quarterly filing deadline (Apr–Jun quarter)", "importance": "medium"},
    {"title": "GST Return (GSTR-1)",     "subtitle": "Oct 13, 2026",      "date": "2026-10-13", "category": "tax",    "region": "IN", "flag": "🇮🇳", "description": "GSTR-1 quarterly filing deadline (Jul–Sep quarter)", "importance": "medium"},
    {"title": "GST Return (GSTR-1)",     "subtitle": "Jan 13, 2027",      "date": "2027-01-13", "category": "tax",    "region": "IN", "flag": "🇮🇳", "description": "GSTR-1 quarterly filing deadline (Oct–Dec quarter)", "importance": "medium"},

    # ── India Earnings Season (approx Q4 FY26 results) ───────────────────
    {"title": "India Q4 FY26 Earnings Season", "subtitle": "Apr–May 2026", "date": "2026-04-15", "category": "market", "region": "IN", "flag": "🇮🇳", "description": "NSE/BSE listed companies report Jan–Mar 2026 quarterly results", "importance": "medium"},

    # ── US Earnings Season (approx) ───────────────────────────────────────
    {"title": "US Q1 2026 Earnings Season",    "subtitle": "Apr–May 2026", "date": "2026-04-14", "category": "market", "region": "US", "flag": "🇺🇸", "description": "S&P 500 companies report Q1 2026 quarterly earnings", "importance": "medium"},
    {"title": "US Q2 2026 Earnings Season",    "subtitle": "Jul–Aug 2026", "date": "2026-07-13", "category": "market", "region": "US", "flag": "🇺🇸", "description": "S&P 500 companies report Q2 2026 quarterly earnings", "importance": "medium"},

    # ── US Federal Budget / Debt Ceiling ─────────────────────────────────
    {"title": "US Fiscal Year End",            "subtitle": "Sep 30, 2026", "date": "2026-09-30", "category": "policy", "region": "US", "flag": "🇺🇸", "description": "US Federal Government fiscal year end — budget debates", "importance": "medium"},

    # ── G20 Summit (approx — South Africa 2025, rotating) ────────────────
    {"title": "G7 Summit 2026",                "subtitle": "Jun 2026",      "date": "2026-06-01", "category": "policy", "region": "GLOBAL", "flag": "🌍", "description": "G7 leaders summit — global economic policy discussions", "importance": "medium"},
]


def get_upcoming_financial_events(max_events: int = 25) -> List[Dict[str, Any]]:
    """
    Return upcoming financial calendar events sorted by date.
    Combines static events with dynamically computed ones (NSE expiry, US NFP).
    """
    today = date.today()
    events: List[Dict[str, Any]] = []

    # Add static events that are still in the future
    for e in _STATIC_EVENTS:
        event_date = date.fromisoformat(e["date"])
        if event_date >= today:
            enriched = dict(e)
            enriched["days_until"] = (event_date - today).days
            events.append(enriched)

    # ── Dynamic: NSE/BSE F&O Monthly Expiry (next 6 months) ─────────────
    for offset in range(7):
        month = today.month + offset
        year = today.year
        while month > 12:
            month -= 12
            year += 1
        expiry = _last_thursday(year, month)
        if expiry >= today:
            events.append({
                "title": "NSE F&O Monthly Expiry",
                "subtitle": expiry.strftime("%b %d, %Y"),
                "date": expiry.isoformat(),
                "category": "market",
                "region": "IN",
                "flag": "🇮🇳",
                "description": "NSE/BSE Futures & Options monthly contract expiry — high volatility expected",
                "importance": "medium",
                "days_until": (expiry - today).days,
            })

    # ── Dynamic: US Non-Farm Payrolls (first Friday each month, ~5 months) ──
    for offset in range(6):
        month = today.month + offset
        year = today.year
        while month > 12:
            month -= 12
            year += 1
        nfp_date = _first_friday(year, month)
        if nfp_date >= today:
            events.append({
                "title": "US Non-Farm Payrolls",
                "subtitle": nfp_date.strftime("%b %d, %Y"),
                "date": nfp_date.isoformat(),
                "category": "economic_data",
                "region": "US",
                "flag": "🇺🇸",
                "description": "US monthly jobs report — key market-moving employment indicator",
                "importance": "high",
                "days_until": (nfp_date - today).days,
            })

    # Sort by date, deduplicate by (title + date), and take top N
    seen = set()
    unique: List[Dict[str, Any]] = []
    for e in sorted(events, key=lambda x: x["date"]):
        key = (e["title"], e["date"])
        if key not in seen:
            seen.add(key)
            unique.append(e)

    return unique[:max_events]


# ── Global Financial News ─────────────────────────────────────────────────────

async def get_global_financial_news(count: int = 8) -> List[Dict[str, Any]]:
    """
    Fetch top financial news from global + India RSS feeds.
    - Filters out individual stock/corporate news from foreign companies.
    - Guarantees at least _MIN_INDIA_NEWS articles from India sources.
    - Falls back to empty list if all feeds fail.
    """

    async def _fetch_feed(
        client: httpx.AsyncClient,
        feed: Dict[str, str],
        is_india_source: bool = False,
    ) -> List[Dict[str, Any]]:
        try:
            r = await client.get(feed["url"], headers=_RSS_HEADERS, timeout=_TIMEOUT)
            r.raise_for_status()
            # Use raw bytes so feedparser can detect encoding from XML declaration
            # (important for MoneyControl which uses ISO-8859-1)
            parsed = feedparser.parse(r.content)
            items: List[Dict[str, Any]] = []
            for entry in parsed.entries[:15]:
                title = _strip_html(entry.get("title", ""))
                summary = _strip_html(
                    entry.get("summary", "") or entry.get("description", "")
                )
                link = entry.get("link", "")
                if not title or not link:
                    continue

                # Parse publication time
                pub_dt: str | None = None
                for time_attr in ("published_parsed", "updated_parsed"):
                    t = getattr(entry, time_attr, None)
                    if t:
                        pub_dt = datetime.utcfromtimestamp(timegm(t)).isoformat() + "Z"
                        break

                # Skip articles older than 24 hours
                if pub_dt:
                    pub_datetime = datetime.fromisoformat(pub_dt.replace("Z", "+00:00"))
                    if pub_datetime < datetime.now(timezone.utc) - timedelta(hours=24):
                        continue

                score, category = _score_and_categorize(title, summary)
                if score < 0:
                    continue  # filter irrelevant

                # Force India category for articles from India feeds
                if is_india_source:
                    if category not in ("central_bank", "economy", "commodities", "crypto", "policy"):
                        category = "india"

                items.append({
                    "title": title,
                    "url": link,
                    "published": pub_dt,
                    "source": feed["name"],
                    "category": category,
                    "relevance_score": score,
                    "summary": summary[:220] if summary else "",
                    "is_india_source": is_india_source,
                })
            return items
        except Exception as exc:
            logger.warning("Failed to fetch news feed '%s': %s", feed["name"], exc)
            return []

    try:
        async with httpx.AsyncClient() as client:
            global_results, india_results = await asyncio.gather(
                asyncio.gather(*[_fetch_feed(client, f, False) for f in _GLOBAL_NEWS_FEEDS]),
                asyncio.gather(*[_fetch_feed(client, f, True)  for f in _INDIA_NEWS_FEEDS]),
            )

        all_global: List[Dict[str, Any]] = [i for batch in global_results for i in batch]
        all_india:  List[Dict[str, Any]] = [i for batch in india_results  for i in batch]

        # Deduplicate each pool by normalised title prefix
        def _dedupe(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            seen: set = set()
            out: List[Dict[str, Any]] = []
            for item in items:
                key = re.sub(r"\W+", "", item["title"].lower())[:60]
                if key not in seen:
                    seen.add(key)
                    out.append(item)
            return out

        global_items = _dedupe(all_global)
        india_items  = _dedupe(all_india)

        # Filter foreign individual-stock news from the global pool
        global_items = [
            item for item in global_items
            if not _is_individual_foreign_stock(
                item["title"], item.get("summary", ""), item["category"]
            )
        ]

        # Sort each pool by relevance then recency
        def _sort_key(x: Dict[str, Any]):
            return (x["relevance_score"], x["published"] or "")

        global_items.sort(key=_sort_key, reverse=True)
        india_items.sort(key=_sort_key, reverse=True)

        # Build final list: guarantee _MIN_INDIA_NEWS India slots, fill rest from global
        india_slots  = min(len(india_items), max(_MIN_INDIA_NEWS, count // 2))
        global_slots = max(0, count - india_slots)

        final = india_items[:india_slots] + global_items[:global_slots]

        # Re-sort the combined list for natural reading order (recent + relevant first)
        final.sort(key=_sort_key, reverse=True)

        # Strip internal fields before returning
        return [
            {
                "title":     item["title"],
                "url":       item["url"],
                "published": item["published"],
                "source":    item["source"],
                "category":  item["category"],
                "summary":   item["summary"],
            }
            for item in final
        ]

    except Exception as exc:
        logger.warning("Failed to fetch global financial news: %s", exc)
        return []


# ── 30-minute news cache ───────────────────────────────────────────────────────

_NEWS_CACHE_TTL_MINUTES = 30
_news_cache_lock = threading.Lock()
_news_cache_data: List[Dict[str, Any]] = []
_news_cache_expires_at: datetime = datetime.min.replace(tzinfo=timezone.utc)


async def get_cached_global_financial_news(count: int = 8) -> List[Dict[str, Any]]:
    """Return news from the in-memory cache if fresh; otherwise fetch and refresh."""
    global _news_cache_data, _news_cache_expires_at
    now = datetime.now(timezone.utc)
    with _news_cache_lock:
        if _news_cache_data and now < _news_cache_expires_at:
            return _news_cache_data[:count]

    # Fetch outside the lock to avoid blocking other requests
    fresh = await get_global_financial_news(count=count)

    with _news_cache_lock:
        _news_cache_data = fresh
        _news_cache_expires_at = datetime.now(timezone.utc) + timedelta(minutes=_NEWS_CACHE_TTL_MINUTES)

    return fresh


def refresh_news_cache() -> None:
    """Synchronously warm / refresh the news cache. Called by the scheduler every 30 min."""
    global _news_cache_data, _news_cache_expires_at
    try:
        loop = asyncio.new_event_loop()
        try:
            fresh = loop.run_until_complete(get_global_financial_news(count=8))
        finally:
            loop.close()
        with _news_cache_lock:
            _news_cache_data = fresh
            _news_cache_expires_at = datetime.now(timezone.utc) + timedelta(minutes=_NEWS_CACHE_TTL_MINUTES)
        logger.info("News cache refreshed: %d articles", len(fresh))
    except Exception as exc:
        logger.warning("News cache refresh failed: %s", exc)
