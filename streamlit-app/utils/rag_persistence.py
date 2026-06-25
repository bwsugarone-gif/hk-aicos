"""Persistence + retrieval for ingested-document RAG chunks (Phase 6.4).

Uploaded knowledge documents are chunked into :class:`RagChunk` rows and stored
in a dedicated, append-only, git-ignored JSONL store
(``data/ingested_rag_chunks.jsonl``). Keeping these separate from the
auto-rebuilt ``rag_index.jsonl`` means a "rebuild SOP/RAG index" action can never
wipe user-ingested document chunks — that is the persistence hardening goal.

Chunking is deterministic and page-aware; no embeddings are used.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .analysis_models import KnowledgeSnippet
from .rag_indexer import chunk_text
from .rag_models import RagChunk


_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DEFAULT_INGESTED_RAG_PATH = _DATA_DIR / "ingested_rag_chunks.jsonl"
_LOCK = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())


def build_chunks_from_pages(
    *,
    source_id: str,
    source_title: str,
    source_file_name: str | None,
    pages: list[Any],
    project_ref: str | None = None,
    source_type: str = "uploaded_document",
    trust_level: str = "internal",
    tags: list[str] | None = None,
    confidence: float = 1.0,
) -> list[RagChunk]:
    """Deterministically chunk page texts into RAG chunks, preserving page refs.

    ``pages`` items may be ``PageText`` objects or ``{"page_number", "text"}``
    dicts. Page numbers and the source file name are preserved on every chunk.
    """
    now = _now()
    tags = list(tags or [])
    chunks: list[RagChunk] = []
    for page in pages or []:
        page_number = getattr(page, "page_number", None)
        text = getattr(page, "text", None)
        if text is None and isinstance(page, dict):
            page_number = page.get("page_number")
            text = page.get("text")
        try:
            page_number = int(page_number) if page_number not in (None, "") else None
        except (TypeError, ValueError):
            page_number = None
        for index, content in enumerate(chunk_text(str(text or ""))):
            digest = hashlib.sha256(
                f"{source_id}:{page_number}:{index}:{content}".encode("utf-8", errors="ignore")
            ).hexdigest()[:20]
            chunks.append(RagChunk(
                chunk_id=f"ingrag_{digest}",
                source_id=source_id,
                title=source_title,
                source_type=source_type,
                trust_level=trust_level,
                project_ref=project_ref,
                section_ref=(f"第 {page_number} 頁" if page_number else None),
                page_ref=(f"p.{page_number}" if page_number else None),
                text=content,
                summary=" ".join(content.split())[:240],
                tags=tags,
                created_at=now,
                metadata={"source_file_name": source_file_name} if source_file_name else {},
                source_file_name=source_file_name,
                page_number=page_number,
                confidence=max(0.0, min(1.0, float(confidence))),
            ))
    return chunks


def append_ingested_chunks(
    chunks: list[RagChunk],
    *,
    path: str | Path = DEFAULT_INGESTED_RAG_PATH,
) -> list[RagChunk]:
    rows = [chunk.to_dict() for chunk in chunks if chunk.chunk_id and chunk.text]
    _append_rows(Path(path), rows)
    return chunks


def read_ingested_chunks(*, path: str | Path = DEFAULT_INGESTED_RAG_PATH) -> list[RagChunk]:
    file_path = Path(path)
    if not file_path.exists():
        return []
    chunks: list[RagChunk] = []
    try:
        lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            chunk = RagChunk.from_dict(json.loads(line))
        except (json.JSONDecodeError, TypeError, ValueError, KeyError):
            continue
        if chunk.chunk_id and chunk.text:
            chunks.append(chunk)
    return chunks


def _terms(value: str) -> list[str]:
    import re

    text = str(value or "").lower()
    tokens = [term for term in re.findall(r"[a-z0-9_./-]+|[㐀-鿿]+", text) if len(term) >= 2]
    return list(dict.fromkeys(tokens))[:40]


def search_ingested_chunks(
    query: str,
    *,
    project_ref: str | None = None,
    source_id: str | None = None,
    limit: int = 8,
    path: str | Path = DEFAULT_INGESTED_RAG_PATH,
) -> list[RagChunk]:
    """Deterministic keyword search over ingested document chunks."""
    terms = _terms(query)
    ranked: list[tuple[int, str, RagChunk]] = []
    for chunk in read_ingested_chunks(path=path):
        if project_ref and (chunk.project_ref or "").lower() != project_ref.lower():
            continue
        if source_id and chunk.source_id != source_id:
            continue
        title = chunk.title.lower()
        blob = (chunk.text + " " + " ".join(chunk.tags) + " " + (chunk.source_file_name or "")).lower()
        score = sum(5 for term in terms if term in title) + sum(min(blob.count(term), 6) for term in terms)
        if terms and score <= 0:
            continue
        ranked.append((score, chunk.created_at, chunk))
    ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)
    return [chunk for _, _, chunk in ranked[: max(0, int(limit))]]


def build_ingested_rag_context(
    query: str,
    project_ref: str | None = None,
    limit: int = 5,
    *,
    path: str | Path = DEFAULT_INGESTED_RAG_PATH,
) -> list[KnowledgeSnippet]:
    """KnowledgeSnippets from ingested document chunks for Ask AICOS context."""
    snippets: list[KnowledgeSnippet] = []
    for rank, chunk in enumerate(search_ingested_chunks(query, project_ref=project_ref, limit=limit, path=path)):
        page_hint = f"（第 {chunk.page_number} 頁）" if chunk.page_number else ""
        snippets.append(KnowledgeSnippet(
            title=f"{chunk.title}{page_hint}",
            path=f"知識文件 / {chunk.source_file_name or chunk.source_id}",
            snippet=chunk.text[:700],
            score=max(1.0, float(limit - rank)),
            source_type="rag_chunk",
            source_id=f"ingrag:{chunk.chunk_id}",
            trust_level="uploaded_record",
            provider="ingested_documents",
        ))
    return snippets
