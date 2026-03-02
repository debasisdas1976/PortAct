"""
AI-powered news and alert service for portfolio assets.
Supports OpenAI, Grok (xAI), Google Gemini, Anthropic Claude, DeepSeek, and Mistral.
"""
import httpx
import json
import asyncio
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from loguru import logger

from app.core.config import settings
from app.models.asset import Asset, AssetType
from app.models.alert import Alert, AlertType, AlertSeverity
from app.services.news_progress_tracker import progress_tracker


@dataclass
class AIResult:
    """Structured result from an AI query — carries either content or error details."""
    success: bool
    content: Optional[str] = None
    error: Optional[str] = None          # human-readable error message
    error_type: Optional[str] = None     # "no_api_key", "rate_limit", "quota_exhausted", "timeout", "api_error"
    provider: Optional[str] = None       # e.g. "OpenAI", "Gemini"
    model: Optional[str] = None          # e.g. "gpt-3.5-turbo"
    fatal: bool = False                  # True → stop processing all remaining assets


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
        "Respond with valid JSON only, no markdown formatting."
    )

    # Only market-driven asset types get per-asset alerts.
    # Fixed-value assets (PPF, FD, land, etc.) are covered by generic sector alerts.
    ALERTABLE_ASSET_TYPES = [
        AssetType.STOCK,
        AssetType.US_STOCK,
        AssetType.EQUITY_MUTUAL_FUND,
        AssetType.HYBRID_MUTUAL_FUND,
        AssetType.DEBT_MUTUAL_FUND,
        AssetType.COMMODITY,
        AssetType.CRYPTO,
        AssetType.SOVEREIGN_GOLD_BOND,
        AssetType.REIT,
        AssetType.INVIT,
        AssetType.ESOP,
        AssetType.RSU,
    ]

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

    def get_provider_config(self) -> dict:
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

    async def fetch_asset_news(
        self,
        db: Session,
        user_id: int,
        asset: Asset,
    ) -> Tuple[Optional[Dict], Optional[AIResult]]:
        """
        Fetch relevant news and insights for a specific asset using AI.

        Returns:
            (news_data, None) on success
            (None, AIResult) on error — AIResult carries error details
        """
        try:
            prompt = self._build_news_prompt(asset)
            result = await self._query_ai(prompt)

            if not result.success:
                return None, result

            parsed = self._parse_ai_response(result.content, asset)
            if parsed is None:
                # JSON parse failed but AI call succeeded — not fatal
                return None, AIResult(
                    success=False,
                    error="Failed to parse AI response as valid JSON",
                    error_type="parse_error",
                    provider=result.provider,
                    model=result.model,
                    fatal=False,
                )
            return parsed, None

        except Exception as exc:
            logger.error(f"Error fetching news for asset '{asset.name}': {exc}")
            return None, AIResult(
                success=False,
                error=str(exc),
                error_type="api_error",
                fatal=False,
            )

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
                "price_change": AlertType.PRICE_CHANGE,
                "rebalance_suggestion": AlertType.REBALANCE_SUGGESTION,
                "maturity_reminder": AlertType.MATURITY_REMINDER,
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
        Process all eligible market-driven assets in a user's portfolio
        and create alerts for AI-generated insights.

        Returns:
            Tuple of (assets_processed, alerts_created, session_id)
        """
        try:
            query = (
                db.query(Asset)
                .filter(
                    Asset.user_id == user_id,
                    Asset.is_active == True,
                    Asset.asset_type.in_(self.ALERTABLE_ASSET_TYPES),
                )
                .order_by(Asset.current_value.desc())
            )

            assets = query.all()

            if not session_id:
                config = self.get_provider_config()
                session_id = progress_tracker.create_session(
                    user_id, assets,
                    provider=config.get("display_name"),
                    model=config.get("model"),
                )

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

                    news_data, error_result = await self.fetch_asset_news(db, user_id, asset)

                    if error_result:
                        if error_result.fatal:
                            # Fatal error — stop processing all remaining assets
                            error_msg = (
                                f"{error_result.provider or 'AI'}"
                                f" ({error_result.model or 'unknown'})"
                                f" — {error_result.error}"
                            )
                            logger.error(
                                f"Fatal AI error for session {session_id}: {error_msg}"
                            )
                            progress_tracker.update_asset_status(
                                session_id, asset.id, "error",
                                error_message=error_result.error,
                            )
                            assets_processed += 1
                            progress_tracker.fail_session(session_id, error_detail=error_msg)
                            return assets_processed, alerts_created, session_id

                        # Non-fatal error — mark asset as error, continue
                        progress_tracker.update_asset_status(
                            session_id, asset.id, "error",
                            error_message=error_result.error,
                        )
                        assets_processed += 1

                        # After rate limit, add extra cooldown before next request
                        if error_result.error_type == "rate_limit":
                            logger.info("Rate-limited — cooling down 30s before next asset.")
                            await asyncio.sleep(30.0)

                        continue

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
                progress_tracker.fail_session(session_id, error_detail=str(exc))
            return 0, 0, session_id or ""

    async def fetch_generic_india_news(
        self,
        db: Session,
        user_id: int,
    ) -> List[Dict]:
        """
        Fetch generic news for broad Indian investment categories
        covering sectors not handled by per-asset alerts
        (government schemes, fixed income, real estate, policy changes).

        Returns a list of news data dictionaries.
        """
        topics = [
            "Indian stock market outlook — Nifty 50 and Sensex trends, FII/DII flows",
            "RBI monetary policy and repo rate outlook for Indian investors",
            "Indian mutual fund industry — SIP trends, SEBI regulatory changes, NFO launches",
            "Gold and Silver investment outlook for Indian investors — prices, duties, demand",
            "EPF and PPF interest rate changes — government announcements, contribution limits",
            "NPS (National Pension System) India — fund performance, tier changes, tax benefits",
            "Fixed deposit and recurring deposit rate changes across major Indian banks",
            "Small savings schemes (NSC, KVP, SCSS, MIS, SSY) — quarterly rate revisions and policy updates",
            "Indian real estate market — RERA updates, stamp duty changes, home loan rate trends",
            "Cryptocurrency regulations and taxation in India — RBI, SEBI, and Finance Ministry updates",
            "Indian insurance sector — IRDAI regulatory changes, claim settlement updates",
            "Union Budget and fiscal policy changes affecting Indian investors — capital gains, deductions, surcharges",
        ]

        news_results: List[Dict] = []

        for topic in topics:
            try:
                prompt = self._build_generic_topic_prompt(topic)
                result = await self._query_ai(prompt)

                if result.success and result.content:
                    data = self._strip_markdown_json(result.content)
                    if data and data.get("title") and data.get("summary"):
                        data["topic"] = topic
                        data["asset_name"] = topic
                        news_results.append(data)
                elif result.fatal:
                    logger.error(
                        f"Fatal AI error during generic news: "
                        f"{result.provider} ({result.model}) — {result.error}"
                    )
                    break

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

    async def _query_ai(self, prompt: str) -> AIResult:
        """Route the prompt to the currently configured AI provider."""
        config = self.get_provider_config()

        if not config["api_key"]:
            return AIResult(
                success=False,
                error=f"No API key configured for {config['display_name']}. "
                      f"Set it in Settings → AI Configuration.",
                error_type="no_api_key",
                provider=config["display_name"],
                model=config["model"],
                fatal=True,
            )

        if config["api_format"] == "anthropic":
            return await self._query_anthropic(
                endpoint=config["endpoint"],
                api_key=config["api_key"],
                model=config["model"],
                prompt=prompt,
                provider_name=config["display_name"],
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
    ) -> AIResult:
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
                    return AIResult(
                        success=True,
                        content=response.json()["choices"][0]["message"]["content"],
                        provider=provider_name,
                        model=model,
                    )

                if response.status_code == 401:
                    return AIResult(
                        success=False,
                        error=f"Invalid API key for {provider_name}. Check your key in Settings → AI Configuration.",
                        error_type="api_error",
                        provider=provider_name,
                        model=model,
                        fatal=True,
                    )

                if response.status_code == 429:
                    # Check if this is a permanent quota issue vs temporary rate limit
                    try:
                        error_body = response.json()
                        error_code = error_body.get("error", {}).get("code", "")
                        error_msg = error_body.get("error", {}).get("message", "")
                    except Exception:
                        error_code = ""
                        error_msg = ""

                    if error_code == "insufficient_quota":
                        return AIResult(
                            success=False,
                            error=f"{provider_name} API quota exhausted. "
                                  f"Add billing credits or switch AI provider in Settings.",
                            error_type="quota_exhausted",
                            provider=provider_name,
                            model=model,
                            fatal=True,
                        )

                    # Temporary rate limit — use longer waits (20s, 40s, 60s)
                    rate_limit_wait = 20.0 * attempt
                    if attempt < self.max_retries:
                        logger.warning(
                            f"{provider_name} rate-limited. "
                            f"Retrying in {rate_limit_wait}s (attempt {attempt}/{self.max_retries})."
                        )
                        await asyncio.sleep(rate_limit_wait)
                        continue

                    # After all retries: non-fatal — skip this asset, continue to next
                    return AIResult(
                        success=False,
                        error=f"{provider_name} rate-limited. Skipping this asset. "
                              f"{error_msg or 'Will retry on next asset with longer delay.'}",
                        error_type="rate_limit",
                        provider=provider_name,
                        model=model,
                        fatal=False,
                    )

                # Other HTTP errors
                logger.error(
                    f"{provider_name} API error {response.status_code}: {response.text}"
                )
                return AIResult(
                    success=False,
                    error=f"{provider_name} API returned HTTP {response.status_code}.",
                    error_type="api_error",
                    provider=provider_name,
                    model=model,
                    fatal=response.status_code in (401, 403),
                )

            except httpx.TimeoutException:
                logger.warning(
                    f"{provider_name} request timed out "
                    f"(attempt {attempt}/{self.max_retries})."
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * attempt)
                    continue
                return AIResult(
                    success=False,
                    error=f"{provider_name} request timed out after {self.max_retries} attempts.",
                    error_type="timeout",
                    provider=provider_name,
                    model=model,
                    fatal=False,
                )

            except Exception as exc:
                logger.error(
                    f"{provider_name} unexpected error "
                    f"(attempt {attempt}/{self.max_retries}): {exc}"
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * attempt)
                    continue
                return AIResult(
                    success=False,
                    error=f"{provider_name} unexpected error: {exc}",
                    error_type="api_error",
                    provider=provider_name,
                    model=model,
                    fatal=False,
                )

        return AIResult(
            success=False,
            error=f"{provider_name} failed after all retries.",
            error_type="api_error",
            provider=provider_name,
            model=model,
            fatal=False,
        )

    async def _query_anthropic(
        self,
        *,
        endpoint: str,
        api_key: str,
        model: str,
        prompt: str,
        provider_name: str,
    ) -> AIResult:
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
                    return AIResult(
                        success=True,
                        content="".join(text_parts),
                        provider=provider_name,
                        model=model,
                    )

                if response.status_code == 401:
                    return AIResult(
                        success=False,
                        error=f"Invalid API key for {provider_name}. Check your key in Settings → AI Configuration.",
                        error_type="api_error",
                        provider=provider_name,
                        model=model,
                        fatal=True,
                    )

                if response.status_code == 429:
                    rate_limit_wait = 20.0 * attempt
                    if attempt < self.max_retries:
                        logger.warning(
                            f"{provider_name} rate-limited. "
                            f"Retrying in {rate_limit_wait}s (attempt {attempt}/{self.max_retries})."
                        )
                        await asyncio.sleep(rate_limit_wait)
                        continue

                    return AIResult(
                        success=False,
                        error=f"{provider_name} rate-limited. Skipping this asset.",
                        error_type="rate_limit",
                        provider=provider_name,
                        model=model,
                        fatal=False,
                    )

                logger.error(
                    f"{provider_name} API error {response.status_code}: {response.text}"
                )
                return AIResult(
                    success=False,
                    error=f"{provider_name} API returned HTTP {response.status_code}.",
                    error_type="api_error",
                    provider=provider_name,
                    model=model,
                    fatal=response.status_code in (401, 403),
                )

            except httpx.TimeoutException:
                logger.warning(
                    f"{provider_name} request timed out "
                    f"(attempt {attempt}/{self.max_retries})."
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * attempt)
                    continue
                return AIResult(
                    success=False,
                    error=f"{provider_name} request timed out after {self.max_retries} attempts.",
                    error_type="timeout",
                    provider=provider_name,
                    model=model,
                    fatal=False,
                )

            except Exception as exc:
                logger.error(
                    f"{provider_name} unexpected error "
                    f"(attempt {attempt}/{self.max_retries}): {exc}"
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * attempt)
                    continue
                return AIResult(
                    success=False,
                    error=f"{provider_name} unexpected error: {exc}",
                    error_type="api_error",
                    provider=provider_name,
                    model=model,
                    fatal=False,
                )

        return AIResult(
            success=False,
            error=f"{provider_name} failed after all retries.",
            error_type="api_error",
            provider=provider_name,
            model=model,
            fatal=False,
        )

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

        # Always create an alert if we got valid JSON with a title and summary.
        # No has_significant_news gate — the LLM is instructed to always provide insights.
        if not data.get("title") or not data.get("summary"):
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

        current_price = f"₹{asset.current_price:,.2f}" if asset.current_price else "N/A"
        purchase_price = f"₹{asset.purchase_price:,.2f}" if asset.purchase_price else "N/A"
        current_value = f"₹{asset.current_value:,.2f}" if asset.current_value else "N/A"
        asset_type = asset.asset_type  # enum instance for comparisons
        asset_type_value = asset_type.value  # string for prompt

        # Build holding context for personalized insights
        holding_context = f"Current Price: {current_price}"
        if asset.purchase_price:
            holding_context += f"\nPurchase Price: {purchase_price}"
        if asset.quantity:
            holding_context += f"\nQuantity: {asset.quantity}"
        if asset.current_value:
            holding_context += f"\nCurrent Value: {current_value}"

        # Market-traded assets get a different focus than fixed-income / govt schemes
        if asset_type in (AssetType.STOCK, AssetType.US_STOCK, AssetType.ESOP, AssetType.RSU):
            focus = """Focus areas:
1. Key risks, red flags, or concerns — corporate governance issues, debt problems, sector headwinds
2. Recent or upcoming catalysts — earnings results, regulatory decisions, management changes
3. Competitive landscape, market share trends, and sector outlook
4. Dividend history, buyback announcements, or payout sustainability
5. Analyst consensus and price target direction (bullish/bearish)
6. Any recent news that directly impacts this stock"""
        elif asset_type in (AssetType.EQUITY_MUTUAL_FUND, AssetType.HYBRID_MUTUAL_FUND):
            focus = """Focus areas:
1. Fund performance vs benchmark and category peers — recent returns
2. Portfolio concentration risks — top holdings, sector overweight
3. Fund manager changes or AMC-level concerns
4. NAV trends, AUM changes, or redemption pressure
5. SEBI regulatory changes affecting this fund category
6. Exit load, expense ratio changes, or tax implications"""
        elif asset_type == AssetType.DEBT_MUTUAL_FUND:
            focus = """Focus areas:
1. Interest rate outlook and its impact on debt fund NAV — RBI repo rate direction
2. Credit risk — any holdings with rating downgrades or default concerns
3. Duration risk — how sensitive is this fund to rate changes
4. Category comparison — liquid vs short-term vs corporate bond vs gilt
5. Tax efficiency changes (LTCG rules for debt funds)
6. Liquidity and exit load considerations"""
        elif asset_type == AssetType.CRYPTO:
            focus = """Focus areas:
1. Regulatory landscape in India and globally — RBI, SEBI, or government actions
2. Technology risks — network upgrades, forks, protocol vulnerabilities
3. Market sentiment — whale movements, exchange flows, funding rates
4. Security concerns — recent hacks, exchange issues, or scam alerts
5. Tax implications — 30% tax + 1% TDS for Indian crypto investors
6. Price action context — support/resistance levels, trend direction"""
        elif asset_type in (AssetType.COMMODITY, AssetType.SOVEREIGN_GOLD_BOND):
            focus = """Focus areas:
1. Supply-demand dynamics and global price drivers
2. Indian government policies — import duties, taxes, SGB issuance calendar
3. Inflation hedge value — CPI trends and real returns
4. Seasonal trends and cyclical factors affecting prices
5. Currency impact — USD/INR movement and its effect on domestic prices
6. Central bank buying/selling patterns (gold) or industrial demand shifts"""
        elif asset_type in (AssetType.REIT, AssetType.INVIT):
            focus = """Focus areas:
1. Distribution yield trends and payout consistency
2. Occupancy rates, lease renewals, and rental escalation outlook
3. NAV discount/premium and market price vs intrinsic value
4. Interest rate sensitivity — impact of rate changes on REIT/InvIT valuations
5. Regulatory changes affecting REITs/InvITs in India (SEBI rules)
6. Sponsor quality and asset quality of underlying portfolio"""
        else:
            focus = """Focus areas:
1. Key risks and opportunities for this investment
2. Regulatory or policy changes that may affect returns
3. Market conditions and outlook
4. Tax implications for Indian investors
5. Actionable recommendations"""

        return f"""Analyse the following asset from an Indian investor's portfolio and provide ONE important insight, risk alert, or actionable recommendation.

Asset: {asset_info}
Type: {asset_type_value}
{holding_context}

{focus}

RULES:
- Provide a specific, actionable insight about THIS asset — not generic advice.
- Use concrete data points where possible (earnings dates, rate changes, regulatory deadlines).
- Severity guide: "critical" = immediate action needed (crash, fraud, delisting risk), "warning" = attention needed (earnings miss, sector headwind, rating downgrade), "info" = useful update (analyst upgrade, sector trend, upcoming event).

Respond with ONLY this JSON (no markdown, no extra text):
{{
    "severity": "info|warning|critical",
    "title": "<concise headline, max 100 chars>",
    "summary": "<detailed insight with specific data points, max 500 chars>",
    "impact": "<how this affects the investor's holding>",
    "suggested_action": "<specific action the investor should consider>",
    "category": "price_change|news_event|regulatory_change|earnings_report|dividend_announcement|market_volatility|rebalance_suggestion"
}}"""

    def _build_generic_topic_prompt(self, topic: str) -> str:
        return f"""Provide ONE important and recent insight or update about: '{topic}'

This is for an Indian investor's portfolio alert system. Focus on:
1. Recent developments, announcements, or policy changes (last 30 days if possible)
2. Specific numbers, dates, or rates where applicable
3. Direct impact on Indian investors and their portfolios
4. Actionable recommendations

RULES:
- Be specific and data-driven — cite rates, percentages, dates, or policy names.
- Severity guide: "critical" = immediate action needed, "warning" = important change to note, "info" = useful update.

Respond with ONLY this JSON (no markdown, no extra text):
{{
    "severity": "info|warning|critical",
    "title": "<concise headline, max 100 chars>",
    "summary": "<detailed insight with specific data, max 500 chars>",
    "impact": "<how this affects Indian investors>",
    "suggested_action": "<specific action investors should consider>",
    "category": "regulatory_change|news_event|market_volatility"
}}"""


# Singleton instance
ai_news_service = AINewsService()
