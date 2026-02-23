"""
AMFI NAV data cache service.
Downloads, parses, and caches the full NAV list from amfiindia.com.
Thread-safe in-memory singleton with configurable TTL.
"""
import logging
import re
import requests
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

from app.core.config import settings

logger = logging.getLogger(__name__)

# Noise words/suffixes to strip when tokenizing fund names
_NOISE_PATTERNS = [
    ' - DIRECT PLAN', ' -DIRECT PLAN', ' - REGULAR PLAN', ' -REGULAR PLAN',
    ' - GROWTH', ' -GROWTH', ' GROWTH', ' - DIVIDEND', ' -DIVIDEND',
    '(G)', '(D)', ' PLAN', ' OPTION',
]

# Stop words to exclude from significant token sets
_STOP_WORDS = frozenset({
    'FUND', 'MUTUAL', 'SCHEME', 'PLAN', 'THE', 'OF', 'AND', 'FOR',
})


def _tokenize(name: str) -> Set[str]:
    """
    Normalize and tokenize a fund name for matching.
    - Uppercase
    - Strip known noise words/suffixes
    - Split on non-alphanumeric characters
    - Remove single-char tokens
    """
    s = name.upper()
    for noise in _NOISE_PATTERNS:
        s = s.replace(noise, '')
    # Replace non-alphanumeric with space, collapse whitespace
    s = re.sub(r'[^A-Z0-9]+', ' ', s).strip()
    tokens = s.split()
    return set(t for t in tokens if len(t) > 1)


class AMFIScheme:
    """Parsed representation of a single AMFI scheme line."""
    __slots__ = (
        'scheme_code', 'isin1', 'isin2', 'scheme_name', 'nav',
        'nav_date', 'amc_name',
        'name_upper', 'name_tokens', 'is_direct', 'is_growth',
    )

    def __init__(
        self,
        scheme_code: str,
        isin1: str,
        isin2: str,
        scheme_name: str,
        nav: float,
        nav_date: str,
        amc_name: str,
    ):
        self.scheme_code = scheme_code
        self.isin1 = isin1
        self.isin2 = isin2
        self.scheme_name = scheme_name
        self.nav = nav
        self.nav_date = nav_date
        self.amc_name = amc_name
        # Pre-computed for fast matching
        self.name_upper = scheme_name.upper()
        self.name_tokens = _tokenize(scheme_name)
        self.is_direct = 'DIRECT' in self.name_upper
        self.is_growth = 'GROWTH' in self.name_upper

    @property
    def isin(self) -> str:
        """Return the primary ISIN (payout/growth preferred over reinvestment)."""
        return self.isin1 if self.isin1 else self.isin2


class AMFICache:
    """Singleton-style class-level cache for AMFI NAV data."""

    _schemes: List[AMFIScheme] = []
    _isin_index: Dict[str, AMFIScheme] = {}
    _amc_index: Dict[str, List[AMFIScheme]] = {}
    _last_fetched: Optional[datetime] = None
    _cache_duration = timedelta(hours=4)
    _lock = threading.Lock()

    @classmethod
    def get_schemes(cls) -> List[AMFIScheme]:
        """Get all parsed AMFI schemes (auto-refreshes if stale)."""
        cls._ensure_loaded()
        return cls._schemes

    @classmethod
    def get_by_isin(cls, isin: str) -> Optional[AMFIScheme]:
        """Lookup a scheme by ISIN (O(1) dict lookup)."""
        cls._ensure_loaded()
        return cls._isin_index.get(isin)

    @classmethod
    def get_schemes_by_amc(cls, amc_key: str) -> List[AMFIScheme]:
        """Get all schemes belonging to a normalized AMC name."""
        cls._ensure_loaded()
        return cls._amc_index.get(amc_key.upper().strip(), [])

    @classmethod
    def get_amc_names(cls) -> List[str]:
        """Get all unique AMC names."""
        cls._ensure_loaded()
        return list(cls._amc_index.keys())

    @classmethod
    def _ensure_loaded(cls):
        """Load data if not cached or cache is stale."""
        if cls._last_fetched and (datetime.now() - cls._last_fetched < cls._cache_duration):
            return
        with cls._lock:
            # Double-check after acquiring lock
            if cls._last_fetched and (datetime.now() - cls._last_fetched < cls._cache_duration):
                return
            cls._fetch_and_parse()

    @classmethod
    def _fetch_and_parse(cls):
        """Download and parse the AMFI NAV text file."""
        try:
            url = settings.AMFI_NAV_URL
            response = requests.get(url, timeout=settings.API_TIMEOUT)
            response.raise_for_status()

            lines = response.text.split('\n')
            schemes = []
            isin_index = {}
            amc_index = {}
            current_amc = ''

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                parts = line.split(';')

                if len(parts) < 5:
                    # Not a scheme line — could be AMC header or category header
                    # AMC headers are plain text without semicolons and without
                    # "Open Ended Schemes" / "Close Ended Schemes" prefixes
                    if (not line.startswith('Open Ended')
                            and not line.startswith('Close Ended')
                            and not line.startswith('Interval Fund')
                            and 'Scheme' not in line
                            and len(line) > 3):
                        current_amc = line.strip()
                    continue

                if len(parts) < 6:
                    continue

                scheme_code = parts[0].strip()
                isin1 = parts[1].strip()
                isin2 = parts[2].strip()
                scheme_name = parts[3].strip()
                nav_str = parts[4].strip()
                nav_date = parts[5].strip() if len(parts) > 5 else ''

                # Skip if no valid NAV
                try:
                    nav = float(nav_str) if nav_str and nav_str != 'N.A.' else 0.0
                except ValueError:
                    nav = 0.0

                scheme = AMFIScheme(
                    scheme_code=scheme_code,
                    isin1=isin1,
                    isin2=isin2,
                    scheme_name=scheme_name,
                    nav=nav,
                    nav_date=nav_date,
                    amc_name=current_amc,
                )
                schemes.append(scheme)

                # Build ISIN index
                if isin1:
                    isin_index[isin1] = scheme
                if isin2:
                    isin_index[isin2] = scheme

                # Build AMC index
                amc_key = current_amc.upper().strip()
                if amc_key:
                    if amc_key not in amc_index:
                        amc_index[amc_key] = []
                    amc_index[amc_key].append(scheme)

            # Atomically replace cached data
            cls._schemes = schemes
            cls._isin_index = isin_index
            cls._amc_index = amc_index
            cls._last_fetched = datetime.now()

            logger.info(
                f"AMFI cache loaded: {len(schemes)} schemes, "
                f"{len(isin_index)} ISINs, {len(amc_index)} AMCs"
            )

        except Exception as e:
            logger.error(f"Failed to fetch/parse AMFI NAV data: {e}")
            # Keep stale data if available rather than clearing
            if not cls._schemes:
                raise

    @classmethod
    def clear_cache(cls):
        """Clear the AMFI cache (for testing or forced refresh)."""
        with cls._lock:
            cls._schemes = []
            cls._isin_index = {}
            cls._amc_index = {}
            cls._last_fetched = None
            logger.info("AMFI cache cleared")
