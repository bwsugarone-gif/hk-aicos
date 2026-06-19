"""Simple BM25-like keyword retrieval over the local RAG JSONL index."""

from __future__ import annotations

import re
from collections import Counter

from .analysis_models import KnowledgeSnippet
from .rag_indexer import DEFAULT_RAG_PATH, read_rag_index
from .rag_models import RagChunk


_DOMAIN_TERMS = ("磨機", "火花", "熱工", "切割", "高空", "臨邊", "防墮", "安全", "法例", "指引", "棚架")


def search_rag(
    query: str,
    project_ref: str | None = None,
    trust_filter: list[str] | None = None,
    limit: int = 8,
    *,
    index_path=DEFAULT_RAG_PATH,
) -> list[RagChunk]:
    terms = _terms(query)
    trusts = {item.lower() for item in trust_filter or []}
    ranked = []
    for chunk in read_rag_index(index_path=index_path):
        if project_ref and (chunk.project_ref or "").lower() != project_ref.lower():
            continue
        if trusts and chunk.trust_level.lower() not in trusts:
            continue
        title = chunk.title.lower()
        text = (chunk.text + " " + " ".join(chunk.tags)).lower()
        score = sum(5 for term in terms if term in title) + sum(min(text.count(term), 6) for term in terms)
        if terms and not score:
            continue
        ranked.append((score, chunk.created_at, chunk))
    ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)
    return [chunk for _, _, chunk in ranked[: max(0, int(limit))]]


def build_rag_context(query: str, project_ref: str | None = None, limit: int = 5, *, index_path=DEFAULT_RAG_PATH) -> list[KnowledgeSnippet]:
    return [
        KnowledgeSnippet(
            title=chunk.title,
            path=f"RAG / {chunk.source_id}", snippet=chunk.text[:700],
            score=max(1.0, float(limit - rank)), source_type="rag_chunk",
            source_id=f"rag:{chunk.chunk_id}",
            trust_level="official_hk" if chunk.trust_level == "official" else ("trusted_industry" if chunk.trust_level == "trusted" else "local_internal"),
            provider="local_rag",
        )
        for rank, chunk in enumerate(search_rag(query, project_ref, limit=limit, index_path=index_path))
    ]


def summarize_rag_hits(hits: list[RagChunk]) -> dict:
    counts = Counter(item.trust_level for item in hits)
    return {
        "total": len(hits),
        "trust_counts": dict(counts),
        "last_updated_at": max((item.created_at for item in hits), default=""),
    }


def _terms(value: str) -> list[str]:
    text = str(value or "").lower()
    tokens = [term for term in re.findall(r"[a-z0-9_./-]+|[\u3400-\u9fff]+", text) if len(term) >= 2]
    known = [term for term in _DOMAIN_TERMS if term in text]
    return list(dict.fromkeys([*known, *tokens]))[:24]
