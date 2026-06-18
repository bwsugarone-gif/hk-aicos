"""Trust classification and filtering for Hong Kong construction sources."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from typing import Any, Iterable
from urllib.parse import urlsplit, urlunsplit

from .analysis_models import SourceCitation


SOURCE_MODES = ("official_only", "trusted_first", "general_web")
OFFICIAL_HK_DOMAINS = {
    "gov.hk",
    "labour.gov.hk",
    "bd.gov.hk",
    "emsd.gov.hk",
    "devb.gov.hk",
    "e-legislation.gov.hk",
}
TRUSTED_INDUSTRY_DOMAINS = {
    "cic.hk",
    "hkcic.org",
    "construction-innovation.hk",
}
TRUST_LABELS_ZH = {
    "official_hk": "官方香港來源",
    "trusted_industry": "可信行業來源",
    "local_internal": "本地內部文件",
    "uploaded_record": "已儲存紀錄",
    "general_web": "一般網上來源",
    "fallback_only": "未使用外部來源",
    "unknown": "未分類來源",
}
SOURCE_MODE_LABELS_ZH = {
    "official_only": "只限香港官方來源",
    "trusted_first": "官方／可信來源優先",
    "general_web": "一般網上搜尋",
}


def normalize_url(url: str) -> str:
    value = str(url or "").strip()
    if not value:
        return ""
    if value.lower().startswith(("javascript:", "data:", "file:", "mailto:")):
        return ""
    if value.startswith("//"):
        value = "https:" + value
    elif "://" not in value:
        value = "https://" + value
    try:
        parts = urlsplit(value)
    except ValueError:
        return ""
    if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
        return ""
    host = parts.hostname.lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    try:
        port = parts.port
    except ValueError:
        return ""
    netloc = host if port is None else f"{host}:{port}"
    path = parts.path or "/"
    return urlunsplit((parts.scheme.lower(), netloc, path, parts.query, ""))


def extract_domain(url: str) -> str:
    normalized = normalize_url(url)
    if not normalized:
        return ""
    return (urlsplit(normalized).hostname or "").lower()


def is_official_hk_source(url: str) -> bool:
    domain = extract_domain(url)
    return any(_domain_matches(domain, trusted) for trusted in OFFICIAL_HK_DOMAINS)


def classify_source_trust(url: str) -> str:
    domain = extract_domain(url)
    if not domain:
        return "unknown"
    if any(_domain_matches(domain, trusted) for trusted in OFFICIAL_HK_DOMAINS):
        return "official_hk"
    if any(_domain_matches(domain, trusted) for trusted in TRUSTED_INDUSTRY_DOMAINS):
        return "trusted_industry"
    return "general_web"


def default_source_mode(question_type: str) -> str:
    if question_type == "law_regulation":
        return "official_only"
    if question_type == "safety":
        return "trusted_first"
    return "general_web"


def filter_sources_by_mode(results: Iterable[Any], mode: str) -> list[Any]:
    """Enrich source trust and filter/sort without restricting future domains."""
    normalized_mode = mode if mode in SOURCE_MODES else "general_web"
    enriched = [_with_trust(result) for result in results]
    if normalized_mode == "official_only":
        return [item for item in enriched if _trust_of(item) == "official_hk"]
    if normalized_mode == "trusted_first":
        rank = {"official_hk": 0, "trusted_industry": 1, "general_web": 2, "unknown": 3}
        return sorted(enriched, key=lambda item: rank.get(_trust_of(item), 4))
    return enriched


def source_id_for(value: str, prefix: str = "src") -> str:
    digest = hashlib.sha256(str(value or "unknown").encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def citation_from_source(source: Any, *, used_in_answer: bool = False) -> SourceCitation:
    data = _as_dict(source)
    url = normalize_url(str(data.get("url") or data.get("source_url") or ""))
    path = str(data.get("path") or data.get("source_path") or "")
    trust = str(data.get("trust_level") or "").strip()
    if trust in {"", "unknown"}:
        trust = classify_source_trust(url) if url else str(data.get("source_type") or "unknown")
    if trust not in TRUST_LABELS_ZH:
        trust = "unknown"
    source_type = str(data.get("source_type") or trust)
    identifier = str(data.get("source_id") or source_id_for(url or path or str(data.get("title") or "source")))
    return SourceCitation(
        source_id=identifier,
        source_title=str(data.get("title") or data.get("source_title") or "未命名來源"),
        source_url=url,
        source_path=path,
        source_type=source_type,
        trust_level=trust,
        snippet=str(data.get("snippet") or data.get("content_summary") or "")[:1000],
        used_in_answer=bool(used_in_answer or data.get("used_in_answer")),
        provider=str(data.get("provider") or data.get("source") or ""),
        retrieved_at=data.get("retrieved_at"),
    )


def _with_trust(result: Any) -> Any:
    data = _as_dict(result)
    trust = classify_source_trust(str(data.get("url") or ""))
    source_id = str(data.get("source_id") or source_id_for(str(data.get("url") or data.get("title") or "source"), "web"))
    if isinstance(result, dict):
        enriched = dict(result)
        enriched["trust_level"] = trust
        enriched["source_type"] = trust if trust != "unknown" else "general_web"
        enriched["source_id"] = source_id
        return enriched
    try:
        return replace(
            result,
            trust_level=trust,
            source_type=trust if trust != "unknown" else "general_web",
            source_id=source_id,
        )
    except (TypeError, ValueError):
        return result


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return {
        key: getattr(value, key)
        for key in ("title", "url", "path", "snippet", "source", "source_type", "trust_level", "source_id", "provider", "retrieved_at")
        if hasattr(value, key)
    }


def _trust_of(value: Any) -> str:
    return str(_as_dict(value).get("trust_level") or "unknown")


def _domain_matches(domain: str, trusted: str) -> bool:
    return bool(domain) and (domain == trusted or domain.endswith("." + trusted))
