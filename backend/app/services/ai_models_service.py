"""
Fetches available model lists from AI providers and caches them in app_settings.
"""
import json
from datetime import datetime, timezone

import httpx
from loguru import logger
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.app_settings import AppSettings

# Maps each provider to the endpoint / header scheme needed to list models.
# Most providers expose an OpenAI-compatible GET /v1/models endpoint.
PROVIDER_MODEL_ENDPOINTS = {
    "openai": {
        "url": "https://api.openai.com/v1/models",
        "auth": "bearer",
        "key_setting": "ai_openai_api_key",
        "key_env": "OPENAI_API_KEY",
    },
    "grok": {
        "url": "https://api.x.ai/v1/models",
        "auth": "bearer",
        "key_setting": "ai_grok_api_key",
        "key_env": "GROK_API_KEY",
    },
    "gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/models",
        "auth": "query_key",
        "key_setting": "ai_gemini_api_key",
        "key_env": "GEMINI_API_KEY",
    },
    "anthropic": {
        "url": "https://api.anthropic.com/v1/models",
        "auth": "anthropic",
        "key_setting": "ai_anthropic_api_key",
        "key_env": "ANTHROPIC_API_KEY",
    },
    "deepseek": {
        "url": "https://api.deepseek.com/models",
        "auth": "bearer",
        "key_setting": "ai_deepseek_api_key",
        "key_env": "DEEPSEEK_API_KEY",
    },
    "mistral": {
        "url": "https://api.mistral.ai/v1/models",
        "auth": "bearer",
        "key_setting": "ai_mistral_api_key",
        "key_env": "MISTRAL_API_KEY",
    },
}

CACHE_SETTING_KEY = "ai_available_models"
TIMEOUT = 15  # seconds per provider

# Well-known models shown immediately (before any API call succeeds).
# The scheduler will replace these with the live list once it runs.
DEFAULT_MODELS: dict[str, list[str]] = {
    "openai": [
        "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano",
        "gpt-4o", "gpt-4o-mini",
        "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo",
        "o3", "o3-mini", "o4-mini",
    ],
    "grok": [
        "grok-3", "grok-3-fast", "grok-3-mini", "grok-3-mini-fast",
        "grok-2", "grok-beta",
    ],
    "gemini": [
        "gemini-2.5-pro", "gemini-2.5-flash",
        "gemini-2.0-flash", "gemini-2.0-flash-lite",
        "gemini-1.5-pro", "gemini-1.5-flash",
    ],
    "anthropic": [
        "claude-opus-4-20250514", "claude-sonnet-4-20250514",
        "claude-3-7-sonnet-20250219",
        "claude-3-5-haiku-20241022",
    ],
    "deepseek": [
        "deepseek-chat", "deepseek-reasoner",
    ],
    "mistral": [
        "mistral-large-latest", "mistral-medium-latest",
        "mistral-small-latest", "open-mistral-nemo",
    ],
}


def _resolve_api_key(db: Session, provider_cfg: dict) -> str | None:
    """DB setting first, then env var."""
    row = db.query(AppSettings).filter(AppSettings.key == provider_cfg["key_setting"]).first()
    if row and row.value and not row.value.startswith("***"):
        return row.value
    return getattr(settings, provider_cfg["key_env"], None) or None


def _fetch_openai_compatible(url: str, api_key: str) -> list[str]:
    """GET /v1/models with Bearer token (OpenAI, Grok, DeepSeek, Mistral)."""
    resp = httpx.get(url, headers={"Authorization": f"Bearer {api_key}"}, timeout=TIMEOUT)
    resp.raise_for_status()
    data = resp.json().get("data", [])
    return sorted(m["id"] for m in data if isinstance(m, dict) and "id" in m)


def _fetch_anthropic_models(url: str, api_key: str) -> list[str]:
    """GET /v1/models with Anthropic-specific headers."""
    resp = httpx.get(
        url,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json().get("data", [])
    return sorted(m["id"] for m in data if isinstance(m, dict) and "id" in m)


def _fetch_gemini_models(url: str, api_key: str) -> list[str]:
    """GET /v1beta/models?key=... (Google Gemini REST)."""
    resp = httpx.get(url, params={"key": api_key}, timeout=TIMEOUT)
    resp.raise_for_status()
    models = resp.json().get("models", [])
    # Gemini returns names like "models/gemini-2.0-flash" — strip prefix
    result = []
    for m in models:
        name = m.get("name", "")
        if name.startswith("models/"):
            name = name[len("models/"):]
        # Only include generative models (skip embedding, etc.)
        methods = m.get("supportedGenerationMethods", [])
        if "generateContent" in methods:
            result.append(name)
    return sorted(result)


def _fetch_models_for_provider(db: Session, provider: str) -> list[str] | None:
    """Fetch models list for a single provider. Returns None if no key available."""
    cfg = PROVIDER_MODEL_ENDPOINTS.get(provider)
    if not cfg:
        return None
    api_key = _resolve_api_key(db, cfg)
    if not api_key:
        return None
    try:
        if cfg["auth"] == "anthropic":
            return _fetch_anthropic_models(cfg["url"], api_key)
        elif cfg["auth"] == "query_key":
            return _fetch_gemini_models(cfg["url"], api_key)
        else:
            return _fetch_openai_compatible(cfg["url"], api_key)
    except Exception as exc:
        logger.warning(f"Failed to fetch models for {provider}: {exc}")
        return None


def refresh_ai_models_cache() -> dict:
    """
    Fetch available models from all configured providers and cache in app_settings.
    Called by the scheduler (no args) or manually.
    Returns the models dict: {provider: [model_id, ...]}
    """
    db: Session = SessionLocal()
    try:
        result: dict[str, list[str]] = {}
        for provider in PROVIDER_MODEL_ENDPOINTS:
            models = _fetch_models_for_provider(db, provider)
            if models is not None:
                result[provider] = models
                logger.info(f"AI models cache: {provider} → {len(models)} models")

        # Store as JSON in app_settings
        payload = json.dumps({
            "models": result,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        row = db.query(AppSettings).filter(AppSettings.key == CACHE_SETTING_KEY).first()
        if row:
            row.value = payload
        else:
            db.add(AppSettings(
                key=CACHE_SETTING_KEY,
                value=payload,
                value_type="string",
                category="ai",
                label="AI Available Models Cache",
                description="Cached list of available models per AI provider (auto-refreshed daily).",
            ))
        db.commit()
        logger.info(f"AI models cache updated — {len(result)} providers")
        return result
    except Exception as exc:
        db.rollback()
        logger.error(f"AI models cache refresh failed: {exc}")
        return {}
    finally:
        db.close()


def get_cached_models(db: Session) -> dict:
    """
    Read cached models from app_settings, merged with defaults.
    Returns {models: {provider: [model_id, ...]}, updated_at: ...}.
    """
    cached: dict = {"models": {}, "updated_at": None}
    row = db.query(AppSettings).filter(AppSettings.key == CACHE_SETTING_KEY).first()
    if row and row.value:
        try:
            cached = json.loads(row.value)
        except (json.JSONDecodeError, TypeError):
            pass

    # Merge: use cached models if available, otherwise use defaults
    merged: dict[str, list[str]] = {}
    for provider in DEFAULT_MODELS:
        live = cached.get("models", {}).get(provider)
        merged[provider] = live if live else DEFAULT_MODELS[provider]
    return {"models": merged, "updated_at": cached.get("updated_at")}
