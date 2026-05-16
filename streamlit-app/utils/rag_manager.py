# -*- coding: utf-8 -*-
"""
utils/rag_manager.py
HK-AICOS Phase 2.5F — RAG Foundation Layer

Lightweight JSON-based document index for the rag_documents/ library.
No vector DB, no embeddings — keyword matching only.
Phase 3 upgrade path: swap search() for Qdrant vector queries.

Folder structure expected under streamlit-app/rag_documents/:
    regulations/
    codes_of_practice/
    practice_notes/
    technical_circulars/
    guidelines/
    forms_checklists/
    company_sop/
    project_docs/
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
_BASE_DIR    = Path(__file__).parent.parent          # streamlit-app/
RAG_DIR      = _BASE_DIR / "rag_documents"
INDEX_FILE   = RAG_DIR / "rag_index.json"

# Supported document extensions
SUPPORTED_EXTENSIONS = {".md", ".txt", ".pdf"}

# Category display names (folder → label)
CATEGORY_LABELS = {
    "regulations":        "法規 / Regulations",
    "codes_of_practice":  "實務守則 / Codes of Practice",
    "practice_notes":     "實務備考 / Practice Notes",
    "technical_circulars":"技術通告 / Technical Circulars",
    "guidelines":         "指引 / Guidelines",
    "forms_checklists":   "表格及核查清單 / Forms & Checklists",
    "company_sop":        "公司 SOP / Company SOP",
    "project_docs":       "項目文件 / Project Documents",
}

# Department keyword → source_department mapping (for auto-tagging)
_DEPT_KEYWORDS = [
    (["labour", "勞工", "工人安全", "工傷", "工資"],                    "勞工處"),
    (["bd", "屋宇署", "building department", "buildings ordinance"],    "屋宇署"),
    (["fsd", "消防", "fire services", "fire safety"],                   "消防處"),
    (["emsd", "機電", "electrical", "mechanical", "lift", "escalator"], "EMSD"),
    (["wsd", "水務", "water supply", "waterworks"],                     "水務署"),
    (["dsd", "渠務", "drainage", "sewerage"],                           "渠務署"),
    (["hyd", "路政", "highway", "road works"],                          "路政署"),
    (["td", "運輸", "transport", "traffic"],                            "運輸署"),
    (["landsd", "地政", "land registry", "lease"],                      "地政總署"),
    (["epd", "環保", "environmental", "noise", "waste"],                "環保署"),
    (["cedd", "geo", "slope", "斜坡", "土力", "geotechnical"],          "CEDD / GEO"),
]


# ── Metadata schema ───────────────────────────────────────────────────────────
def _empty_metadata(file_path: Path, category: str) -> dict:
    """Return a metadata record with all required fields."""
    return {
        "file_name":         file_path.name,
        "file_type":         file_path.suffix.lstrip(".").lower(),
        "category":          category,
        "source_department": _guess_department(file_path.name),
        "version_date":      "",
        "uploaded_at":       datetime.now(timezone.utc).isoformat(),
        "language":          _guess_language(file_path.name),
        "summary":           "",
        "keywords":          [],
        "path":              str(file_path.relative_to(_BASE_DIR)),
    }


def _guess_department(filename: str) -> str:
    lower = filename.lower()
    for keywords, dept in _DEPT_KEYWORDS:
        if any(k in lower for k in keywords):
            return dept
    return ""


def _guess_language(filename: str) -> str:
    lower = filename.lower()
    if any(c in lower for c in ["tc", "zh", "hk", "chinese", "繁"]):
        return "zh-Hant"
    if "en" in lower or "english" in lower:
        return "en"
    return "zh-Hant"   # default for HK engineering docs


def _extract_keywords_from_text(text: str, max_keywords: int = 20) -> list:
    """Very lightweight keyword extraction — just unique CJK words + English tokens."""
    # CJK 2-4 char sequences
    cjk = re.findall(r"[\u4e00-\u9fff]{2,4}", text)
    # English words 4+ chars
    eng = re.findall(r"[A-Za-z]{4,}", text)
    combined = list(dict.fromkeys(cjk[:max_keywords//2] + [w.lower() for w in eng[:max_keywords//2]]))
    return combined[:max_keywords]


def _read_text_preview(file_path: Path, max_chars: int = 500) -> str:
    """Read first N chars of a text/markdown file for keyword extraction."""
    if file_path.suffix.lower() == ".pdf":
        return ""   # PDF text extraction not done at index time (no extra deps)
    for enc in ("utf-8", "utf-8-sig", "big5", "cp950", "latin-1"):
        try:
            text = file_path.read_text(encoding=enc)
            return text[:max_chars]
        except Exception:
            continue
    return ""


# ── Index management ──────────────────────────────────────────────────────────
def load_index() -> dict:
    """Load rag_index.json. Returns empty index if not found."""
    if INDEX_FILE.exists():
        try:
            return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[rag_manager] WARNING: could not load index: {e}", file=sys.stderr)
    return {"version": "2.5F", "updated_at": "", "documents": []}


def save_index(index: dict) -> None:
    """Save index to rag_index.json."""
    index["updated_at"] = datetime.now(timezone.utc).isoformat()
    RAG_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_FILE.write_text(
        json.dumps(index, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def scan_and_index() -> dict:
    """
    Scan all rag_documents/ subfolders and rebuild rag_index.json.
    Preserves existing metadata (summary, version_date, keywords) for
    files already in the index — only adds new files.

    Returns the updated index dict.
    """
    existing = load_index()
    existing_map = {doc["file_name"]: doc for doc in existing.get("documents", [])}

    documents = []
    for category in CATEGORY_LABELS:
        folder = RAG_DIR / category
        if not folder.exists():
            continue
        for file_path in sorted(folder.iterdir()):
            if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            if file_path.name.startswith("."):
                continue

            if file_path.name in existing_map:
                # Keep existing metadata, just refresh path
                doc = dict(existing_map[file_path.name])
                doc["path"] = str(file_path.relative_to(_BASE_DIR))
            else:
                # New file — auto-generate metadata
                doc = _empty_metadata(file_path, category)
                preview = _read_text_preview(file_path)
                if preview:
                    doc["keywords"] = _extract_keywords_from_text(preview)
                    # Use first non-empty line as summary if none set
                    first_line = next(
                        (ln.strip() for ln in preview.splitlines() if ln.strip()),
                        ""
                    )
                    doc["summary"] = first_line[:120]

            documents.append(doc)

    index = {
        "version":    "2.5F",
        "updated_at": "",
        "documents":  documents,
    }
    save_index(index)
    print(f"[rag_manager] Index rebuilt: {len(documents)} documents", file=sys.stderr)
    return index


# ── Search ────────────────────────────────────────────────────────────────────
def search(
    query: str,
    top_k: int = 5,
    category_filter: str = "",
    department_filter: str = "",
) -> list:
    """
    Keyword search over the RAG index.
    Returns list of matching document metadata dicts, ranked by match count.

    Args:
        query:             Free-text query (Chinese or English).
        top_k:             Max results to return.
        category_filter:   Limit to a specific category folder name.
        department_filter: Limit to a specific source_department.

    Returns:
        List of metadata dicts with an added "_score" field.

    Phase 3 upgrade: replace this function body with Qdrant vector search.
    """
    index = load_index()
    docs  = index.get("documents", [])

    if not docs:
        return []

    # Tokenise query
    query_lower = query.lower()
    cjk_tokens  = re.findall(r"[\u4e00-\u9fff]{2,4}", query)
    eng_tokens  = [w.lower() for w in re.findall(r"[A-Za-z]{3,}", query)]
    all_tokens  = cjk_tokens + eng_tokens

    results = []
    for doc in docs:
        # Apply filters
        if category_filter and doc.get("category") != category_filter:
            continue
        if department_filter and doc.get("source_department") != department_filter:
            continue

        # Score: count token hits across searchable fields
        searchable = " ".join([
            doc.get("file_name", ""),
            doc.get("summary", ""),
            doc.get("source_department", ""),
            doc.get("category", ""),
            " ".join(doc.get("keywords", [])),
        ]).lower()

        score = sum(1 for t in all_tokens if t in searchable)
        # Bonus: exact query substring match
        if query_lower in searchable:
            score += 3

        if score > 0:
            results.append({**doc, "_score": score})

    results.sort(key=lambda x: x["_score"], reverse=True)
    return results[:top_k]


def search_by_regulations(regulation_keys: list, top_k: int = 5) -> list:
    """
    Search for documents relevant to a list of regulation keys
    (e.g. ["Labour", "FSD", "BD"]).
    Used by rag_reader to enrich agent prompts.
    """
    if not regulation_keys:
        return []
    query = " ".join(regulation_keys)
    return search(query, top_k=top_k)


def get_document_by_name(file_name: str) -> dict | None:
    """Return metadata for a specific file by name."""
    index = load_index()
    for doc in index.get("documents", []):
        if doc["file_name"] == file_name:
            return doc
    return None


def get_all_documents(category: str = "") -> list:
    """Return all indexed documents, optionally filtered by category."""
    index = load_index()
    docs  = index.get("documents", [])
    if category:
        docs = [d for d in docs if d.get("category") == category]
    return docs


def get_index_stats() -> dict:
    """Return summary stats about the current index."""
    index = load_index()
    docs  = index.get("documents", [])
    by_cat = {}
    for doc in docs:
        cat = doc.get("category", "unknown")
        by_cat[cat] = by_cat.get(cat, 0) + 1
    return {
        "total":      len(docs),
        "updated_at": index.get("updated_at", ""),
        "by_category": by_cat,
    }


# ── Read document content ─────────────────────────────────────────────────────
def read_document(doc: dict, max_chars: int = 2000) -> str:
    """
    Read the text content of a document from the index.
    Returns empty string for PDFs (binary) or missing files.
    """
    rel_path = doc.get("path", "")
    if not rel_path:
        return ""
    file_path = _BASE_DIR / rel_path
    if not file_path.exists():
        return ""
    if file_path.suffix.lower() == ".pdf":
        return f"[PDF: {doc['file_name']} — 請直接開啟文件查閱]"
    preview = _read_text_preview(file_path, max_chars=max_chars)
    return preview


# ── CLI helper ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys as _sys
    print("Scanning rag_documents/ and rebuilding index...")
    idx = scan_and_index()
    stats = get_index_stats()
    print(f"Total documents: {stats['total']}")
    print(f"By category: {stats['by_category']}")
    print(f"Index saved to: {INDEX_FILE}")

    if len(_sys.argv) > 1:
        q = " ".join(_sys.argv[1:])
        print(f"\nSearch: '{q}'")
        hits = search(q)
        for h in hits:
            print(f"  [{h['_score']}] {h['file_name']} ({h['category']}) — {h['summary'][:60]}")
