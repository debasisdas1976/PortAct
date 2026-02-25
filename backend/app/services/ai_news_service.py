"""
AI-powered news and alert service for portfolio assets.
Supports OpenAI, Grok (xAI), Google Gemini, Anthropic Claude, DeepSeek, and Mistral.
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

    # Provider registry: maps provider name to its DB setting keys, env var names, and API format
    PROVIDERS = {
        "openai": {
            "key_setting": "ai_openai_api_key",
            "key_env": "OPENAI_API_KEY",
            "endpoint_setting": "ai_openai_endpoint",
            "endpoint_env": "OPENAI_API_ENDPOINT",
            "model_setting": "ai_openai_model",
            "model_env": "OPENAI_MODEL",
            "api_format": "openai_compatible",
            "display_name": "OpenAI",
        },
        "grok": {
            "key_setting": "ai_grok_api_key",
            "key_env": "GROK_API_KEY",
            "endpoint_setting": "ai_grok_endpoint",
            "endpoint_env": "GROK_API_ENDPOINT",
            "model_setting": "ai_grok_model",
            "model_env": "GROK_MODEL",
            "api_format": "openai_compatible",
            "display_name": "Grok",
        },
        "gemini": {
            "key_setting": "ai_gemini_api_key",
            "key_env": "GEMINI_API_KEY",
            "endpoint_setting": "ai_gemini_endpoint",
            "endpoint_env": "GEMINI_API_ENDPOINT",
            "model_setting": "ai_gemini_model",
            "model_env": "GEMINI_MODEL",
            "api_format": "openai_compatible",
            "display_name": "Gemini",
        },
        "anthropic": {
            "key_setting": "ai_anthropic_api_key",
            "key_env": "ANTHROPIC_API_KEY",
            "endpoint_setting": "ai_anthropic_endpoint",
            "endpoint_env": "ANTHROPIC_API_ENDPOINT",
            "model_setting": "ai_anthropic_model",
            "model_env": "ANTHROPIC_MODEL",
            "api_format": "anthropic",
            "display_name": "Anthropic",
        },
        "deepseek": {
            "key_setting": "ai_deepseek_api_key",
            "key_env": "DEEPSEEK_API_KEY",
            "endpoint_setting": "ai_deepseek_endpoint",
            "endpoint_env": "DEEPSEEK_API_ENDPOINT",
            "model_setting": "ai_deepseek_model",
            "model_env": "DEEPSEEK_MODEL",
            "api_format": "openai_compatible",
            "display_name": "DeepSeek",
        },
        "mistral": {
            "key_setting": "ai_mistral_api_key",
            "key_env": "MISTRAL_API_KEY",
            "endpoint_setting": "ai_mistral_endpoint",
            "endpoint_env": "MISTRAL_API_ENDPOINT",
            "model_setting": "ai_mistral_model",
            "model_env": "MISTRAL_MODEL",
            "api_format": "openai_compatible",
            "display_name": "Mistral",
        },
    }

    SYSTEM_PROMPT = (
        "You are a knowledgeable financial analyst specializing in "
        "Indian markets and investments. You ALWAYS provide useful, "
        "specific insights about any asset or investment topic. "
        "Never say there is nothing to report — every investment "
        "has risks, opportunities, or considerations worth highlighting. "
        "Respond with valid JSON only, no markdown formatting."
    )

    def __init__(self):
        # Request tuning (operational params, not provider-specific)
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
                        AssetType.EQUITY_MUTUAL_FUND,
                        AssetType.DEBT_MUTUAL_FUND,
                        AssetType.COMMODITY,
                        AssetType.SOVEREIGN_GOLD_BOND,
                        AssetType.REIT,
                        AssetType.INVIT,
                        AssetType.CORPORATE_BOND,
                        AssetType.RBI_BOND,
                        AssetType.TAX_SAVING_BOND,
                        AssetType.PPF,
                        AssetType.PF,
                        AssetType.NPS,
                        AssetType.SSY,
                        AssetType.NSC,
                        AssetType.KVP,
                        AssetType.SCSS,
                        AssetType.MIS,
                        AssetType.FIXED_DEPOSIT,
                        AssetType.RECURRING_DEPOSIT,
                        AssetType.INSURANCE_POLICY,
                        AssetType.REAL_ESTATE,
                    ]),
                )
                .order_by(Asset.current_value.desc())
            )

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
            "Indian stock market outlook — Nifty 50 and Sensex trends",
            "RBI monetary policy and interest rate outlook for Indian investors",
            "Indian mutual fund industry — SIP trends and regulatory changes",
            "Gold and Silver investment outlook for Indian investors",
            "Indian real estate market — RERA updates and price trends",
            "NPS (National Pension System) India — returns and regulatory updates",
            "Indian government bonds and small savings schemes rate changes",
            "Cryptocurrency regulations and taxation in India",
            "Indian insurance sector — IRDAI regulatory changes",
            "Income tax changes affecting Indian investors — capital gains and deductions",
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
    # Provider configuration
    # ------------------------------------------------------------------

    def _get_provider_config(self) -> dict:
        """
        Resolve the active provider's API key, endpoint, and model.
        Priority: DB setting > env var > None.

        Returns:
            {"provider": str, "api_key": str, "endpoint": str,
             "model": str, "api_format": str, "display_name": str}
        """
        from app.core.database import SessionLocal
        from app.models.app_settings import AppSettings

        db = SessionLocal()
        try:
            ai_rows = db.query(AppSettings).filter(AppSettings.category == "ai").all()
            db_settings = {row.key: row.value for row in ai_rows}
        finally:
            db.close()

        provider = (db_settings.get("ai_news_provider") or settings.AI_NEWS_PROVIDER).lower()

        if provider not in self.PROVIDERS:
            logger.warning(f"Unknown AI provider '{provider}', falling back to openai.")
            provider = "openai"

        prov_conf = self.PROVIDERS[provider]

        # Resolve: DB value > env var fallback
        api_key = (
            db_settings.get(prov_conf["key_setting"])
            or getattr(settings, prov_conf["key_env"], None)
        )
        endpoint = (
            db_settings.get(prov_conf["endpoint_setting"])
            or getattr(settings, prov_conf["endpoint_env"], "")
        )
        model = (
            db_settings.get(prov_conf["model_setting"])
            or getattr(settings, prov_conf["model_env"], "")
        )

        return {
            "provider": provider,
            "api_key": api_key,
            "endpoint": endpoint,
            "model": model,
            "api_format": prov_conf["api_format"],
            "display_name": prov_conf["display_name"],
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _query_ai(self, prompt: str) -> Optional[str]:
        """Route the prompt to the currently configured AI provider."""
        config = self._get_provider_config()

        if not config["api_key"]:
            logger.warning(
                f"No API key configured for provider '{config['display_name']}'. "
                "Cannot fetch news."
            )
            return None

        if config["api_format"] == "anthropic":
            return await self._query_anthropic(
                endpoint=config["endpoint"],
                api_key=config["api_key"],
                model=config["model"],
                prompt=prompt,
            )
        else:
            return await self._query_provider(
                endpoint=config["endpoint"],
                api_key=config["api_key"],
                model=config["model"],
                prompt=prompt,
                provider_name=config["display_name"],
            )

    async def _query_provider(
        self,
        *,
        endpoint: str,
        api_key: str,
        model: str,
        prompt: str,
        provider_name: str,
    ) -> Optional[str]:
        """Generic OpenAI-compatible API caller with retry logic."""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": self.SYSTEM_PROMPT,
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
                    # Check if this is a permanent quota issue vs temporary rate limit
                    try:
                        error_body = response.json()
                        error_code = error_body.get("error", {}).get("code", "")
                    except Exception:
                        error_code = ""

                    if error_code == "insufficient_quota":
                        logger.error(
                            f"{provider_name} API quota exhausted. "
                            f"Please add billing credits or switch AI provider."
                        )
                        return None

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

    async def _query_anthropic(
        self,
        *,
        endpoint: str,
        api_key: str,
        model: str,
        prompt: str,
    ) -> Optional[str]:
        """Anthropic Messages API caller with retry logic."""
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "max_tokens": self.max_tokens,
            "system": self.SYSTEM_PROMPT,
            "messages": [
                {"role": "user", "content": prompt},
            ],
            "temperature": self.temperature,
        }

        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(endpoint, headers=headers, json=payload)

                if response.status_code == 200:
                    resp_data = response.json()
                    content_blocks = resp_data.get("content", [])
                    text_parts = [b["text"] for b in content_blocks if b.get("type") == "text"]
                    return "".join(text_parts)

                if response.status_code == 429:
                    if attempt < self.max_retries:
                        wait = self.retry_delay * attempt
                        logger.warning(
                            f"Anthropic rate-limited. "
                            f"Retrying in {wait}s (attempt {attempt}/{self.max_retries})."
                        )
                        await asyncio.sleep(wait)
                        continue
                    logger.error("Anthropic rate limit exceeded after all retries.")
                    return None

                logger.error(
                    f"Anthropic API error {response.status_code}: {response.text}"
                )
                return None

            except httpx.TimeoutException:
                logger.warning(
                    f"Anthropic request timed out "
                    f"(attempt {attempt}/{self.max_retries})."
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * attempt)
                    continue
                return None

            except Exception as exc:
                logger.error(
                    f"Anthropic unexpected error "
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
        asset_type = asset.asset_type.value

        # Market-traded assets get a different focus than fixed-income / govt schemes
        if asset_type in ("stock", "us_stock", "equity_mutual_fund", "hybrid_mutual_fund", "reit", "invit", "esop", "rsu"):
            focus = """Focus areas:
1. Key risks, red flags, or concerns investors should be aware of for this specific asset
2. Known corporate governance issues, debt levels, or sector headwinds
3. Competitive landscape and market position analysis
4. Upcoming catalysts: earnings seasons, regulatory decisions, or sector trends
5. Dividend history and payout sustainability
6. Any well-known analyst consensus or outlook (bullish/bearish)"""
        elif asset_type in ("crypto",):
            focus = """Focus areas:
1. Regulatory landscape for this cryptocurrency in India and globally
2. Technology risks, network upgrades, or protocol changes
3. Market sentiment and adoption trends
4. Security concerns, exchange risks, or known vulnerabilities
5. Tax implications for Indian crypto investors"""
        elif asset_type in ("commodity", "sovereign_gold_bond"):
            focus = """Focus areas:
1. Supply-demand dynamics and global price drivers
2. Indian government policies affecting this commodity (import duties, taxes)
3. Inflation hedge value and historical performance patterns
4. Seasonal trends and cyclical factors
5. Currency impact (USD/INR) on commodity prices in India"""
        elif asset_type in ("debt_mutual_fund", "corporate_bond", "rbi_bond", "tax_saving_bond"):
            focus = """Focus areas:
1. Interest rate outlook and its impact on bond/debt fund returns
2. Credit risk assessment and rating agency concerns
3. RBI monetary policy direction and yield curve analysis
4. Liquidity risk and exit load considerations
5. Tax efficiency compared to alternatives (FD, govt schemes)"""
        elif asset_type in ("ppf", "pf", "nps", "ssy", "nsc", "kvp", "scss", "mis"):
            focus = """Focus areas:
1. Current and recent interest rate changes for this scheme
2. Government policy changes or proposed reforms
3. Tax benefit analysis under current tax regime (old vs new)
4. Contribution limits, lock-in periods, and withdrawal rules
5. Comparison with alternative investment options
6. Any maturity or renewal considerations"""
        elif asset_type in ("fixed_deposit", "recurring_deposit"):
            focus = """Focus areas:
1. Current interest rate environment and RBI rate outlook
2. Comparison of rates across major banks
3. Tax implications and TDS rules
4. Premature withdrawal penalties and liquidity options
5. Senior citizen rate benefits and special FD schemes"""
        elif asset_type in ("insurance_policy",):
            focus = """Focus areas:
1. Policy type analysis (term, endowment, ULIP) and adequacy
2. Claim settlement ratio of the insurer
3. IRDAI regulatory changes affecting policyholders
4. Tax benefits under Section 80C and 10(10D)
5. Surrender value considerations and policy review recommendations"""
        elif asset_type in ("real_estate",):
            focus = """Focus areas:
1. Real estate market trends in India — residential and commercial
2. RERA regulations and buyer protection updates
3. Home loan interest rate trends
4. Capital gains tax rules and indexation benefits
5. Rental yield analysis and vacancy trends"""
        else:
            focus = """Focus areas:
1. Key risks and opportunities for this investment
2. Regulatory or policy changes that may affect returns
3. Market conditions and outlook
4. Tax implications for Indian investors
5. Actionable recommendations"""

        return f"""You are a financial analyst providing investment insights for an Indian investor's portfolio.

Analyse the following asset and provide ONE important insight, risk alert, or actionable recommendation.

Asset: {asset_info}
Type: {asset_type}
Current Price: {current_price}

{focus}

IMPORTANT RULES:
- You MUST always provide an insight. Every asset has something worth knowing.
- Provide analysis based on your knowledge of this asset, its sector, and market conditions.
- Focus on actionable, practical advice the investor can use.
- Be specific to THIS asset, not generic platitudes.
- Set has_significant_news to true.

Response format (strict JSON, no markdown):
{{
    "has_significant_news": true,
    "severity": "info|warning|critical",
    "title": "<concise headline, max 100 chars>",
    "summary": "<detailed insight with specific data points, max 500 chars>",
    "impact": "<how this affects the investor's portfolio>",
    "suggested_action": "<specific action the investor should consider>",
    "category": "news_event|regulatory_change|earnings_report|dividend_announcement|market_volatility"
}}"""

    def _build_generic_topic_prompt(self, topic: str) -> str:
        return f"""You are a financial analyst providing investment insights for Indian investors.

Provide ONE important insight or update about: '{topic}'

Focus areas:
1. Current market conditions, trends, and outlook
2. Policy or regulatory changes with direct investor impact
3. Interest rate environment and its implications
4. Key risks investors should be aware of
5. Actionable recommendations for portfolio management

IMPORTANT RULES:
- You MUST provide an insight. This topic is always relevant to Indian investors.
- Be specific and data-driven where possible.
- Focus on practical, actionable advice.
- Set has_significant_news to true.

Response format (strict JSON, no markdown):
{{
    "has_significant_news": true,
    "severity": "info|warning|critical",
    "title": "<concise headline, max 100 chars>",
    "summary": "<detailed insight, max 500 chars>",
    "impact": "<how this affects Indian investors>",
    "suggested_action": "<specific action investors should consider>",
    "category": "regulatory_change|news_event|market_volatility"
}}"""


# Singleton instance
ai_news_service = AINewsService()
