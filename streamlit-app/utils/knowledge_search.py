"""Lightweight, secret-aware keyword search over local AICOS documents."""

from __future__ import annotations

import re
from pathlib import Path

from .analysis_models import KnowledgeSnippet
from .official_sources import source_id_for


SAFE_EXTENSIONS = {".md", ".txt", ".rst", ".sql"}
EXCLUDED_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build",
    ".pytest_cache", ".streamlit", "uploads", "reports",
}
EXCLUDED_NAMES = {".env", ".env.local", "secrets.toml", "site_records.jsonl"}
DEFAULT_MAX_FILE_SIZE = 1_000_000
DEFAULT_SOURCE_DIRS = ("HK-AICOS", "streamlit-app", "buildway-ai-core")

_SECRET_LINE = re.compile(
    r"(?i)(?:api[_-]?key|secret|password|token|authorization)\s*[:=]|bearer\s+[a-z0-9._-]+|sk-[a-z0-9_-]{12,}"
)
_DOMAIN_HINTS = {
    "safety": {"safety", "安全", "危險", "高空", "臨邊", "護欄", "安全帶", "棚架", "risk"},
    "law": {"law", "regulation", "ordinance", "法例", "規例", "條例", "cap."},
    "document": {"document", "manual", "procedure", "文件", "手冊", "程序", "指引"},
}


def search_local_knowledge(
    query: str,
    *,
    project_root: str | Path | None = None,
    limit: int = 5,
    include_python: bool = False,
    max_file_size: int = DEFAULT_MAX_FILE_SIZE,
) -> list[KnowledgeSnippet]:
    """Search safe local text sources and return ranked contextual snippets."""
    query = str(query or "").strip()
    if not query or limit <= 0:
        return []
    root = Path(project_root) if project_root else Path(__file__).resolve().parents[2]
    extensions = SAFE_EXTENSIONS | ({".py"} if include_python else set())
    terms = _query_terms(query)
    candidates: list[KnowledgeSnippet] = []

    for source_dir_name in DEFAULT_SOURCE_DIRS:
        source_dir = root / source_dir_name
        if not source_dir.exists():
            continue
        for path in _safe_files(source_dir, extensions, max_file_size):
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except (OSError, UnicodeError):
                continue
            score = _score(path, text, query.lower(), terms)
            if score <= 0:
                continue
            relative = path.relative_to(root).as_posix()
            candidates.append(
                KnowledgeSnippet(
                    title=_title_for(path, text),
                    path=_short_path(relative),
                    snippet=_make_snippet(text, query, terms),
                    score=round(score, 2),
                    source_type="local_internal",
                    source_id=source_id_for(relative, "local"),
                    trust_level="local_internal",
                    provider=f"local_keyword:{_source_type(relative)}",
                )
            )

    candidates.sort(key=lambda item: (-item.score, item.path.lower()))
    return candidates[:limit]


def _safe_files(source_dir: Path, extensions: set[str], max_file_size: int):
    try:
        paths = source_dir.rglob("*")
        for path in paths:
            if not path.is_file() or path.suffix.lower() not in extensions:
                continue
            lowered_parts = {part.lower() for part in path.parts}
            if lowered_parts & EXCLUDED_DIRS:
                continue
            name = path.name.lower()
            if name in EXCLUDED_NAMES or name.startswith(".env"):
                continue
            try:
                if path.stat().st_size > max_file_size:
                    continue
            except OSError:
                continue
            yield path
    except OSError:
        return


def _query_terms(query: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9_./-]+|[\u3400-\u9fff]+", query.lower())
    domain_terms = [
        hint
        for hints in _DOMAIN_HINTS.values()
        for hint in hints
        if len(hint) >= 2 and hint in query.lower()
    ]
    return list(dict.fromkeys([*domain_terms, *(token for token in tokens if len(token) >= 2)]))[:16]


def _score(path: Path, text: str, query: str, terms: list[str]) -> float:
    lowered = text.lower()
    path_text = path.as_posix().lower()
    score = 0.0
    if query in lowered:
        score += 12.0
    if query in path_text:
        score += 15.0
    matched_terms = 0
    for term in terms:
        count = min(lowered.count(term), 8)
        if count:
            matched_terms += 1
            score += 2.0 + count * 0.6
        if term in path_text:
            score += 4.0
    if matched_terms > 1:
        score += matched_terms * 1.5
    for hints in _DOMAIN_HINTS.values():
        if any(hint in query for hint in hints) and any(hint in (path_text + " " + lowered[:3000]) for hint in hints):
            score += 3.0
    return score


def _make_snippet(text: str, query: str, terms: list[str], radius: int = 220) -> str:
    lowered = text.lower()
    positions = [lowered.find(query.lower())]
    positions.extend(lowered.find(term) for term in terms)
    valid = [position for position in positions if position >= 0]
    start_at = min(valid) if valid else 0
    start = max(0, start_at - radius)
    end = min(len(text), start_at + radius * 2)
    snippet = " ".join(text[start:end].split())
    safe_lines = [part for part in re.split(r"(?<=[。.!?])\s+", snippet) if not _SECRET_LINE.search(part)]
    cleaned = " ".join(safe_lines).strip()
    if not cleaned:
        return "[相關內容包含敏感設定，已隱藏]"
    return ("…" if start else "") + cleaned[:600] + ("…" if end < len(text) else "")


def _title_for(path: Path, text: str) -> str:
    for line in text.splitlines()[:20]:
        stripped = line.strip().lstrip("#").strip()
        if stripped and not _SECRET_LINE.search(stripped):
            return stripped[:100]
    return path.stem.replace("_", " ").replace("-", " ")[:100]


def _short_path(relative: str, max_length: int = 100) -> str:
    if len(relative) <= max_length:
        return relative
    parts = relative.split("/")
    return f"{parts[0]}/…/{parts[-1]}"


def _source_type(relative: str) -> str:
    first = relative.split("/", 1)[0].lower()
    if first == "hk-aicos":
        return "hk_aicos_document"
    if first == "buildway-ai-core":
        return "ai_core_document"
    return "streamlit_document"
