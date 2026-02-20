"""
AI-powered news and alert service for portfolio assets.
Supports both Grok (xAI) and OpenAI ChatGPT APIs.
"""
import httpx
import json
import asyncio
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from loguru import logger

from app.core.config import settings
from app.models.asset import Asset, AssetType
from app.models.alert import Alert, AlertType, AlertSeverity
from app.services.news_progress_tracker import progress_tracker


class AINewsService:
    """Service to fetch AI-powered news and insights for portfolio assets."""

    def __init__(self):
        self.openai_api_key = settings.OPENAI_API_KEY
        self.grok_api_key = settings.GROK_API_KEY
        self.ai_provider = settings.AI_NEWS_PROVIDER.lower()

        # API endpoints from config (overridable for proxies / staging)
        self.openai_endpoint = settings.OPENAI_API_ENDPOINT
        self.grok_endpoint = settings.GROK_API_ENDPOINT

        # Model selection from config
        self.openai_model = settings.OPENAI_MODEL
        self.grok_model = settings.GROK_MODEL

        # Request tuning from config
        self.timeout = settings.AI_REQUEST_TIMEOUT
        self.request_delay = settings.AI_REQUEST_DELAY
        self.max_retries = settings.AI_MAX_RETRIES
        self.retry_delay = settings.AI_RETRY_DELAY
        self.max_tokens = settings.AI_MAX_TOKENS
        self.temperature = settings.AI_TEMPERATURE

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def fetch_asset_news(
        self,
        db: Session,
        user_id: int,
        asset: Asset,
    ) -> Optional[Dict]:
        """
        Fetch relevant news and insights for a specific asset using AI.

        Returns a structured dictionary with news data, or None if there is
        no significant news or the AI call fails.
        """
        try:
            prompt = self._build_news_prompt(asset)
            response = await self._query_ai(prompt)
            if not response:
                return None
            return self._parse_ai_response(response, asset)
        except Exception as exc:
            logger.error(f"Error fetching news for asset '{asset.name}': {exc}")
            return None

    async def create_alert_from_news(
        self,
        db: Session,
        user_id: int,
        news_data: Dict,
    ) -> Optional[Alert]:
        """Create an Alert row from structured AI news data."""
        try:
            category_map = {
                "news_event": AlertType.NEWS_EVENT,
                "regulatory_change": AlertType.REGULATORY_CHANGE,
                "earnings_report": AlertType.EARNINGS_REPORT,
                "dividend_announcement": AlertType.DIVIDEND_ANNOUNCEMENT,
                "market_volatility": AlertType.MARKET_VOLATILITY,
            }
            severity_map = {
                "info": AlertSeverity.INFO,
                "warning": AlertSeverity.WARNING,
                "critical": AlertSeverity.CRITICAL,
            }

            alert_type = category_map.get(
                news_data.get("category", "news_event"),
                AlertType.NEWS_EVENT,
            )
            severity = severity_map.get(
                news_data.get("severity", "info"),
                AlertSeverity.INFO,
            )

            message_parts = [news_data.get("summary", "")]
            impact = news_data.get("impact")
            if impact:
                message_parts.append(f"\n\nImpact: {impact}")

            alert = Alert(
                user_id=user_id,
                asset_id=news_data.get("asset_id"),
                alert_type=alert_type,
                severity=severity,
                title=news_data.get("title", "Asset Update"),
                message="".join(message_parts),
                suggested_action=news_data.get("suggested_action"),
                is_actionable=True,
            )

            db.add(alert)
            db.commit()
            db.refresh(alert)

            logger.info(
                f"Created alert for user {user_id}, asset '{news_data.get('asset_name')}'"
            )
            return alert

        except Exception as exc:
            logger.error(f"Error creating alert from news data: {exc}")
            db.rollback()
            return None

    async def process_user_portfolio(
        self,
        db: Session,
        user_id: int,
        limit: Optional[int] = None,
        session_id: Optional[str] = None,
    ) -> Tuple[int, int, str]:
        """
        Process all eligible assets in a user's portfolio and create alerts
        for significant news findings.

        Returns:
            Tuple of (assets_processed, alerts_created, session_id)
        """
        try:
            query = (
                db.query(Asset)
                .filter(
                    Asset.user_id == user_id,
                    Asset.is_active == True,
                    Asset.asset_type.in_([
                        AssetType.STOCK,
                        AssetType.US_STOCK,
                        AssetType.CRYPTO,
                    ]),
                )
                .order_by(Asset.current_value.desc())
            )

            if limit:
                query = query.limit(limit)

            assets = query.all()

            if not session_id:
                session_id = progress_tracker.create_session(user_id, assets)

            assets_processed = 0
            alerts_created = 0

            for asset in assets:
                if progress_tracker.is_cancelled(session_id):
                    logger.info(f"Session {session_id} cancelled by user.")
                    break

                try:
                    progress_tracker.update_asset_status(session_id, asset.id, "processing")

                    if assets_processed > 0:
                        logger.debug(
                            f"Waiting {self.request_delay}s before next AI request…"
                        )
                        await asyncio.sleep(self.request_delay)

                    news_data = await self.fetch_asset_news(db, user_id, asset)

                    if news_data:
                        alert = await self.create_alert_from_news(db, user_id, news_data)
                        if alert:
                            alerts_created += 1
                            progress_tracker.update_asset_status(
                                session_id, asset.id, "completed",
                                alert_created=True, alert_message=alert.title,
                            )
                        else:
                            progress_tracker.update_asset_status(
                                session_id, asset.id, "completed",
                                alert_created=False, alert_message="Processed. No alerts",
                            )
                    else:
                        progress_tracker.update_asset_status(
                            session_id, asset.id, "completed",
                            alert_created=False, alert_message="Processed. No alerts",
                        )

                    assets_processed += 1

                except Exception as exc:
                    logger.error(f"Error processing asset '{asset.name}': {exc}")
                    progress_tracker.update_asset_status(
                        session_id, asset.id, "error", error_message=str(exc)
                    )
                    assets_processed += 1

            progress_tracker.complete_session(session_id)
            logger.info(
                f"Portfolio processing complete for user {user_id}: "
                f"{assets_processed} assets processed, {alerts_created} alerts created."
            )
            return assets_processed, alerts_created, session_id

        except Exception as exc:
            logger.error(f"Fatal error processing portfolio for user {user_id}: {exc}")
            if session_id:
                progress_tracker.fail_session(session_id)
            return 0, 0, session_id or ""

    async def fetch_generic_india_news(
        self,
        db: Session,
        user_id: int,
    ) -> List[Dict]:
        """
        Fetch generic news for broad Indian investment categories
        (PPF, EPF, Gold, Silver, Crypto regulations).

        Returns a list of news data dictionaries for items with significant news.
        """
        topics = [
            "Public Provident Fund (PPF) India",
            "Employee Provident Fund (EPF) India",
            "Gold investment India",
            "Silver investment India",
            "Cryptocurrency regulations India",
        ]

        news_results: List[Dict] = []

        for topic in topics:
            try:
                prompt = self._build_generic_topic_prompt(topic)
                response = await self._query_ai(prompt)

                if response:
                    data = self._strip_markdown_json(response)
                    if data and data.get("has_significant_news", False):
                        data["topic"] = topic
                        data["asset_name"] = topic
                        news_results.append(data)

                await asyncio.sleep(self.request_delay)

            except Exception as exc:
                logger.error(f"Error fetching generic news for '{topic}': {exc}")
                continue

        return news_results

    async def process_generic_india_news(
        self,
        db: Session,
        user_id: int,
    ) -> int:
        """
        Fetch and persist generic India investment news alerts.

        Returns the number of alerts created.
        """
        try:
            news_results = await self.fetch_generic_india_news(db, user_id)
            alerts_created = 0

            for news_data in news_results:
                alert = await self.create_alert_from_news(db, user_id, news_data)
                if alert:
                    alerts_created += 1

            logger.info(
                f"Created {alerts_created} generic India news alerts for user {user_id}."
            )
            return alerts_created

        except Exception as exc:
            logger.error(f"Error processing generic India news for user {user_id}: {exc}")
            return 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _query_ai(self, prompt: str) -> Optional[str]:
        """Route the prompt to the configured AI provider."""
        if self.ai_provider == "grok" and self.grok_api_key:
            return await self._query_provider(
                endpoint=self.grok_endpoint,
                api_key=self.grok_api_key,
                model=self.grok_model,
                prompt=prompt,
                provider_name="Grok",
            )
        if self.openai_api_key:
            return await self._query_provider(
                endpoint=self.openai_endpoint,
                api_key=self.openai_api_key,
                model=self.openai_model,
                prompt=prompt,
                provider_name="OpenAI",
            )
        logger.warning("No AI API key configured. Cannot fetch news.")
        return None

    async def _query_provider(
        self,
        *,
        endpoint: str,
        api_key: str,
        model: str,
        prompt: str,
        provider_name: str,
    ) -> Optional[str]:
        """Generic AI API caller with retry logic."""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a financial analyst providing concise, "
                        "actionable investment insights."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(endpoint, headers=headers, json=payload)

                if response.status_code == 200:
                    return response.json()["choices"][0]["message"]["content"]

                if response.status_code == 429:
                    if attempt < self.max_retries:
                        wait = self.retry_delay * attempt
                        logger.warning(
                            f"{provider_name} rate-limited. "
                            f"Retrying in {wait}s (attempt {attempt}/{self.max_retries})."
                        )
                        await asyncio.sleep(wait)
                        continue
                    logger.error(f"{provider_name} rate limit exceeded after all retries.")
                    return None

                logger.error(
                    f"{provider_name} API error {response.status_code}: {response.text}"
                )
                return None

            except httpx.TimeoutException:
                logger.warning(
                    f"{provider_name} request timed out "
                    f"(attempt {attempt}/{self.max_retries})."
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * attempt)
                    continue
                return None

            except Exception as exc:
                logger.error(
                    f"{provider_name} unexpected error "
                    f"(attempt {attempt}/{self.max_retries}): {exc}"
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * attempt)
                    continue
                return None

        return None

    def _strip_markdown_json(self, raw: str) -> Optional[Dict]:
        """Strip markdown fences and parse JSON. Returns None on failure."""
        try:
            text = raw.strip()
            if text.startswith("```json"):
                text = text[7:]
            elif text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            return json.loads(text.strip())
        except json.JSONDecodeError as exc:
            logger.error(f"Failed to parse AI response as JSON: {exc}")
            logger.debug(f"Raw AI response: {raw}")
            return None
        except Exception as exc:
            logger.error(f"Unexpected error parsing AI response: {exc}")
            return None

    def _parse_ai_response(self, response: str, asset: Asset) -> Optional[Dict]:
        """Parse and enrich AI response with asset metadata."""
        data = self._strip_markdown_json(response)
        if data is None:
            return None
        if not data.get("has_significant_news", False):
            return None

        data["asset_id"] = asset.id
        data["asset_name"] = asset.name
        data["asset_symbol"] = asset.symbol
        data["asset_type"] = asset.asset_type.value
        return data

    def _build_news_prompt(self, asset: Asset) -> str:
        asset_info = asset.name
        if asset.symbol:
            asset_info += f" ({asset.symbol})"

        current_price = f"₹{asset.current_price}" if asset.current_price else "N/A"

        return f"""You are a financial analyst assistant. Analyse the following asset and report ONLY the most significant, actionable news from the last 7 days.

Asset: {asset_info}
Type: {asset.asset_type.value}
Current Price: {current_price}

Focus areas:
1. Major announcements (mergers, acquisitions, regulatory actions)
2. Policy / regulatory changes with direct financial impact
3. Earnings surprises, dividend announcements
4. Significant market movements or sector trends
5. Credit rating changes, fraud alerts, or material risks

Rules:
- Only report information from the last 7 days.
- Ignore minor price moves or routine updates.
- If there is NO significant news respond with {{"has_significant_news": false}}.

Response format (strict JSON, no markdown):
{{
    "has_significant_news": true,
    "severity": "info|warning|critical",
    "title": "<max 100 chars>",
    "summary": "<max 500 chars>",
    "impact": "<how this affects the investment>",
    "suggested_action": "<what the investor should consider>",
    "source_date": "YYYY-MM-DD",
    "category": "news_event|regulatory_change|earnings_report|dividend_announcement|market_volatility"
}}"""

    def _build_generic_topic_prompt(self, topic: str) -> str:
        return f"""You are a financial analyst assistant. Report the most impactful information about '{topic}' from the last 7 days.

Focus areas:
1. Policy or regulatory changes with direct investor impact
2. Interest rate changes (for PPF/EPF)
3. Significant price movements or market shifts (for Gold/Silver/Crypto)
4. New rules, compliance requirements, or legal changes
5. New schemes, benefits, or important updates

Rules:
- Only report information from the last 7 days.
- If there is NO significant news respond with {{"has_significant_news": false}}.

Response format (strict JSON, no markdown):
{{
    "has_significant_news": true,
    "severity": "info|warning|critical",
    "title": "<max 100 chars>",
    "summary": "<max 500 chars>",
    "impact": "<how this affects investors>",
    "suggested_action": "<what investors should consider>",
    "source_date": "YYYY-MM-DD",
    "category": "regulatory_change|news_event|market_volatility"
}}"""


# Singleton instance
ai_news_service = AINewsService()
