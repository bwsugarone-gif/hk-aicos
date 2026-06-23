"""Intent-aware context selection for Ask AICOS and Workspace quick ask."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .analysis_models import KnowledgeSnippet, SearchResult
from .ask_intent_router import AskIntent, classify_ask_intent
from .drawing_context import (
    build_drawing_context,
    build_no_drawing_guidance,
    recent_drawing_summary,
)
from .followup_store import build_followup_context, list_followups
from .knowledge_retriever import build_knowledge_pack_context
from .knowledge_search import search_local_knowledge
from .knowledge_tracker import build_knowledge_context
from .memory_indexer import build_project_memory_context
from .project_memory_store import read_all_memory
from .query_expander import HOT_WORK_QUERY_TERMS, WORK_AT_HEIGHT_QUERY_TERMS, safety_query_profile
from .rag_retriever import build_rag_context
from .site_memory import build_memory_context
from .site_record_store import SiteRecordStore


@dataclass
class AskContextSelection:
    intent: AskIntent
    contexts: list[Any] = field(default_factory=list)
    local_contexts: list[Any] = field(default_factory=list)
    web_contexts: list[Any] = field(default_factory=list)
    context_basis: list[str] = field(default_factory=list)
    retrieval_counts: dict[str, int] = field(default_factory=dict)
    recent_image_referenced: bool = False


def build_ask_context_selection(
    question: str,
    *,
    search_scope: str = "all",
    project_ref: str | None = None,
    latest_analysis_result: dict[str, Any] | None = None,
    web_sources: list[SearchResult] | None = None,
    limit: int = 5,
) -> AskContextSelection:
    """Select context by intent so unrelated recent images cannot dominate."""
    has_recent = bool(latest_analysis_result) or bool(_latest_upload_memory(project_ref))
    intent = classify_ask_intent(question, has_recent_upload=has_recent)
    allow_local = search_scope in {"local_knowledge", "all"}
    allow_records = search_scope in {"uploaded_records", "all"}
    allow_web = search_scope in {"web_search", "all"}
    supplied_web = _trusted_first(list(web_sources or [])) if allow_web else []

    knowledge: list[Any] = []
    rag: list[Any] = []
    memories: list[Any] = []
    followups: list[Any] = []
    recent: list[Any] = []
    drawing: list[Any] = []
    drawing_summary: dict[str, Any] | None = None
    visual_evidence_count = 0

    if allow_local and intent.intent_type in {
        "safety_definition_question", "legal_source_question", "sop_howto_question",
        "general_safety_question", "unknown", "recent_image_question",
        "drawing_question", "cad_bim_handoff_question",
    }:
        knowledge.extend(search_local_knowledge(question, limit=limit))
        knowledge.extend(build_knowledge_pack_context(question, limit=limit))
        knowledge.extend(build_knowledge_context(question, project_ref, limit=limit))
        rag.extend(build_rag_context(question, project_ref, limit=limit))

    knowledge = _rank_topic_contexts(knowledge, question)
    rag = _rank_topic_contexts(rag, question)
    supplied_web = _rank_topic_contexts(supplied_web, question, preserve_trust=True)

    if allow_records and intent.intent_type == "recent_image_question":
        session_context, visual_evidence_count = _latest_analysis_context(latest_analysis_result)
        if session_context:
            recent.append(session_context)
        latest_memory = _latest_upload_memory(project_ref)
        if latest_memory:
            recent.append(_project_memory_snippet(latest_memory, score=9.0))
            followups.extend(_followups_for_latest(latest_memory.memory_id, project_ref, limit))
        if not recent:
            latest_record = next(
                (item for item in SiteRecordStore().list_records(limit=10) if item.record_type == "image_analysis"),
                None,
            )
            if latest_record:
                recent.append(KnowledgeSnippet(
                    title=latest_record.title,
                    path=f"地盤記錄 {latest_record.record_id}",
                    snippet=latest_record.content_summary,
                    score=8.0,
                    source_type="uploaded_record",
                    source_id=f"recent-record:{latest_record.record_id}",
                    trust_level="uploaded_record",
                    provider="site_record_store",
                ))

    elif allow_records and intent.intent_type == "followup_question":
        followups.extend(build_followup_context(question, project_ref, limit=limit))
        memories.extend(build_project_memory_context(question, project_ref, limit=min(3, limit)))
        if intent.use_recent_upload:
            latest_memory = _latest_upload_memory(project_ref)
            if latest_memory:
                recent.append(_project_memory_snippet(latest_memory, score=9.0))

    elif allow_records and intent.intent_type == "project_memory_question":
        memories.extend(build_project_memory_context(question, project_ref, limit=limit))
        memories.extend(build_memory_context(question, project_ref, limit=min(3, limit)))
        followups.extend(build_followup_context(question, project_ref, limit=limit))

    elif allow_records and intent.intent_type in {"drawing_question", "cad_bim_handoff_question"}:
        drawing.extend(build_drawing_context(question, project_ref, intent_type=intent.intent_type, limit=limit))
        drawing_summary = recent_drawing_summary(project_ref, limit=limit)
        if not drawing_summary["found"]:
            # No drawing analysis yet -> steer the answer to ask the user to upload.
            drawing.append(build_no_drawing_guidance())
        followups.extend(build_followup_context(question, project_ref, limit=min(3, limit)))
        memories.extend(build_project_memory_context(question, project_ref, limit=min(2, limit)))

    elif allow_records and intent.intent_type == "unknown":
        memories.extend(build_project_memory_context(question, project_ref, limit=min(2, limit)))

    if intent.intent_type == "legal_source_question":
        ordered = [*supplied_web, *knowledge, *rag]
    elif intent.intent_type in {"safety_definition_question", "sop_howto_question", "general_safety_question"}:
        ordered = [*knowledge, *rag, *supplied_web]
    elif intent.intent_type == "recent_image_question":
        ordered = [*recent, *followups, *knowledge, *rag, *supplied_web]
    elif intent.intent_type in {"followup_question", "project_memory_question"}:
        ordered = [*followups, *recent, *memories, *knowledge, *rag, *supplied_web]
    elif intent.intent_type in {"drawing_question", "cad_bim_handoff_question"}:
        ordered = [*drawing, *followups, *memories, *knowledge, *rag, *supplied_web]
    else:
        ordered = [*knowledge, *rag, *memories, *supplied_web]

    contexts = _dedupe_contexts(ordered)[:15]
    recent_referenced = any(
        str(getattr(item, "source_id", "")).startswith(("recent-", "project-memory:"))
        and getattr(item, "source_type", "") in {"recent_image_analysis", "project_memory"}
        for item in contexts
    ) and intent.intent_type in {"recent_image_question", "followup_question"}
    local_contexts = [item for item in contexts if item not in supplied_web]
    selected_web = [item for item in contexts if item in supplied_web]
    counts = {
        "memory": sum(1 for item in contexts if getattr(item, "source_type", "") in {"project_memory", "qa_memory", "memory"}),
        "followups": sum(1 for item in contexts if getattr(item, "source_type", "") == "follow_up"),
        "knowledge": sum(1 for item in contexts if getattr(item, "source_type", "") not in {"project_memory", "qa_memory", "memory", "follow_up", "recent_image_analysis", "uploaded_record", "rag_chunk", "general_web"} and item not in selected_web),
        "rag": sum(1 for item in contexts if getattr(item, "source_type", "") == "rag_chunk"),
        "official": sum(1 for item in contexts if getattr(item, "trust_level", "") == "official_hk"),
        "visual_evidence": visual_evidence_count if recent_referenced else 0,
        "recent_image": 1 if recent_referenced else 0,
        "drawing_found": 1 if (drawing_summary and drawing_summary.get("found")) else 0,
        "drawing_handoff": int(drawing_summary.get("handoff_count", 0)) if drawing_summary else 0,
        "drawing_pages": int(drawing_summary.get("page_count", 0)) if drawing_summary else 0,
    }
    return AskContextSelection(
        intent=intent,
        contexts=contexts,
        local_contexts=local_contexts,
        web_contexts=selected_web,
        context_basis=_context_basis(intent, counts, recent_referenced),
        retrieval_counts=counts,
        recent_image_referenced=recent_referenced,
    )


def _context_basis(intent: AskIntent, counts: dict[str, int], recent_referenced: bool) -> list[str]:
    if intent.intent_type in {"drawing_question", "cad_bim_handoff_question"}:
        return [
            "問題類型：圖紙 / CAD-BIM 查詢",
            "最近圖紙分析：" + ("已引用" if counts.get("drawing_found") else "未找到"),
            f"CAD/BIM 交接事項：{counts.get('drawing_handoff', 0)} 項",
            f"圖紙頁面：{counts.get('drawing_pages', 0)} 頁",
        ]
    lines = [f"問題類型：{intent.label}"]
    if intent.intent_type == "safety_definition_question":
        lines.append("最近相片分析：未引用，因問題不是相片跟進")
    else:
        lines.append("最近相片分析：" + ("已引用" if recent_referenced else "未引用"))
    if intent.intent_type == "recent_image_question":
        lines.extend((
            f"視覺證據：{counts['visual_evidence']} 項",
            f"未完成跟進：{counts['followups']} 項",
            f"知識來源：{counts['knowledge']} 項",
        ))
    else:
        lines.extend((
            f"知識來源：{counts['knowledge']} 項",
            f"RAG 片段：{counts['rag']} 項",
            "官方來源：" + ("有" if counts["official"] else "未核實"),
        ))
    return lines


def _latest_analysis_context(data: dict[str, Any] | None) -> tuple[KnowledgeSnippet | None, int]:
    if not isinstance(data, dict):
        return None, 0
    image = data.get("image_analysis") if isinstance(data.get("image_analysis"), dict) else data
    observations = list(image.get("visual_observations") or image.get("key_observations") or data.get("observations") or [])
    evidence = list(image.get("evidence_items") or [])
    summary_items = list(dict.fromkeys([*observations, *evidence]))[:6]
    if not summary_items and not data.get("agent_answer") and not data.get("analysis_result"):
        return None, 0
    snippet = "；".join(summary_items) or str(data.get("agent_answer") or data.get("analysis_result") or "")[:700]
    return KnowledgeSnippet(
        title="最近相片分析",
        path="AICOS Session / latest image analysis",
        snippet=snippet,
        score=10.0,
        source_type="recent_image_analysis",
        source_id="recent-image:session",
        trust_level="uploaded_record",
        provider="session_context",
    ), len(evidence or observations)


def _latest_upload_memory(project_ref: str | None):
    return next((
        item for item in read_all_memory()
        if item.source_type == "upload_analysis"
        and (not project_ref or (item.project_ref or "").lower() == project_ref.lower())
    ), None)


def _project_memory_snippet(item, score: float) -> KnowledgeSnippet:
    return KnowledgeSnippet(
        title=item.title,
        path=f"AICOS Project Memory / {item.memory_id}",
        snippet=item.summary,
        score=score,
        source_type="project_memory",
        source_id=f"project-memory:{item.memory_id}",
        trust_level="uploaded_record",
        provider="project_memory_store",
    )


def _followups_for_latest(memory_id: str, project_ref: str | None, limit: int) -> list[KnowledgeSnippet]:
    items = [
        item for item in list_followups(project_ref=project_ref, limit=None)
        if item.status in {"open", "in_progress", "waiting"}
        and (not memory_id or item.source_memory_id == memory_id)
    ][:limit]
    return [KnowledgeSnippet(
        title=item.title,
        path=f"AICOS Follow-up / {item.followup_id}",
        snippet=item.description,
        score=max(1.0, float(limit - rank)),
        source_type="follow_up",
        source_id=f"follow-up:{item.followup_id}",
        trust_level="uploaded_record",
        provider="followup_store",
    ) for rank, item in enumerate(items)]


def _trusted_first(results: list[SearchResult]) -> list[SearchResult]:
    order = {"official_hk": 0, "trusted_industry": 1, "general_web": 2, "unknown": 3}
    return sorted(results, key=lambda item: order.get(str(getattr(item, "trust_level", "unknown")), 4))


def _rank_topic_contexts(items: list[Any], question: str, preserve_trust: bool = False) -> list[Any]:
    hot_work, height = safety_query_profile(question)
    if not hot_work and not height:
        return items
    trust_order = {"official_hk": 4, "trusted_industry": 3, "local_internal": 2, "uploaded_record": 1}

    def score(item: Any) -> tuple[int, float]:
        text = " ".join((
            str(getattr(item, "title", "") or ""),
            str(getattr(item, "snippet", "") or ""),
            str(getattr(item, "url", "") or ""),
        )).lower()
        hot_hits = sum(term in text for term in HOT_WORK_QUERY_TERMS)
        height_hits = sum(term in text for term in WORK_AT_HEIGHT_QUERY_TERMS)
        relevance = hot_hits * 4 + height_hits if hot_work and not height else (
            height_hits * 4 + hot_hits if height and not hot_work else hot_hits + height_hits
        )
        if hot_work and not height and height_hits and not hot_hits:
            relevance -= 10
        if height and not hot_work and hot_hits and not height_hits:
            relevance -= 10
        trust = trust_order.get(str(getattr(item, "trust_level", "")), 0) if preserve_trust else 0
        return trust * 5 + relevance, float(getattr(item, "score", 0.0) or 0.0)

    return sorted(items, key=score, reverse=True)


def _dedupe_contexts(items: list[Any]) -> list[Any]:
    output = []
    seen = set()
    for item in items:
        identity = str(getattr(item, "source_id", "") or getattr(item, "url", "") or getattr(item, "title", ""))
        if not identity or identity in seen:
            continue
        seen.add(identity)
        output.append(item)
    return output
