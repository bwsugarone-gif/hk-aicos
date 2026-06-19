"""Safe local knowledge scanner and compact JSONL metadata index."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .knowledge_models import KnowledgeSource


APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_ROOT.parent
DEFAULT_INDEX_PATH = APP_ROOT / "data" / "knowledge_index.jsonl"
DEFAULT_KNOWLEDGE_DIRS = (
    REPO_ROOT / "HK-AICOS" / "rag",
    REPO_ROOT / "regulations",
    APP_ROOT / "knowledge",
    REPO_ROOT / "docs",
)
SAFE_TEXT_EXTENSIONS = {".md", ".txt", ".rst"}
SAFE_METADATA_EXTENSIONS = SAFE_TEXT_EXTENSIONS | {".pdf"}
MAX_TEXT_BYTES = 1_000_000
_SECRET_LINE = re.compile(r"(?i)(api[_-]?key|secret|password|token|authorization)\s*[:=]|sk-[a-z0-9_-]{8,}")


def scan_local_knowledge_sources(
    source_dirs: Iterable[str | Path] | None = None,
) -> list[KnowledgeSource]:
    now = datetime.now(timezone.utc).isoformat()
    sources = []
    for directory in [Path(item) for item in (source_dirs or DEFAULT_KNOWLEDGE_DIRS)]:
        if not directory.exists():
            continue
        try:
            paths = sorted(directory.rglob("*"), key=lambda item: item.as_posix().lower())
        except OSError:
            continue
        for path in paths:
            if not path.is_file() or path.suffix.lower() not in SAFE_METADATA_EXTENSIONS:
                continue
            try:
                relative = path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
            except (OSError, ValueError):
                relative = path.as_posix()
            text = _safe_text(path) if path.suffix.lower() in SAFE_TEXT_EXTENSIONS else ""
            title = _title(path, text)
            trust = _trust_level(relative, text)
            sources.append(
                KnowledgeSource(
                    source_id="ksrc_" + hashlib.sha256(relative.encode("utf-8", errors="ignore")).hexdigest()[:20],
                    title=title,
                    source_type=_source_type(relative, trust),
                    path_or_url=relative,
                    trust_level=trust,
                    jurisdiction="HK" if _is_hk(relative + " " + text[:1000]) else None,
                    trade_tags=_trade_tags(relative + " " + text[:3000]),
                    topic_tags=_topic_tags(relative + " " + text[:3000]),
                    summary=_summary(text) if text else f"{path.suffix.upper().lstrip('.')} 文件；本階段只建立檔名及路徑索引。",
                    extracted_refs=extract_reference_hints(text),
                    last_indexed_at=now,
                )
            )
    return sources


def build_or_refresh_knowledge_index(
    source_dirs: Iterable[str | Path] | None = None,
    *,
    index_path: str | Path = DEFAULT_INDEX_PATH,
) -> list[KnowledgeSource]:
    sources = scan_local_knowledge_sources(source_dirs)
    path = Path(index_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(json.dumps(item.to_dict(), ensure_ascii=False, separators=(",", ":")) + "\n" for item in sources)
    path.write_text(payload, encoding="utf-8", newline="\n")
    return sources


def read_knowledge_index(*, index_path: str | Path = DEFAULT_INDEX_PATH) -> list[KnowledgeSource]:
    path = Path(index_path)
    if not path.exists():
        return []
    sources = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    for line in lines:
        try:
            sources.append(KnowledgeSource.from_dict(json.loads(line)))
        except (json.JSONDecodeError, TypeError, ValueError, KeyError):
            continue
    return sources


def extract_reference_hints(text: str) -> list[str]:
    patterns = (
        r"(?:chapter|第)\s*([0-9A-Z.-]+)\s*(?:章)?",
        r"(?:section|第)\s*([0-9A-Z.-]+)\s*(?:節)?",
        r"(?:clause|第)\s*([0-9A-Z.-]+)\s*(?:條)?",
        r"(?:page|p\.)\s*([0-9]+)",
    )
    hints = []
    for pattern in patterns:
        for match in re.finditer(pattern, str(text or ""), flags=re.IGNORECASE):
            hints.append(match.group(0).strip())
    return list(dict.fromkeys(hints))[:20]


def _safe_text(path: Path) -> str:
    try:
        if path.stat().st_size > MAX_TEXT_BYTES:
            return ""
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except (OSError, UnicodeError):
        return ""
    return "\n".join(line for line in lines if not _SECRET_LINE.search(line))[:MAX_TEXT_BYTES]


def _title(path: Path, text: str) -> str:
    for line in text.splitlines()[:20]:
        candidate = line.strip().lstrip("#").strip()
        if candidate:
            return candidate[:160]
    return path.stem.replace("_", " ").replace("-", " ")[:160]


def _summary(text: str) -> str:
    return " ".join(text.split())[:1200]


def _trust_level(relative: str, text: str) -> str:
    lowered = (relative + " " + text[:1500]).lower()
    if any(term in lowered for term in ("labour.gov.hk", "bd.gov.hk", "emsd.gov.hk", "elegislation.gov.hk", "gov.hk")):
        return "official"
    if any(term in lowered for term in ("cic.hk", "construction industry council", "建造業議會")):
        return "trusted"
    if any(part in relative.lower() for part in ("docs/", "hk-aicos/", "streamlit-app/knowledge")):
        return "internal"
    return "unverified"


def _source_type(relative: str, trust: str) -> str:
    if trust == "official":
        return "official"
    if "sop" in relative.lower():
        return "company_sop"
    return "project_note" if "project" in relative.lower() else "company_sop"


def _is_hk(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in ("hong kong", "香港", "gov.hk", "cic.hk"))


def _trade_tags(text: str) -> list[str]:
    lowered = text.lower()
    mapping = {"安全": ("safety", "安全"), "機電": ("electrical", "機電"), "結構": ("structural", "結構"), "熱工": ("hot work", "熱工", "火花")}
    return [label for label, terms in mapping.items() if any(term in lowered for term in terms)]


def _topic_tags(text: str) -> list[str]:
    lowered = text.lower()
    mapping = {"法例": ("law", "regulation", "法例"), "指引": ("guidance", "code of practice", "指引"), "風險": ("risk", "hazard", "風險")}
    return [label for label, terms in mapping.items() if any(term in lowered for term in terms)]
