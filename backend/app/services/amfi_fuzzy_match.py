"""
Heuristic fuzzy matching engine for AMFI mutual fund schemes.
When exact/substring matching fails, this module finds the closest
AMFI scheme names using multi-signal scoring.
"""
import logging
import re
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Set

from app.services.amfi_cache import AMFICache, AMFIScheme, _tokenize, _STOP_WORDS

logger = logging.getLogger(__name__)

# Known AMC name fragments mapped to their full AMFI AMC header names.
# Keys are checked against the uppercased query; values are used to filter
# via AMFICache.get_schemes_by_amc().
# Multiple keys can map to the same AMC for common abbreviations.
_AMC_KEYWORDS: List[tuple] = [
    ('PPFAS', 'PPFAS MUTUAL FUND'),
    ('PARAG PARIKH', 'PPFAS MUTUAL FUND'),
    ('ADITYA BIRLA', 'ADITYA BIRLA SUN LIFE MUTUAL FUND'),
    ('ABSL', 'ADITYA BIRLA SUN LIFE MUTUAL FUND'),
    ('ICICI PRUDENTIAL', 'ICICI PRUDENTIAL MUTUAL FUND'),
    ('ICICI PRU', 'ICICI PRUDENTIAL MUTUAL FUND'),
    ('HDFC', 'HDFC MUTUAL FUND'),
    ('SBI', 'SBI MUTUAL FUND'),
    ('AXIS', 'AXIS MUTUAL FUND'),
    ('KOTAK', 'KOTAK MAHINDRA MUTUAL FUND'),
    ('MIRAE ASSET', 'MIRAE ASSET MUTUAL FUND'),
    ('MIRAE', 'MIRAE ASSET MUTUAL FUND'),
    ('DSP', 'DSP MUTUAL FUND'),
    ('NIPPON', 'NIPPON INDIA MUTUAL FUND'),
    ('NIPPON INDIA', 'NIPPON INDIA MUTUAL FUND'),
    ('UTI', 'UTI MUTUAL FUND'),
    ('TATA', 'TATA MUTUAL FUND'),
    ('MOTILAL OSWAL', 'MOTILAL OSWAL MUTUAL FUND'),
    ('MOTILAL', 'MOTILAL OSWAL MUTUAL FUND'),
    ('FRANKLIN', 'FRANKLIN TEMPLETON MUTUAL FUND'),
    ('TEMPLETON', 'FRANKLIN TEMPLETON MUTUAL FUND'),
    ('EDELWEISS', 'EDELWEISS MUTUAL FUND'),
    ('SUNDARAM', 'SUNDARAM MUTUAL FUND'),
    ('CANARA ROBECO', 'CANARA ROBECO MUTUAL FUND'),
    ('INVESCO', 'INVESCO MUTUAL FUND'),
    ('L&T', 'BANDHAN MUTUAL FUND'),
    ('BANDHAN', 'BANDHAN MUTUAL FUND'),
    ('MAHINDRA MANULIFE', 'MAHINDRA MANULIFE MUTUAL FUND'),
    ('QUANT', 'QUANT MUTUAL FUND'),
    ('PGIM', 'PGIM INDIA MUTUAL FUND'),
    ('BARODA BNP', 'BARODA BNP PARIBAS MUTUAL FUND'),
    ('BARODA', 'BARODA BNP PARIBAS MUTUAL FUND'),
    ('HSBC', 'HSBC MUTUAL FUND'),
    ('IDFC', 'BANDHAN MUTUAL FUND'),
    ('JM FINANCIAL', 'JM FINANCIAL MUTUAL FUND'),
    ('JM', 'JM FINANCIAL MUTUAL FUND'),
    ('UNION', 'UNION MUTUAL FUND'),
    ('GROWW', 'GROWW MUTUAL FUND'),
    ('WHITEOAK', 'WHITEOAK CAPITAL MUTUAL FUND'),
    ('360 ONE', '360 ONE MUTUAL FUND'),
    ('IIFL', '360 ONE MUTUAL FUND'),
    ('NAVI', 'NAVI MUTUAL FUND'),
    ('SAMCO', 'SAMCO MUTUAL FUND'),
    ('QUANTUM', 'QUANTUM MUTUAL FUND'),
    ('TRUST', 'TRUST MUTUAL FUND'),
    ('ITI', 'ITI MUTUAL FUND'),
    ('HELIOS', 'HELIOS MUTUAL FUND'),
    ('BAJAJ FINSERV', 'BAJAJ FINSERV MUTUAL FUND'),
    ('ZERODHA', 'ZERODHA MUTUAL FUND'),
    ('OLD BRIDGE', 'OLD BRIDGE MUTUAL FUND'),
    ('SHRIRAM', 'SHRIRAM MUTUAL FUND'),
]


def _detect_amc(query_upper: str) -> Optional[str]:
    """
    Detect the AMC from a fund name query.
    Returns the full AMFI AMC header name, or None if not detected.
    Longer keywords are checked first (sorted by descending length).
    """
    for keyword, amc_name in _AMC_KEYWORDS:
        if keyword in query_upper:
            return amc_name
    return None


def _compute_score(
    query_tokens: Set[str],
    query_upper: str,
    scheme: AMFIScheme,
    query_is_direct: bool,
    query_is_growth: bool,
) -> float:
    """
    Compute a similarity score between a query and an AMFI scheme.
    Returns a float, typically in the range [0.0, 1.0+].
    """
    score = 0.0

    # Signal 1: SequenceMatcher ratio (character-level similarity)
    seq_score = SequenceMatcher(None, query_upper, scheme.name_upper).ratio()
    score += seq_score * 0.50

    # Signal 2: Token Jaccard overlap (word-level)
    if scheme.name_tokens and query_tokens:
        intersection = query_tokens & scheme.name_tokens
        union = query_tokens | scheme.name_tokens
        token_score = len(intersection) / len(union) if union else 0
        score += token_score * 0.30

    # Signal 3: Keyword containment (significant query tokens in scheme)
    significant_tokens = query_tokens - _STOP_WORDS
    if significant_tokens:
        contained = sum(1 for t in significant_tokens if t in scheme.name_upper)
        containment_score = contained / len(significant_tokens)
        score += containment_score * 0.15

    # Signal 4: Plan type bonus
    if query_is_direct and scheme.is_direct:
        score += 0.025
    elif not query_is_direct and not scheme.is_direct:
        score += 0.01
    if query_is_growth and scheme.is_growth:
        score += 0.025
    elif not query_is_growth and not scheme.is_growth:
        score += 0.01

    return score


def fuzzy_search_amfi(
    query: str,
    top_n: int = 5,
) -> List[Dict]:
    """
    Find the top N best-matching AMFI schemes for a given fund name.

    Args:
        query: The mutual fund name from the statement (may be truncated/abbreviated).
        top_n: Number of suggestions to return.

    Returns:
        List of dicts sorted by score descending:
        [{'scheme_code', 'isin', 'scheme_name', 'nav', 'score', 'amc_name'}, ...]
    """
    if not query or not query.strip():
        return []

    query_upper = query.upper().strip()
    query_tokens = _tokenize(query)
    query_is_direct = 'DIRECT' in query_upper
    query_is_growth = 'GROWTH' in query_upper

    # Step 1: Detect AMC and narrow candidate pool
    detected_amc = _detect_amc(query_upper)
    if detected_amc:
        candidates = AMFICache.get_schemes_by_amc(detected_amc)
        if not candidates:
            # AMC keyword matched but no schemes found under that exact name.
            # Try partial matching against all AMC names.
            for amc_name in AMFICache.get_amc_names():
                if detected_amc.split()[0] in amc_name:
                    candidates = AMFICache.get_schemes_by_amc(amc_name)
                    if candidates:
                        break
        if not candidates:
            # Fallback to all schemes
            candidates = AMFICache.get_schemes()
            logger.debug(f"AMC '{detected_amc}' detected but no schemes found, using all schemes")
    else:
        candidates = AMFICache.get_schemes()
        logger.debug(f"No AMC detected for '{query[:50]}', searching all schemes")

    # Step 2: Filter by plan type if strongly indicated
    if query_is_direct:
        direct_candidates = [s for s in candidates if s.is_direct]
        if direct_candidates:
            candidates = direct_candidates
    elif 'REGULAR' in query_upper:
        regular_candidates = [s for s in candidates if not s.is_direct]
        if regular_candidates:
            candidates = regular_candidates

    # Step 3: Score all candidates
    scored = []
    for scheme in candidates:
        # Skip schemes without ISINs (useless for resolution)
        if not scheme.isin:
            continue
        s = _compute_score(query_tokens, query_upper, scheme, query_is_direct, query_is_growth)
        scored.append((s, scheme))

    # Step 4: Sort and return top N
    scored.sort(key=lambda x: x[0], reverse=True)

    results = []
    for score, scheme in scored[:top_n]:
        results.append({
            'scheme_code': scheme.scheme_code,
            'isin': scheme.isin,
            'scheme_name': scheme.scheme_name,
            'nav': scheme.nav,
            'score': round(score, 4),
            'amc_name': scheme.amc_name,
        })

    if results:
        logger.info(
            f"Fuzzy search for '{query[:60]}': top match = "
            f"'{results[0]['scheme_name'][:60]}' (score={results[0]['score']})"
        )

    return results
