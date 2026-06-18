import json

import pytest

from utils.analysis_models import SearchResult
from utils.search_query_builder import build_hk_official_query
from utils import web_search_adapter
from utils.web_search_adapter import (
    BraveSearchProvider,
    TavilySearchProvider,
    WebSearchResponse,
    get_web_search_status,
    select_web_search_provider,
    web_search,
)


WEB_KEYS = ("TAVILY_API_KEY", "BRAVE_SEARCH_API_KEY")


def _clear_web_keys(monkeypatch):
    for name in WEB_KEYS:
        monkeypatch.delenv(name, raising=False)


def _provider_results():
    return [
        SearchResult("Labour", "https://labour.gov.hk/safety", "Official", "labour.gov.hk"),
        SearchResult("CIC", "https://www.cic.hk/eng/safety", "Industry", "cic.hk"),
        SearchResult("Article", "https://example.com/safety", "General", "example.com"),
    ]


def test_provider_selection_prefers_tavily(monkeypatch):
    _clear_web_keys(monkeypatch)
    monkeypatch.setenv("TAVILY_API_KEY", "test-tavily")
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "test-brave")
    monkeypatch.setattr(TavilySearchProvider, "search", lambda self, query, limit: _provider_results())

    assert isinstance(select_web_search_provider(), TavilySearchProvider)
    response = web_search("香港地盤安全", mode="general_web")
    assert response.provider == "tavily"
    assert response.configured is True
    assert response.fallback_used is False


def test_provider_selection_uses_brave_without_tavily(monkeypatch):
    _clear_web_keys(monkeypatch)
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "test-brave")
    monkeypatch.setattr(BraveSearchProvider, "search", lambda self, query, limit: _provider_results())

    assert isinstance(select_web_search_provider(), BraveSearchProvider)
    response = web_search("香港建築物料", mode="trusted_first")
    assert response.provider == "brave"
    assert response.configured is True
    assert [item.trust_level for item in response.results] == [
        "official_hk",
        "trusted_industry",
        "general_web",
    ]


def test_no_provider_returns_honest_fallback(monkeypatch):
    _clear_web_keys(monkeypatch)
    response = web_search("香港高空工作", mode="official_only")

    assert isinstance(response, WebSearchResponse)
    assert response.results == []
    assert response.provider == "fallback"
    assert response.configured is False
    assert response.fallback_used is True
    assert response.error is None
    status = get_web_search_status()
    assert status.performed is False
    assert status.source_mode == "official_only"


def test_query_builder_biases_law_to_hk_official_domains():
    query = build_hk_official_query("高空工作適用哪條法例？", "law_regulation", "official_only")
    assert "site:elegislation.gov.hk" in query
    assert "site:e-legislation.gov.hk" in query
    assert "site:labour.gov.hk" in query
    assert "香港" in query
    assert "法例" in query
    assert len(query) <= 420


def test_query_builder_adds_broad_hk_safety_hints_for_trusted_first():
    query = build_hk_official_query("臨邊護欄有甚麼要求？", "safety", "trusted_first")
    assert "香港" in query
    assert "地盤" in query
    assert "安全" in query
    assert "勞工處" in query
    assert "建造業議會" in query


def test_general_web_query_is_not_site_restricted():
    query = build_hk_official_query("防水物料比較", "material", "general_web")
    assert "site:" not in query
    assert "香港" in query


def test_response_shape_and_official_counts(monkeypatch):
    _clear_web_keys(monkeypatch)
    monkeypatch.setenv("TAVILY_API_KEY", "test-tavily")
    monkeypatch.setattr(TavilySearchProvider, "search", lambda self, query, limit: _provider_results())

    response = web_search("safety", mode="general_web")
    payload = response.to_dict()
    assert set(payload) == {
        "results",
        "provider",
        "configured",
        "error",
        "searched_query",
        "search_mode",
        "official_results_count",
        "trusted_results_count",
        "general_results_count",
        "fallback_used",
    }
    assert response.official_results_count == 1
    assert response.trusted_results_count == 1
    assert response.general_results_count == 1
    assert all("trust_level" in item for item in payload["results"])
    assert all(item["used_in_answer"] is False for item in payload["results"])


@pytest.mark.parametrize(
    ("env_name", "provider_class", "provider_name"),
    [
        ("TAVILY_API_KEY", TavilySearchProvider, "tavily"),
        ("BRAVE_SEARCH_API_KEY", BraveSearchProvider, "brave"),
    ],
)
def test_provider_failure_returns_safe_fallback(monkeypatch, env_name, provider_class, provider_name):
    _clear_web_keys(monkeypatch)
    monkeypatch.setenv(env_name, "secret-test-key")

    def fail(self, query, limit):
        raise RuntimeError(f"temporary failure {self.api_key}")

    monkeypatch.setattr(provider_class, "search", fail)
    response = web_search("香港安全", mode="trusted_first")

    assert response.provider == provider_name
    assert response.configured is True
    assert response.fallback_used is True
    assert response.results == []
    assert "RuntimeError" in response.error
    assert "secret-test-key" not in response.error
    assert "[REDACTED]" in response.error
    assert get_web_search_status().performed is False


class _FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")
        self.headers = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return self.payload


def test_tavily_network_response_is_normalized_without_live_call(monkeypatch):
    payload = {
        "results": [
            {
                "title": "Labour safety guide",
                "url": "https://www.labour.gov.hk/eng/public/os/B/FIW.pdf",
                "content": "Safety guidance",
                "score": 0.91,
                "published_date": "2025-01-02",
            }
        ]
    }
    monkeypatch.setattr(
        web_search_adapter.urllib.request,
        "urlopen",
        lambda request, timeout: _FakeResponse(payload),
    )
    results = TavilySearchProvider("test-key").search("香港安全", 5)
    assert results[0].provider == "tavily"
    assert results[0].source == "labour.gov.hk"
    assert results[0].confidence == 0.91
    assert results[0].published_date == "2025-01-02"
