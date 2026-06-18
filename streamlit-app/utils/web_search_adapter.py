"""Real web-search providers with transparent, non-crashing fallback behavior."""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterator

from .analysis_models import SearchResult
from .official_sources import SOURCE_MODES, extract_domain, filter_sources_by_mode


@dataclass(eq=False)
class WebSearchResponse:
    results: list[SearchResult] = field(default_factory=list)
    provider: str = "fallback"
    configured: bool = False
    error: str | None = None
    searched_query: str = ""
    search_mode: str = "trusted_first"
    official_results_count: int = 0
    trusted_results_count: int = 0
    general_results_count: int = 0
    fallback_used: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "results": [item.to_dict() for item in self.results],
            "provider": self.provider,
            "configured": self.configured,
            "error": self.error,
            "searched_query": self.searched_query,
            "search_mode": self.search_mode,
            "official_results_count": self.official_results_count,
            "trusted_results_count": self.trusted_results_count,
            "general_results_count": self.general_results_count,
            "fallback_used": self.fallback_used,
        }

    # Phase 5.6 compatibility: callers that treated web_search() as a list keep
    # working while new code consumes the structured response above.
    def __iter__(self) -> Iterator[SearchResult]:
        return iter(self.results)

    def __len__(self) -> int:
        return len(self.results)

    def __getitem__(self, index: int) -> SearchResult:
        return self.results[index]

    def __eq__(self, other: object) -> bool:
        if isinstance(other, list):
            return self.results == other
        if isinstance(other, WebSearchResponse):
            return self.to_dict() == other.to_dict()
        return NotImplemented


@dataclass
class WebSearchStatus:
    """Legacy status view retained for Phase 5.6 integrations."""

    configured: bool
    performed: bool
    provider: str
    message: str
    source_mode: str = "general_web"
    trust_level: str = "fallback_only"
    official_results_found: bool = False
    result_count: int = 0


class WebSearchProvider(ABC):
    name = "unknown"

    def __init__(self, api_key: str = "") -> None:
        self.api_key = str(api_key or "").strip()

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    @abstractmethod
    def search(self, query: str, limit: int) -> list[SearchResult]:
        """Run a provider request and return normalized, unfiltered results."""


class TavilySearchProvider(WebSearchProvider):
    name = "tavily"

    def search(self, query: str, limit: int) -> list[SearchResult]:
        payload = json.dumps(
            {
                "api_key": self.api_key,
                "query": query,
                "max_results": limit,
                "search_depth": "basic",
                "include_answer": False,
                "include_raw_content": False,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            "https://api.tavily.com/search",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        response = _open_json(request)
        raw_results = response.get("results", []) if isinstance(response, dict) else []
        return [
            _convert_result(item, self.name)
            for item in raw_results[:limit]
            if isinstance(item, dict)
        ]


class BraveSearchProvider(WebSearchProvider):
    name = "brave"

    def search(self, query: str, limit: int) -> list[SearchResult]:
        params = urllib.parse.urlencode({"q": query, "count": limit, "search_lang": "zh-hant"})
        request = urllib.request.Request(
            "https://api.search.brave.com/res/v1/web/search?" + params,
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": self.api_key,
            },
        )
        response = _open_json(request)
        web = response.get("web", {}) if isinstance(response, dict) else {}
        raw_results = web.get("results", []) if isinstance(web, dict) else []
        return [
            _convert_result(item, self.name)
            for item in raw_results[:limit]
            if isinstance(item, dict)
        ]


class FallbackSearchProvider(WebSearchProvider):
    name = "fallback"

    def __init__(self) -> None:
        super().__init__("")

    def search(self, query: str, limit: int) -> list[SearchResult]:
        return []


_last_response = WebSearchResponse()
_last_status = WebSearchStatus(False, False, "fallback", "Web search is not configured.")


def get_web_search_status() -> WebSearchStatus:
    return _last_status


def select_web_search_provider() -> WebSearchProvider:
    """Select Tavily first, then Brave, then an honest fallback provider."""
    tavily_key = os.getenv("TAVILY_API_KEY", "").strip()
    if tavily_key:
        return TavilySearchProvider(tavily_key)
    brave_key = os.getenv("BRAVE_SEARCH_API_KEY", "").strip()
    if brave_key:
        return BraveSearchProvider(brave_key)
    return FallbackSearchProvider()


def web_search(
    query: str,
    limit: int = 5,
    mode: str = "trusted_first",
    *,
    source_mode: str | None = None,
) -> WebSearchResponse:
    """Search with the highest-priority configured provider and never crash."""
    global _last_response, _last_status

    searched_query = " ".join(str(query or "").split())
    normalized_mode = source_mode if source_mode in SOURCE_MODES else mode
    normalized_mode = normalized_mode if normalized_mode in SOURCE_MODES else "trusted_first"
    normalized_limit = _normalize_limit(limit)
    provider = select_web_search_provider()

    if not searched_query:
        response = WebSearchResponse(
            provider=provider.name,
            configured=provider.configured,
            error="Search query is empty.",
            searched_query="",
            search_mode=normalized_mode,
            fallback_used=True,
        )
        return _remember(response)

    if isinstance(provider, FallbackSearchProvider):
        return _remember(
            WebSearchResponse(
                provider=provider.name,
                configured=False,
                searched_query=searched_query,
                search_mode=normalized_mode,
                fallback_used=True,
            )
        )

    try:
        raw_results = provider.search(searched_query, normalized_limit)
        results = filter_sources_by_mode(raw_results, normalized_mode)
        response = _response_with_counts(
            results=results,
            provider=provider.name,
            configured=True,
            searched_query=searched_query,
            search_mode=normalized_mode,
            fallback_used=False,
        )
    except Exception as exc:
        response = WebSearchResponse(
            provider=provider.name,
            configured=True,
            error=_safe_error(exc, provider.api_key),
            searched_query=searched_query,
            search_mode=normalized_mode,
            fallback_used=True,
        )
    return _remember(response)


def _open_json(request: urllib.request.Request) -> dict[str, Any]:
    with urllib.request.urlopen(request, timeout=12) as response:
        content_encoding = str(response.headers.get("Content-Encoding", "")).lower()
        raw = response.read()
        if content_encoding == "gzip":
            import gzip

            raw = gzip.decompress(raw)
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Search provider returned a non-object JSON response.")
    return payload


def _convert_result(item: dict[str, Any], provider: str) -> SearchResult:
    url = str(item.get("url") or "").strip()
    return SearchResult(
        title=str(item.get("title") or "未命名搜尋結果").strip(),
        url=url,
        snippet=str(item.get("content") or item.get("description") or "").strip(),
        source=extract_domain(url) or provider,
        provider=provider,
        published_date=_optional_text(item.get("published_date") or item.get("page_age")),
        confidence=_safe_float(item.get("score")),
        source_type="general_web",
        trust_level="unknown",
        retrieved_at=datetime.now(timezone.utc).isoformat(),
        used_in_answer=False,
    )


def _response_with_counts(**kwargs: Any) -> WebSearchResponse:
    results = list(kwargs.pop("results", []))
    return WebSearchResponse(
        results=results,
        official_results_count=sum(item.trust_level == "official_hk" for item in results),
        trusted_results_count=sum(item.trust_level == "trusted_industry" for item in results),
        general_results_count=sum(item.trust_level == "general_web" for item in results),
        **kwargs,
    )


def _remember(response: WebSearchResponse) -> WebSearchResponse:
    global _last_response, _last_status
    _last_response = response
    performed = response.configured and not response.fallback_used and response.error is None
    if response.error:
        message = f"Web search failed: {response.error}"
    elif performed:
        message = f"Web search completed with {len(response.results)} result(s)."
    else:
        message = "Web search is not configured. Set TAVILY_API_KEY or BRAVE_SEARCH_API_KEY."
    first_trust = response.results[0].trust_level if response.results else "fallback_only"
    _last_status = WebSearchStatus(
        configured=response.configured,
        performed=performed,
        provider=response.provider,
        message=message,
        source_mode=response.search_mode,
        trust_level="official_hk" if response.official_results_count else first_trust,
        official_results_found=response.official_results_count > 0,
        result_count=len(response.results),
    )
    return response


def _normalize_limit(limit: Any) -> int:
    try:
        return max(1, min(int(limit or 5), 10))
    except (TypeError, ValueError):
        return 5


def _safe_error(exc: Exception, secret: str) -> str:
    message = f"{type(exc).__name__}: {exc}"[:500]
    if secret:
        message = message.replace(secret, "[REDACTED]")
    return message


def _safe_float(value: Any) -> float | None:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return None


def _optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None
