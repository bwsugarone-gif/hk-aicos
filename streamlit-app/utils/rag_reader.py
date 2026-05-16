# -*- coding: utf-8 -*-
"""
utils/rag_reader.py
HK-AICOS Phase 2.5F — RAG Document Reader

Reads from two sources:
  1. HK-AICOS knowledge base (HK-AICOS/regulations/, agents/, sop/, etc.)
  2. rag_documents/ project library (via rag_manager keyword search)

Phase 3 upgrade: replace rag_manager.search() with Qdrant vector queries.
"""

import sys
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent.parent  # project root

KNOWLEDGE_BASE_PATHS = {
    "regulations": BASE_DIR / "HK-AICOS" / "regulations",
    "agents":      BASE_DIR / "HK-AICOS" / "agents",
    "sop":         BASE_DIR / "HK-AICOS" / "sop",
    "rag":         BASE_DIR / "HK-AICOS" / "rag",
    "governance":  BASE_DIR / "HK-AICOS" / "governance",
}

# Regulation file mapping (HK-AICOS knowledge base)
REGULATION_FILES = {
    "hk-bd-layer":     "hk-bd-layer.md",
    "hk-emsd-layer":   "hk-emsd-layer.md",
    "hk-epd-layer":    "hk-epd-layer.md",
    "hk-labour-layer": "hk-labour-layer.md",
    "hk-fsd-layer":    "hk-fsd-layer.md",
    "hk-wsd-layer":    "hk-wsd-layer.md",
    "hk-landsd-layer": "hk-landsd-layer.md",
    "hk-hyd-layer":    "hk-hyd-layer.md",
    "hk-cedd-layer":   "hk-cedd-layer.md",
    "hk-dsd-layer":    "hk-dsd-layer.md",
    "hk-td-layer":     "hk-td-layer.md",
    "hk-legal-layer":  "hk-legal-layer.md",
}

# Agent regulation key → HK-AICOS regulation file key mapping
_AGENT_REG_MAP = {
    "Labour":  "hk-labour-layer",
    "FSD":     "hk-fsd-layer",
    "BD":      "hk-bd-layer",
    "EMSD":    "hk-emsd-layer",
    "EPD":     "hk-epd-layer",
    "WSD":     "hk-wsd-layer",
    "DSD":     "hk-dsd-layer",
    "HyD":     "hk-hyd-layer",
    "CEDD":    "hk-cedd-layer",
    "GEO":     "hk-cedd-layer",
    "HK Legal":"hk-legal-layer",
    "LandSD":  "hk-landsd-layer",
    "TD":      "hk-td-layer",
}


# ── HK-AICOS knowledge base readers ──────────────────────────────────────────
def read_markdown_file(file_path: Path, max_chars: int = 3000) -> str:
    """Read a markdown file and return its content (truncated if needed)."""
    try:
        if file_path.exists():
            content = file_path.read_text(encoding="utf-8")
            if len(content) > max_chars:
                content = content[:max_chars] + "\n\n[... truncated ...]"
            return content
        return f"[File not found: {file_path}]"
    except Exception as e:
        return f"[Error reading {file_path.name}: {str(e)}]"


def get_regulation_context(regulation_keys: list, max_chars_each: int = 1500) -> str:
    """
    Read regulation documents for the given agent regulation keys.
    Maps agent keys (e.g. "Labour") to HK-AICOS file keys.
    """
    contexts = []
    reg_dir  = KNOWLEDGE_BASE_PATHS["regulations"]

    for key in regulation_keys:
        # Try direct key first, then mapped key
        file_key = _AGENT_REG_MAP.get(key, key.lower().replace(" ", "-"))
        filename = REGULATION_FILES.get(file_key)
        if not filename:
            # Try hk-{key}-layer pattern
            filename = REGULATION_FILES.get(f"hk-{key.lower()}-layer")
        if filename:
            file_path = reg_dir / filename
            content   = read_markdown_file(file_path, max_chars=max_chars_each)
            if "[File not found" not in content:
                contexts.append(f"### {key}\n{content}")

    return "\n\n".join(contexts) if contexts else ""


def get_governance_rules() -> str:
    """Read AI governance rules for inclusion in all prompts."""
    gov_path = KNOWLEDGE_BASE_PATHS["governance"] / "AI_GOVERNANCE.md"
    return read_markdown_file(gov_path, max_chars=2000)


def get_master_system_summary() -> str:
    """Read MASTER_SYSTEM.md summary for context."""
    master_path = BASE_DIR / "HK-AICOS" / "MASTER_SYSTEM.md"
    return read_markdown_file(master_path, max_chars=2000)


def get_sop_context(sop_name: str) -> str:
    """Read a specific SOP document."""
    sop_path = KNOWLEDGE_BASE_PATHS["sop"] / f"{sop_name}.md"
    return read_markdown_file(sop_path, max_chars=2000)


def list_available_regulations() -> list:
    """List all available regulation files."""
    reg_dir = KNOWLEDGE_BASE_PATHS["regulations"]
    if reg_dir.exists():
        return [f.stem for f in reg_dir.glob("*.md")]
    return []


def check_knowledge_base_status() -> dict:
    """Check which knowledge base directories exist and are populated."""
    status = {}
    for name, path in KNOWLEDGE_BASE_PATHS.items():
        if path.exists():
            md_files = list(path.glob("*.md"))
            status[name] = {"exists": True, "file_count": len(md_files)}
        else:
            status[name] = {"exists": False, "file_count": 0}
    return status


# ── rag_documents/ project library search ────────────────────────────────────
def search_rag_documents(
    regulation_keys: list,
    top_k: int = 3,
) -> tuple[list, str]:
    """
    Search rag_documents/ for documents relevant to the given regulation keys.

    Returns:
        (matched_docs, context_text)
        matched_docs: list of metadata dicts (for UI display as "參考文件")
        context_text: formatted text snippet for prompt injection
    """
    try:
        from utils.rag_manager import search_by_regulations, read_document
    except ImportError:
        try:
            from rag_manager import search_by_regulations, read_document
        except ImportError:
            return [], ""

    hits = search_by_regulations(regulation_keys, top_k=top_k)
    if not hits:
        return [], ""

    parts = []
    for doc in hits:
        content = read_document(doc, max_chars=800)
        dept    = doc.get("source_department", "")
        summary = doc.get("summary", "")
        label   = f"{doc['file_name']}" + (f" [{dept}]" if dept else "")
        snippet = content or summary or "(無文字預覽)"
        parts.append(f"文件：{label}\n{snippet}")

    context_text = "\n\n---\n\n".join(parts)
    return hits, context_text


# ── Main public API ───────────────────────────────────────────────────────────
def build_rag_context(regulation_keys: list) -> str:
    """
    Build combined RAG context from:
      1. AI governance rules
      2. HK-AICOS regulation knowledge base
      3. rag_documents/ project library (keyword search)

    Used to enrich AI analysis prompts via agent_router.build_prompt_from_agents().
    """
    parts = []

    # 1. Governance rules
    gov = get_governance_rules()
    if gov and "[File not found" not in gov:
        parts.append("## AI Governance Rules\n" + gov)

    # 2. HK-AICOS regulation knowledge base
    reg_context = get_regulation_context(regulation_keys)
    if reg_context:
        parts.append("## Relevant Hong Kong Regulations\n" + reg_context)

    # 3. rag_documents/ project library
    try:
        _, rag_doc_context = search_rag_documents(regulation_keys, top_k=3)
        if rag_doc_context:
            parts.append("## 參考文件庫\n" + rag_doc_context)
    except Exception as e:
        print(f"[rag_reader] WARNING: rag_documents search failed: {e}", file=sys.stderr)

    return "\n\n".join(parts)


def get_matched_rag_docs(regulation_keys: list, top_k: int = 3) -> list:
    """
    Return list of matched rag_documents metadata dicts for UI display.
    Used by pages/2_Report.py and pages/3_History.py to show "參考文件".
    """
    try:
        matched_docs, _ = search_rag_documents(regulation_keys, top_k=top_k)
        return matched_docs
    except Exception:
        return []
