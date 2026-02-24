"""
System endpoints: version check, update notifications.
"""
import time
from fastapi import APIRouter, Depends
from loguru import logger
import httpx

from app.core.config import settings
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.system import UpdateCheckResponse

router = APIRouter()

# In-memory cache for GitHub release check
_cache: dict = {
    "data": None,
    "expires_at": 0.0,
}
_CACHE_TTL_SECONDS = 3600  # 1 hour

GITHUB_RELEASES_URL = (
    "https://api.github.com/repos/debasisdas1976/PortAct/releases/latest"
)


def _compare_versions(current: str, latest: str) -> bool:
    """Return True if latest > current using semantic version comparison."""
    try:
        def _parse(v: str):
            return tuple(int(p) for p in v.lstrip("v").split("."))
        return _parse(latest) > _parse(current)
    except (ValueError, TypeError):
        return False


async def _fetch_latest_release() -> dict:
    """Fetch the latest release from GitHub API with TTL caching."""
    now = time.time()

    if _cache["data"] is not None and now < _cache["expires_at"]:
        return _cache["data"]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                GITHUB_RELEASES_URL,
                headers={
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": f"PortAct/{settings.APP_VERSION}",
                },
            )

        if response.status_code == 200:
            data = response.json()
            result = {
                "latest_version": data.get("tag_name", "").lstrip("v"),
                "release_url": data.get("html_url", ""),
                "release_notes": data.get("body", ""),
                "published_at": data.get("published_at", ""),
            }
        elif response.status_code == 404:
            result = {
                "error": "No releases found on GitHub.",
                "latest_version": settings.APP_VERSION,
            }
        elif response.status_code == 403:
            result = {
                "error": "GitHub API rate limit exceeded. Try again later.",
                "latest_version": settings.APP_VERSION,
            }
        else:
            result = {
                "error": f"GitHub API returned status {response.status_code}.",
                "latest_version": settings.APP_VERSION,
            }

        _cache["data"] = result
        _cache["expires_at"] = now + _CACHE_TTL_SECONDS
        return result

    except httpx.TimeoutException:
        logger.warning("Timeout while checking GitHub for updates")
        return {
            "error": "Timed out contacting GitHub.",
            "latest_version": settings.APP_VERSION,
        }
    except Exception as exc:
        logger.warning(f"Failed to check for updates: {exc}")
        return {
            "error": "Could not check for updates.",
            "latest_version": settings.APP_VERSION,
        }


@router.get("/check-update", response_model=UpdateCheckResponse)
async def check_for_update(
    _current_user: User = Depends(get_current_active_user),
):
    """
    Check if a newer version of PortAct is available on GitHub Releases.
    Results are cached for 1 hour to avoid GitHub API rate limits.
    """
    release_info = await _fetch_latest_release()
    current = settings.APP_VERSION
    latest = release_info.get("latest_version", current)

    return UpdateCheckResponse(
        current_version=current,
        latest_version=latest,
        update_available=_compare_versions(current, latest),
        release_url=release_info.get("release_url"),
        release_notes=release_info.get("release_notes"),
        published_at=release_info.get("published_at"),
        error=release_info.get("error"),
    )
