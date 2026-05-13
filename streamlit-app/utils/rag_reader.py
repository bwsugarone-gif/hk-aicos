"""
rag_reader.py
HK-AICOS Phase 2.0 - RAG Document Reader

Reads Markdown documents from the HK-AICOS knowledge base.
Phase 2.0: Manual/file-based reading (no vector DB yet).
Phase 2.5: Will be replaced with vector DB queries.
"""

import os
from pathlib import Path

# Base path to HK-AICOS knowledge base (relative to streamlit-app/)
BASE_DIR = Path(__file__).parent.parent.parent  # project root

KNOWLEDGE_BASE_PATHS = {
    "regulations": BASE_DIR / "HK-AICOS" / "regulations",
    "agents": BASE_DIR / "HK-AICOS" / "agents",
    "sop": BASE_DIR / "HK-AICOS" / "sop",
    "rag": BASE_DIR / "HK-AICOS" / "rag",
    "governance": BASE_DIR / "HK-AICOS" / "governance",
}

# Regulation file mapping
REGULATION_FILES = {
    "hk-bd-layer": "hk-bd-layer.md",
    "hk-emsd-layer": "hk-emsd-layer.md",
    "hk-epd-layer": "hk-epd-layer.md",
    "hk-labour-layer": "hk-labour-layer.md",
    "hk-fsd-layer": "hk-fsd-layer.md",
    "hk-wsd-layer": "hk-wsd-layer.md",
    "hk-landsd-layer": "hk-landsd-layer.md",
    "hk-hyd-layer": "hk-hyd-layer.md",
    "hk-cedd-layer": "hk-cedd-layer.md",
    "hk-dsd-layer": "hk-dsd-layer.md",
    "hk-td-layer": "hk-td-layer.md",
    "hk-legal-layer": "hk-legal-layer.md",
}


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
    Read regulation documents for the given keys.
    Returns combined context string for prompt injection.
    """
    contexts = []
    reg_dir = KNOWLEDGE_BASE_PATHS["regulations"]

    for key in regulation_keys:
        filename = REGULATION_FILES.get(key)
        if filename:
            file_path = reg_dir / filename
            content = read_markdown_file(file_path, max_chars=max_chars_each)
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


def build_rag_context(regulation_keys: list) -> str:
    """
    Build combined RAG context from regulations and governance rules.
    Used to enrich AI analysis prompts.
    """
    parts = []

    # Add governance rules
    gov = get_governance_rules()
    if gov and "[File not found" not in gov:
        parts.append("## AI Governance Rules\n" + gov)

    # Add relevant regulations
    reg_context = get_regulation_context(regulation_keys)
    if reg_context:
        parts.append("## Relevant Hong Kong Regulations\n" + reg_context)

    return "\n\n".join(parts)


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
