"""Dependency-free local SOP/RAG chunking and JSONL indexing."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .knowledge_pack_store import REPO_ROOT, read_knowledge_index
from .rag_models import RagChunk
from .source_reference_extractor import extract_source_reference


APP_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAG_PATH = APP_ROOT / "data" / "rag_index.jsonl"
SAFE_TEXT_EXTENSIONS = {".md", ".txt", ".rst", ".sql", ".py"}
EXCLUDED_PARTS = {".git", ".venv", "venv", "node_modules", "__pycache__", "uploads", "data", ".pytest_cache", "cache"}
MAX_SOURCE_BYTES = 1_000_000
_SECRET_LINE = re.compile(r"(?i)(api[_-]?key|secret|password|token|authorization)\s*[:=]|sk-[a-z0-9_-]{8,}")


def chunk_text(text: str, max_chars: int = 800, overlap: int = 100) -> list[str]:
    clean = "\n".join(line for line in str(text or "").splitlines() if not _SECRET_LINE.search(line)).strip()
    if not clean or max_chars <= 0:
        return []
    overlap = max(0, min(int(overlap), max_chars - 1))
    chunks = []
    start = 0
    while start < len(clean):
        end = min(len(clean), start + max_chars)
        if end < len(clean):
            boundary = max(clean.rfind("\n", start, end), clean.rfind("。", start, end), clean.rfind(". ", start, end))
            if boundary > start + max_chars // 2:
                end = boundary + 1
        chunk = clean[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(clean):
            break
        start = max(start + 1, end - overlap)
    return chunks


def index_text_source(
    source_id: str,
    title: str,
    text: str,
    metadata: dict | None = None,
    *,
    index_path: str | Path = DEFAULT_RAG_PATH,
    append: bool = True,
) -> list[RagChunk]:
    metadata = dict(metadata or {})
    now = datetime.now(timezone.utc).isoformat()
    chunks = []
    for index, content in enumerate(chunk_text(text)):
        digest = hashlib.sha256(f"{source_id}:{index}:{content}".encode("utf-8", errors="ignore")).hexdigest()[:20]
        reference = extract_source_reference({
            "source_id": source_id,
            "title": title,
            "snippet": content,
            "trust_level": metadata.get("trust_level", "unverified"),
            "url": metadata.get("path_or_url", ""),
        })
        chunks.append(RagChunk(
            chunk_id=f"rag_{digest}", source_id=source_id, title=title,
            source_type=str(metadata.get("source_type") or "project_note"),
            trust_level=str(metadata.get("trust_level") or "unverified"),
            project_ref=metadata.get("project_ref"),
            section_ref=metadata.get("section_ref") or reference.section or reference.clause or None,
            page_ref=metadata.get("page_ref") or reference.page or None,
            text=content, summary=" ".join(content.split())[:240],
            tags=list(metadata.get("tags") or []), created_at=now,
            metadata={key: value for key, value in metadata.items() if key not in {"raw_text", "api_key", "secret"}},
        ))
    _write_chunks(chunks, Path(index_path), append=append)
    return chunks


def build_rag_index_from_knowledge_sources(
    limit: int | None = None,
    *,
    knowledge_index_path=None,
    rag_index_path: str | Path = DEFAULT_RAG_PATH,
) -> list[RagChunk]:
    kwargs = {"index_path": knowledge_index_path} if knowledge_index_path else {}
    sources = read_knowledge_index(**kwargs)
    if limit is not None:
        sources = sources[: max(0, int(limit))]
    all_chunks = []
    for source in sources:
        text = _source_text(source.path_or_url)
        if not text:
            text = f"{source.title}\n{source.summary}\n" + " ".join(source.extracted_refs)
        metadata = {
            "source_type": source.source_type,
            "trust_level": source.trust_level,
            "tags": [*source.topic_tags, *source.trade_tags],
            "path_or_url": source.path_or_url,
        }
        for index, content in enumerate(chunk_text(text)):
            digest = hashlib.sha256(f"{source.source_id}:{index}:{content}".encode("utf-8", errors="ignore")).hexdigest()[:20]
            reference = extract_source_reference({
                "source_id": source.source_id,
                "title": source.title,
                "snippet": content,
                "trust_level": source.trust_level,
                "url": source.path_or_url or "",
            })
            all_chunks.append(RagChunk(
                chunk_id=f"rag_{digest}", source_id=source.source_id, title=source.title,
                source_type=source.source_type, trust_level=source.trust_level,
                project_ref=None,
                section_ref=(reference.section or reference.clause or (source.extracted_refs[0] if source.extracted_refs else None)),
                page_ref=reference.page or None, text=content, summary=" ".join(content.split())[:240],
                tags=metadata["tags"], created_at=datetime.now(timezone.utc).isoformat(), metadata=metadata,
            ))
    _write_chunks(all_chunks, Path(rag_index_path), append=False)
    return all_chunks


def read_rag_index(*, index_path: str | Path = DEFAULT_RAG_PATH) -> list[RagChunk]:
    path = Path(index_path)
    if not path.exists():
        return []
    chunks = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    for line in lines:
        try:
            chunk = RagChunk.from_dict(json.loads(line))
            if chunk.chunk_id and chunk.text:
                chunks.append(chunk)
        except (json.JSONDecodeError, TypeError, ValueError, KeyError):
            continue
    return chunks


def _source_text(path_or_url: str | None) -> str:
    if not path_or_url or str(path_or_url).startswith(("http://", "https://")):
        return ""
    path = (REPO_ROOT / path_or_url).resolve()
    try:
        path.relative_to(REPO_ROOT.resolve())
    except ValueError:
        return ""
    if any(part.lower() in EXCLUDED_PARTS for part in path.parts) or path.name.lower().startswith(".env"):
        return ""
    if path.suffix.lower() not in SAFE_TEXT_EXTENSIONS or not path.exists() or path.stat().st_size > MAX_SOURCE_BYTES:
        return ""
    try:
        return "\n".join(line for line in path.read_text(encoding="utf-8", errors="ignore").splitlines() if not _SECRET_LINE.search(line))
    except OSError:
        return ""


def _write_chunks(chunks: list[RagChunk], path: Path, *, append: bool) -> None:
    if not chunks and append:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with path.open(mode, encoding="utf-8", newline="\n") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk.to_dict(), ensure_ascii=False, separators=(",", ":")) + "\n")
