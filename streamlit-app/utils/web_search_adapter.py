"""Provider-ready web search adapter with honest no-provider fallback."""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .analysis_models import SearchResult
from .official_sources import filter_sources_by_mode


@dataclass
class WebSearchStatus:
    configured: bool
    performed: bool
    provider: str
    message: str
    source_mode: str = "general_web"
    trust_level: str = "fallback_only"
    official_results_found: bool = False
    result_count: int = 0


_last_status = WebSearchStatus(False, False, "none", "Web search is not configured.")


def get_web_search_status() -> WebSearchStatus:
    return _last_status


def web_search(query: str, limit: int = 5, source_mode: str = "general_web") -> list[SearchResult]:
    """Search through a configured provider; otherwise return an honest empty list."""
    global _last_status
    query = str(query or "").strip()
    limit = max(1, min(int(limit or 5), 10))
    if not query:
        _last_status = WebSearchStatus(False, False, "none", "Search query is empty.", source_mode=source_mode)
        return []

    if os.getenv("TAVILY_API_KEY", "").strip():
        return _search_tavily(query, limit, source_mode)
    if os.getenv("BRAVE_SEARCH_API_KEY", "").strip():
        return _search_brave(query, limit, source_mode)

    future_provider = _future_provider_name()
    if future_provider:
        _last_status = WebSearchStatus(
            True,
            False,
            future_provider,
            f"{future_provider} credentials are present, but this adapter is not enabled yet.",
            source_mode=source_mode,
        )
    else:
        _last_status = WebSearchStatus(
            False,
            False,
            "none",
            "Web search is not configured. Set TAVILY_API_KEY or BRAVE_SEARCH_API_KEY.",
            source_mode=source_mode,
        )
    return []


def _search_tavily(query: str, limit: int, source_mode: str) -> list[SearchResult]:
    payload = json.dumps(
        {"api_key": os.environ["TAVILY_API_KEY"], "query": query, "max_results": limit, "search_depth": "basic"}
    ).encode("utf-8")
    request = urllib.request.Request(
        "https://api.tavily.com/search",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return _perform(request, "tavily", limit, source_mode)


def _search_brave(query: str, limit: int, source_mode: str) -> list[SearchResult]:
    params = urllib.parse.urlencode({"q": query, "count": limit})
    request = urllib.request.Request(
        "https://api.search.brave.com/res/v1/web/search?" + params,
        headers={
            "Accept": "application/json",
            "X-Subscription-Token": os.environ["BRAVE_SEARCH_API_KEY"],
        },
    )
    return _perform(request, "brave", limit, source_mode)


def _perform(request: urllib.request.Request, provider: str, limit: int, source_mode: str) -> list[SearchResult]:
    global _last_status
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            payload = json.loads(response.read().decode("utf-8"))
        raw_results = payload.get("results", []) if provider == "tavily" else payload.get("web", {}).get("results", [])
        converted = [_convert_result(item, provider) for item in raw_results[:limit] if isinstance(item, dict)]
        results = filter_sources_by_mode(converted, source_mode)
        official_found = any(item.trust_level == "official_hk" for item in results)
        _last_status = WebSearchStatus(
            True,
            True,
            provider,
            f"Web search completed with {len(results)} result(s) after trust filtering.",
            source_mode=source_mode,
            trust_level="official_hk" if official_found else (results[0].trust_level if results else "unknown"),
            official_results_found=official_found,
            result_count=len(results),
        )
        return results
    except Exception as exc:
        _last_status = WebSearchStatus(
            True,
            False,
            provider,
            f"Web search failed: {type(exc).__name__}: {exc}",
            source_mode=source_mode,
        )
        return []


def _convert_result(item: dict[str, Any], provider: str) -> SearchResult:
    return SearchResult(
        title=str(item.get("title") or "Untitled result"),
        url=str(item.get("url") or ""),
        snippet=str(item.get("content") or item.get("description") or ""),
        source=provider,
        published_date=item.get("published_date") or item.get("page_age"),
        confidence=_safe_float(item.get("score")),
        source_type="general_web",
        trust_level="unknown",
        provider=provider,
        retrieved_at=datetime.now(timezone.utc).isoformat(),
    )


def _safe_float(value: Any) -> float | None:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return None


def _future_provider_name() -> str:
    if os.getenv("SERPAPI_API_KEY", "").strip():
        return "serpapi"
    if os.getenv("GOOGLE_CSE_ID", "").strip() and os.getenv("GOOGLE_API_KEY", "").strip():
        return "google_cse"
    return ""
