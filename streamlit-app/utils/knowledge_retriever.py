"""Fast search over the persisted Phase 5.8 local knowledge index."""

from __future__ import annotations

import json
import re
from collections import Counter

from .analysis_models import KnowledgeSnippet
from .knowledge_models import KNOWLEDGE_TRUST_LABELS, KnowledgeSource
from .knowledge_pack_store import DEFAULT_INDEX_PATH, read_knowledge_index
from .query_expander import HOT_WORK_QUERY_TERMS, WORK_AT_HEIGHT_QUERY_TERMS, expand_safety_query, safety_query_profile


_KNOWLEDGE_TERMS = ("磨機", "火花", "熱工", "切割", "高空", "臨邊", "防墮", "法例", "指引", "安全")


def search_knowledge(
    query: str,
    topic_tags: list[str] | None = None,
    trust_filter: list[str] | None = None,
    limit: int = 10,
    *,
    index_path=DEFAULT_INDEX_PATH,
) -> list[KnowledgeSource]:
    terms = _terms(query)
    hot_work_query, height_query = safety_query_profile(query)
    wanted_topics = {item.lower() for item in topic_tags or []}
    wanted_trust = {item.lower() for item in trust_filter or []}
    ranked = []
    for source in read_knowledge_index(index_path=index_path):
        if wanted_topics and not wanted_topics.intersection(item.lower() for item in source.topic_tags):
            continue
        if wanted_trust and source.trust_level.lower() not in wanted_trust:
            continue
        searchable = json.dumps(source.to_dict(), ensure_ascii=False).lower()
        score = sum(5 if term in source.title.lower() else min(searchable.count(term), 4) for term in terms if term in searchable)
        score += _topic_adjustment(searchable, hot_work_query, height_query)
        if terms and score <= 0:
            continue
        ranked.append((score, source.last_indexed_at, source))
    ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)
    return [source for _, _, source in ranked[: max(0, int(limit))]]


def build_knowledge_pack_context(query: str, limit: int = 5, *, index_path=DEFAULT_INDEX_PATH) -> list[KnowledgeSnippet]:
    hits = search_knowledge(query, limit=limit, index_path=index_path)
    return [
        KnowledgeSnippet(
            title=item.title,
            path=item.path_or_url or f"Knowledge / {item.source_id}",
            snippet=item.summary,
            score=max(1.0, float(limit - rank)),
            source_type=item.source_type,
            source_id=f"knowledge-pack:{item.source_id}",
            trust_level="official_hk" if item.trust_level == "official" else ("trusted_industry" if item.trust_level == "trusted" else "local_internal"),
            provider="knowledge_pack",
        )
        for rank, item in enumerate(hits)
    ]


def summarize_knowledge_hits(hits: list[KnowledgeSource]) -> dict:
    counts = Counter(item.trust_level for item in hits)
    return {
        "total": len(hits),
        "trust_counts": dict(counts),
        "trust_labels": {key: KNOWLEDGE_TRUST_LABELS.get(key, key) for key in counts},
        "last_indexed_at": max((item.last_indexed_at for item in hits), default=""),
    }


def _terms(value: str) -> list[str]:
    text = str(value or "").lower()
    tokens = [term for term in re.findall(r"[a-z0-9_./-]+|[\u3400-\u9fff]+", text) if len(term) >= 2]
    known = [term.lower() for term in _KNOWLEDGE_TERMS if term.lower() in text]
    expanded = [item.lower() for item in expand_safety_query(text)]
    return list(dict.fromkeys([*known, *tokens, *expanded]))[:40]


def _topic_adjustment(searchable: str, hot_work_query: bool, height_query: bool) -> int:
    hot_hits = sum(term in searchable for term in HOT_WORK_QUERY_TERMS)
    height_hits = sum(term in searchable for term in WORK_AT_HEIGHT_QUERY_TERMS)
    if hot_work_query and not height_query:
        return hot_hits * 3 - (8 if height_hits and not hot_hits else 0)
    if height_query and not hot_work_query:
        return height_hits * 3 - (8 if hot_hits and not height_hits else 0)
    return hot_hits + height_hits
