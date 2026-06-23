"""Ask-AICOS context built from drawing analysis + CAD/BIM handoff (Phase 5.10H).

Turns recent drawing documents / pages / handoff items into ``KnowledgeSnippet``
objects so Ask AICOS can answer questions like "呢份圖紙有咩問題？" or
"CAD team 要做咩？" using the specific drawing record rather than generic safety
knowledge.
"""

from __future__ import annotations

import re

from .analysis_models import KnowledgeSnippet
from .drawing_models import ACTION_TYPE_LABELS_ZH, DISCIPLINE_LABELS_ZH, PAGE_TYPE_LABELS_ZH
from .drawing_store import (
    list_recent_drawing_documents,
    read_pages_for_document,
)


def _terms(query: str) -> list[str]:
    text = str(query or "").lower()
    tokens = [term for term in re.findall(r"[a-z0-9_./-]+|[㐀-鿿]+", text) if len(term) >= 2]
    return list(dict.fromkeys(tokens))[:20]


def _document_snippet(document, score: float) -> KnowledgeSnippet:
    disc = "、".join(DISCIPLINE_LABELS_ZH.get(d, d) for d in document.disciplines) or "未確定"
    types = "、".join(PAGE_TYPE_LABELS_ZH.get(t, t) for t in document.page_types if t != "unknown") or "未分類"
    issues = "；".join(document.drawing_issues[:4]) or "未發現明顯問題"
    missing = "；".join(document.missing_information[:4]) or "暫無"
    snippet = (
        f"{document.summary} 專業：{disc}；類型：{types}。"
        f" 主要問題：{issues}。 待補資料：{missing}。"
    )
    return KnowledgeSnippet(
        title=f"圖紙分析：{document.source_file_name or document.document_id}",
        path=f"AICOS Drawing / {document.document_id}",
        snippet=snippet,
        score=score,
        source_type="drawing_analysis",
        source_id=f"drawing:{document.document_id}",
        trust_level="uploaded_record",
        provider="drawing_store",
    )


def _handoff_snippet(document, score: float) -> KnowledgeSnippet:
    lines = []
    for item in document.handoff_items[:8]:
        label = ACTION_TYPE_LABELS_ZH.get(item.action_type, item.action_type)
        team = {"cad": "CAD", "bim": "BIM", "both": "CAD/BIM"}.get(item.target_team, item.target_team)
        page = f"P{item.page_number} " if item.page_number else ""
        detail = f"（需交付：{item.required_output}）" if getattr(item, "required_output", "") else ""
        lines.append(f"[{team}｜{label}] {page}{item.title}{detail}")
    snippet = "；".join(lines) or "暫無 CAD/BIM 交接事項。"
    return KnowledgeSnippet(
        title=f"CAD/BIM 交接清單：{document.source_file_name or document.document_id}",
        path=f"AICOS Drawing Handoff / {document.document_id}",
        snippet=snippet,
        score=score,
        source_type="cad_bim_handoff",
        source_id=f"drawing-handoff:{document.document_id}",
        trust_level="uploaded_record",
        provider="drawing_store",
    )


NO_DRAWING_GUIDANCE = (
    "未找到任何圖紙分析記錄。請先到「圖紙分析」頁上載 PDF 或圖片圖紙並完成分析，"
    "之後再提問圖紙問題、CAD/BIM 交接或需要 site verify 的頁面。"
)


def recent_drawing_summary(project_ref: str | None = None, *, limit: int = 5) -> dict[str, int | bool]:
    """Lightweight summary of recent drawing analyses for Ask context basis."""
    documents = list_recent_drawing_documents(project_ref, limit=max(1, limit))
    return {
        "found": bool(documents),
        "document_count": len(documents),
        "handoff_count": sum(len(doc.handoff_items) for doc in documents),
        "page_count": sum(int(doc.analyzed_page_count or 0) for doc in documents),
    }


def build_no_drawing_guidance(score: float = 9.0) -> KnowledgeSnippet:
    """Guidance snippet used when a drawing question has no analysis to draw on."""
    return KnowledgeSnippet(
        title="尚未有圖紙分析記錄",
        path="AICOS Drawing / none",
        snippet=NO_DRAWING_GUIDANCE,
        score=score,
        source_type="drawing_guidance",
        source_id="drawing:none",
        trust_level="uploaded_record",
        provider="drawing_store",
    )


def build_drawing_context(
    query: str,
    project_ref: str | None = None,
    *,
    intent_type: str = "drawing_question",
    limit: int = 5,
) -> list[KnowledgeSnippet]:
    """Return drawing / handoff snippets ranked for the question.

    ``intent_type`` of ``cad_bim_handoff_question`` puts the handoff list first.
    """
    documents = list_recent_drawing_documents(project_ref, limit=max(5, limit))
    if not documents:
        return []

    terms = _terms(query)
    ranked = []
    for document in documents:
        searchable = " ".join([
            document.summary,
            " ".join(document.drawing_issues),
            " ".join(document.missing_information),
            " ".join(item.title for item in document.handoff_items),
            document.source_file_name or "",
        ]).lower()
        score = sum(1 for term in terms if term in searchable)
        ranked.append((score, document.updated_at or document.created_at, document))
    ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)

    snippets: list[KnowledgeSnippet] = []
    handoff_first = intent_type == "cad_bim_handoff_question"
    for rank, (_, _, document) in enumerate(ranked[: max(1, limit)]):
        base = float(max(1, limit - rank)) + 6.0
        doc_snip = _document_snippet(document, base)
        handoff_snip = _handoff_snippet(document, base + (1.0 if handoff_first else -0.5))
        if handoff_first:
            snippets.extend([handoff_snip, doc_snip])
        else:
            snippets.extend([doc_snip, handoff_snip])
    return snippets[: max(1, limit) * 2]
