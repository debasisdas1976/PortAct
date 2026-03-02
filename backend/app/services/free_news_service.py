"""
Free (non-AI) alert sources: RSS feeds, price-based analysis, and optional Finnhub API.
Works without any API key configuration — RSS and price analysis are always available.
"""
import hashlib
import asyncio
import re
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from html import unescape
import httpx
import feedparser
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func
from loguru import logger

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.asset import Asset, AssetType
from app.models.alert import Alert, AlertType, AlertSeverity


@dataclass
class FreeAlertResult:
    """Structured result from a free alert source."""
    source: str                                # "rss", "price_analysis", "finnhub"
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    suggested_action: Optional[str] = None
    action_url: Optional[str] = None
    asset_id: Optional[int] = None


class FreeNewsService:
    """Service to generate alerts from free data sources (RSS, price analysis, Finnhub)."""

    # ── RSS feed configuration ──
    RSS_FEEDS_GENERAL = [
        {"name": "MoneyControl", "url": "https://www.moneycontrol.com/rss/MCtopnews.xml"},
        {"name": "ET Markets", "url": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"},
        {"name": "ET Stocks", "url": "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms"},
        {"name": "LiveMint Markets", "url": "https://www.livemint.com/rss/markets"},
    ]
    RSS_FEEDS_CRYPTO = [
        {"name": "CoinDesk", "url": "https://www.coindesk.com/arc/outboundfeeds/rss/"},
        {"name": "CoinTelegraph", "url": "https://cointelegraph.com/rss"},
    ]

    MAX_GENERIC_NEWS = 8          # Max generic (non-portfolio-matched) news items total
    MAX_ENTRIES_PER_FEED = 10     # Max entries to consider per RSS feed

    # ── Price analysis thresholds ──
    REBALANCE_THRESHOLD_PCT = 50.0

    # ── Maturity reminder configuration ──
    MATURITY_ASSET_TYPES = [
        AssetType.FIXED_DEPOSIT, AssetType.RECURRING_DEPOSIT,
        AssetType.CORPORATE_BOND, AssetType.RBI_BOND, AssetType.TAX_SAVING_BOND,
        AssetType.NSC, AssetType.KVP, AssetType.SCSS, AssetType.MIS,
        AssetType.INSURANCE_POLICY, AssetType.SOVEREIGN_GOLD_BOND,
    ]
    MATURITY_THRESHOLDS = [
        (30, AlertSeverity.CRITICAL),
        (60, AlertSeverity.WARNING),
        (90, AlertSeverity.INFO),
    ]

    HTTP_TIMEOUT = 15  # seconds for RSS/Finnhub HTTP calls

    # Regex to strip HTML tags
    _HTML_TAG_RE = re.compile(r"<[^>]+>")

    @staticmethod
    def _strip_html(text: str) -> str:
        """Remove HTML tags and decode entities from RSS content."""
        if not text:
            return ""
        clean = FreeNewsService._HTML_TAG_RE.sub("", text)
        clean = unescape(clean)
        # Collapse whitespace
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean

    # ──────────────────────────────────────────────────────────────────────
    # Public interface
    # ──────────────────────────────────────────────────────────────────────

    async def process_free_alerts(
        self,
        db: Session,
        user_id: int,
        session_id: Optional[str] = None,
    ) -> Tuple[int, str]:
        """
        Run all free alert sources for a user and persist results.
        Returns (alerts_created, session_id).
        """
        alerts_created = 0

        # 1. RSS News Alerts
        try:
            rss_alerts = await self._fetch_rss_alerts(db, user_id)
            for result in rss_alerts:
                if self._create_alert_if_new(db, user_id, result):
                    alerts_created += 1
            logger.info(f"RSS alerts for user {user_id}: {len(rss_alerts)} candidates, {alerts_created} created.")
        except Exception as exc:
            logger.error(f"RSS alert source failed for user {user_id}: {exc}")

        # 2. Price-Based Analysis Alerts
        price_count = 0
        try:
            price_alerts = self._generate_price_alerts(db, user_id)
            for result in price_alerts:
                if self._create_alert_if_new(db, user_id, result):
                    alerts_created += 1
                    price_count += 1
            logger.info(f"Price analysis alerts for user {user_id}: {len(price_alerts)} candidates, {price_count} created.")
        except Exception as exc:
            logger.error(f"Price analysis alert source failed for user {user_id}: {exc}")

        # 3. Finnhub Alerts (optional — only if API key is configured)
        finnhub_count = 0
        try:
            finnhub_key = self._get_finnhub_api_key()
            if finnhub_key:
                finnhub_alerts = await self._fetch_finnhub_alerts(db, user_id, finnhub_key)
                for result in finnhub_alerts:
                    if self._create_alert_if_new(db, user_id, result):
                        alerts_created += 1
                        finnhub_count += 1
                logger.info(f"Finnhub alerts for user {user_id}: {len(finnhub_alerts)} candidates, {finnhub_count} created.")
        except Exception as exc:
            logger.error(f"Finnhub alert source failed for user {user_id}: {exc}")

        logger.info(f"Free alerts complete for user {user_id}: {alerts_created} total alerts created.")
        return alerts_created, session_id or ""

    # ──────────────────────────────────────────────────────────────────────
    # Deduplication + alert creation
    # ──────────────────────────────────────────────────────────────────────

    def _dedupe_key(self, result: FreeAlertResult) -> str:
        """Generate a deduplication key from the alert's action_url or title hash."""
        if result.action_url and result.action_url.startswith("http"):
            return result.action_url
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        raw = f"{result.title}:{today}"
        return f"hash:{hashlib.sha256(raw.encode()).hexdigest()[:16]}"

    def _create_alert_if_new(self, db: Session, user_id: int, result: FreeAlertResult) -> bool:
        """Create an alert only if no duplicate exists (same action_url today)."""
        dedupe_key = self._dedupe_key(result)
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        existing = db.query(Alert).filter(
            Alert.user_id == user_id,
            Alert.action_url == dedupe_key,
            Alert.created_at >= today_start,
        ).first()

        if existing:
            return False

        source_tag = f"[{result.source.upper()}] "
        alert = Alert(
            user_id=user_id,
            asset_id=result.asset_id,
            alert_type=result.alert_type,
            severity=result.severity,
            title=(source_tag + result.title)[:200],
            message=result.message[:2000],
            suggested_action=result.suggested_action,
            action_url=dedupe_key,
            is_actionable=True,
        )
        db.add(alert)
        try:
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False

    # ──────────────────────────────────────────────────────────────────────
    # Source A: RSS Feeds
    # ──────────────────────────────────────────────────────────────────────

    async def _fetch_rss_alerts(self, db: Session, user_id: int) -> List[FreeAlertResult]:
        """Fetch RSS feeds and match articles against user's portfolio assets."""
        # Load user's active assets for matching
        assets = db.query(Asset).filter(
            Asset.user_id == user_id,
            Asset.is_active == True,
        ).all()

        # Determine which feeds to fetch
        has_crypto = any(a.asset_type == AssetType.CRYPTO for a in assets)
        feeds_to_fetch = list(self.RSS_FEEDS_GENERAL)
        if has_crypto:
            feeds_to_fetch.extend(self.RSS_FEEDS_CRYPTO)

        # Fetch all feeds concurrently
        entries = await self._fetch_all_feeds(feeds_to_fetch)

        results: List[FreeAlertResult] = []
        generic_news: List[FreeAlertResult] = []

        for entry_data in entries:
            entry = entry_data["entry"]
            source_name = entry_data["source_name"]
            title = self._strip_html(entry.get("title", ""))
            summary = self._strip_html(entry.get("summary", ""))
            link = entry.get("link", "")

            if not title:
                continue

            # Try to match against portfolio assets
            matched_asset = self._match_article_to_assets(title, summary, assets)

            if matched_asset:
                results.append(FreeAlertResult(
                    source="rss",
                    alert_type=AlertType.NEWS_EVENT,
                    severity=AlertSeverity.INFO,
                    title=f"{title[:90]}",
                    message=f"[{source_name}] {summary[:500]}" if summary else f"[{source_name}] {title}",
                    action_url=link or None,
                    asset_id=matched_asset.id,
                    suggested_action="Read the full article for details relevant to your holding.",
                ))
            elif len(generic_news) < self.MAX_GENERIC_NEWS:
                generic_news.append(FreeAlertResult(
                    source="rss",
                    alert_type=AlertType.NEWS_EVENT,
                    severity=AlertSeverity.INFO,
                    title=f"{title[:90]}",
                    message=f"[{source_name}] {summary[:500]}" if summary else f"[{source_name}] {title}",
                    action_url=link or None,
                ))

        results.extend(generic_news)
        return results

    async def _fetch_all_feeds(self, feeds: List[dict]) -> List[dict]:
        """Fetch and parse all RSS feeds concurrently."""
        async def _fetch_one(feed_config: dict) -> List[dict]:
            try:
                async with httpx.AsyncClient(timeout=self.HTTP_TIMEOUT) as client:
                    resp = await client.get(
                        feed_config["url"],
                        headers={"User-Agent": "PortAct/1.0"},
                        follow_redirects=True,
                    )
                    resp.raise_for_status()
                feed = feedparser.parse(resp.text)
                return [
                    {"entry": entry, "source_name": feed_config["name"]}
                    for entry in feed.entries[:self.MAX_ENTRIES_PER_FEED]
                ]
            except Exception as exc:
                logger.warning(f"Failed to fetch RSS feed {feed_config['name']}: {exc}")
                return []

        tasks = [_fetch_one(f) for f in feeds]
        all_results = await asyncio.gather(*tasks, return_exceptions=False)
        # Flatten
        entries = []
        for result in all_results:
            entries.extend(result)
        return entries

    def _match_article_to_assets(
        self, title: str, summary: str, assets: List[Asset]
    ) -> Optional[Asset]:
        """Check if an article title/summary mentions any portfolio asset name or symbol."""
        text = (title + " " + summary).lower()
        for asset in assets:
            # Match on symbol (prefer — more specific)
            if asset.symbol and len(asset.symbol) >= 2:
                # Exact word boundary match for symbols to avoid false positives
                sym = asset.symbol.lower()
                # Check for symbol as a word (surrounded by non-alphanumeric or at start/end)
                if f" {sym} " in f" {text} ":
                    return asset
            # Match on name (at least 4 chars to avoid false positives)
            if asset.name and len(asset.name) >= 4:
                if asset.name.lower() in text:
                    return asset
        return None

    # ──────────────────────────────────────────────────────────────────────
    # Source B: Price-Based Analysis
    # ──────────────────────────────────────────────────────────────────────

    def _generate_price_alerts(self, db: Session, user_id: int) -> List[FreeAlertResult]:
        """Analyze existing DB data to generate price, maturity, and rebalance alerts."""
        results: List[FreeAlertResult] = []
        results.extend(self._check_maturity_reminders(db, user_id))
        results.extend(self._check_rebalance(db, user_id))
        return results

    def _check_maturity_reminders(self, db: Session, user_id: int) -> List[FreeAlertResult]:
        """Generate MATURITY_REMINDER for assets approaching maturity date."""
        assets = db.query(Asset).filter(
            Asset.user_id == user_id,
            Asset.is_active == True,
            Asset.asset_type.in_(list(self.MATURITY_ASSET_TYPES)),
        ).all()

        results = []
        now = datetime.now(timezone.utc)

        for asset in assets:
            if not asset.details or not isinstance(asset.details, dict):
                continue
            maturity_str = asset.details.get("maturity_date")
            if not maturity_str:
                continue

            try:
                maturity_date = datetime.strptime(str(maturity_str), "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue

            days_left = (maturity_date - now).days
            if days_left < 0:
                continue  # Already matured

            # Find the matching threshold
            for threshold_days, severity in self.MATURITY_THRESHOLDS:
                if days_left <= threshold_days:
                    results.append(FreeAlertResult(
                        source="price_analysis",
                        alert_type=AlertType.MATURITY_REMINDER,
                        severity=severity,
                        title=f"{asset.name} matures in {days_left} days",
                        message=(
                            f"Your {asset.asset_type.value.replace('_', ' ')} '{asset.name}' "
                            f"is maturing on {maturity_str}. "
                            f"Current value: {asset.current_value:,.2f}."
                        ),
                        suggested_action=(
                            "Plan for reinvestment or withdrawal. "
                            "Check if auto-renewal is set up with your bank/institution."
                        ),
                        asset_id=asset.id,
                    ))
                    break  # Use the tightest matching threshold

        return results

    def _check_rebalance(self, db: Session, user_id: int) -> List[FreeAlertResult]:
        """Generate REBALANCE_SUGGESTION if one asset type dominates the portfolio."""
        rows = (
            db.query(
                Asset.asset_type,
                sa_func.sum(Asset.current_value).label("type_total"),
            )
            .filter(Asset.user_id == user_id, Asset.is_active == True)
            .group_by(Asset.asset_type)
            .all()
        )

        if not rows:
            return []

        total_value = sum(r.type_total or 0 for r in rows)
        if total_value <= 0:
            return []

        results = []
        for row in rows:
            type_total = row.type_total or 0
            pct = (type_total / total_value) * 100
            if pct >= self.REBALANCE_THRESHOLD_PCT:
                asset_type_display = str(row.asset_type).replace("_", " ").title()
                results.append(FreeAlertResult(
                    source="price_analysis",
                    alert_type=AlertType.REBALANCE_SUGGESTION,
                    severity=AlertSeverity.WARNING,
                    title=f"{asset_type_display} is {pct:.0f}% of your portfolio",
                    message=(
                        f"Your {asset_type_display} holdings ({type_total:,.0f}) "
                        f"make up {pct:.1f}% of your total portfolio ({total_value:,.0f}). "
                        f"High concentration in a single asset type increases risk."
                    ),
                    suggested_action=(
                        "Consider diversifying across different asset types "
                        "to reduce concentration risk."
                    ),
                ))
        return results

    # ──────────────────────────────────────────────────────────────────────
    # Source C: Finnhub API (optional)
    # ──────────────────────────────────────────────────────────────────────

    def _get_finnhub_api_key(self) -> Optional[str]:
        """Read Finnhub API key from DB settings or env var."""
        try:
            db = SessionLocal()
            try:
                from app.models.app_settings import AppSettings
                row = db.query(AppSettings).filter(AppSettings.key == "finnhub_api_key").first()
                if row and row.value:
                    return row.value
            finally:
                db.close()
        except Exception:
            pass
        return getattr(settings, "FINNHUB_API_KEY", None)

    async def _fetch_finnhub_alerts(
        self, db: Session, user_id: int, api_key: str
    ) -> List[FreeAlertResult]:
        """Fetch news from Finnhub free tier for portfolio stocks."""
        results: List[FreeAlertResult] = []

        # Company news for user's stocks (limit to 10 to respect rate limits)
        stocks = db.query(Asset).filter(
            Asset.user_id == user_id,
            Asset.is_active == True,
            Asset.asset_type.in_([AssetType.STOCK, AssetType.US_STOCK]),
            Asset.symbol != None,
        ).order_by(Asset.current_value.desc()).limit(10).all()

        for asset in stocks:
            symbol = (asset.api_symbol or asset.symbol or "").upper()
            if not symbol:
                continue
            news_items = await self._finnhub_company_news(api_key, symbol)
            if news_items:
                top = news_items[0]
                results.append(FreeAlertResult(
                    source="finnhub",
                    alert_type=AlertType.NEWS_EVENT,
                    severity=AlertSeverity.INFO,
                    title=top.get("headline", "No headline")[:100],
                    message=top.get("summary", "")[:500] or top.get("headline", ""),
                    action_url=top.get("url"),
                    asset_id=asset.id,
                ))
            await asyncio.sleep(1.1)  # Rate limit: 60 calls/min

        # General market news
        general_items = await self._finnhub_general_news(api_key, "general")
        for item in general_items[:3]:
            results.append(FreeAlertResult(
                source="finnhub",
                alert_type=AlertType.NEWS_EVENT,
                severity=AlertSeverity.INFO,
                title=item.get("headline", "No headline")[:100],
                message=item.get("summary", "")[:500] or item.get("headline", ""),
                action_url=item.get("url"),
            ))

        # Crypto market news (if user has crypto)
        has_crypto = db.query(Asset).filter(
            Asset.user_id == user_id,
            Asset.is_active == True,
            Asset.asset_type == AssetType.CRYPTO,
        ).first()

        if has_crypto:
            crypto_items = await self._finnhub_general_news(api_key, "crypto")
            for item in crypto_items[:2]:
                results.append(FreeAlertResult(
                    source="finnhub",
                    alert_type=AlertType.NEWS_EVENT,
                    severity=AlertSeverity.INFO,
                    title=item.get("headline", "No headline")[:100],
                    message=item.get("summary", "")[:500] or item.get("headline", ""),
                    action_url=item.get("url"),
                ))

        return results

    async def _finnhub_company_news(self, api_key: str, symbol: str) -> list:
        """Fetch company-specific news from Finnhub."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
        url = (
            f"https://finnhub.io/api/v1/company-news"
            f"?symbol={symbol}&from={week_ago}&to={today}&token={api_key}"
        )
        try:
            async with httpx.AsyncClient(timeout=self.HTTP_TIMEOUT) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return resp.json()[:5]
                logger.warning(f"Finnhub company news for {symbol}: HTTP {resp.status_code}")
        except Exception as exc:
            logger.warning(f"Finnhub company news for {symbol} failed: {exc}")
        return []

    async def _finnhub_general_news(self, api_key: str, category: str = "general") -> list:
        """Fetch general market news from Finnhub."""
        url = f"https://finnhub.io/api/v1/news?category={category}&token={api_key}"
        try:
            async with httpx.AsyncClient(timeout=self.HTTP_TIMEOUT) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return resp.json()[:5]
                logger.warning(f"Finnhub general news ({category}): HTTP {resp.status_code}")
        except Exception as exc:
            logger.warning(f"Finnhub general news ({category}) failed: {exc}")
        return []


# Singleton instance
free_news_service = FreeNewsService()
