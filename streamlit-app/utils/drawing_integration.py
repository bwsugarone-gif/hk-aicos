"""Link drawing analysis into Project Memory and Follow-up (Phase 5.10G).

Saving a drawing analysis records a ``drawing_analysis`` project-memory entry,
and high-priority CAD/BIM handoff items spin off follow-up items so they surface
in the existing Records / Follow-up workflow. Reuses the existing stores; adds
no new persistence mechanism.
"""

from __future__ import annotations

from typing import Any

from .drawing_models import ACTION_TYPE_LABELS_ZH, DrawingDocument
from .followup_store import create_followup_from_analysis
from .project_memory_store import append_memory

_HIGH_PRIORITIES = {"high", "urgent"}
_TEAM_ROLE = {
    "cad": "CAD／繪圖團隊",
    "bim": "BIM 團隊",
    "both": "CAD／BIM 團隊",
}
_MAX_FOLLOWUPS = 6


def register_drawing_memory(
    document: DrawingDocument,
    *,
    persist: bool = True,
    memory_path: Any = None,
):
    """Create a ``drawing_analysis`` project-memory record for the document."""
    has_high = any(item.priority in _HIGH_PRIORITIES for item in document.handoff_items)
    tags = list(dict.fromkeys([
        "圖紙分析",
        *document.disciplines,
        *[ptype for ptype in document.page_types if ptype != "unknown"],
    ]))
    summary_lines = [document.summary]
    if document.drawing_issues:
        summary_lines.append("主要問題：" + "；".join(document.drawing_issues[:5]))
    if document.missing_information:
        summary_lines.append("待補資料：" + "；".join(document.missing_information[:5]))

    payload = {
        "source_type": "drawing_analysis",
        "project_ref": document.project_ref,
        "title": f"圖紙分析：{document.source_file_name or '未命名圖紙'}",
        "summary": "\n".join(line for line in summary_lines if line),
        "analysis_type": "drawing_analysis",
        "evidence_sources": ["圖紙分析"],
        "tags": tags,
        "status": "open",
        "priority": "high" if has_high else "medium",
        "source_route": "/Drawing_Analysis",
        "source_file_name": document.source_file_name,
        "metadata": {
            "document_id": document.document_id,
            "page_count": document.page_count,
            "handoff_count": len(document.handoff_items),
            "ingestion_status": document.ingestion_status,
        },
    }
    kwargs = {"path": memory_path} if memory_path is not None else {}
    if not persist:
        from .memory_models import ProjectMemoryRecord

        return ProjectMemoryRecord.from_dict(payload)
    return append_memory(payload, **kwargs)


def create_followups_for_handoff(
    document: DrawingDocument,
    *,
    source_memory_id: str | None = None,
    persist: bool = True,
    followup_path: Any = None,
) -> list[Any]:
    """Create follow-up items for high-priority handoff items (capped)."""
    high_items = [item for item in document.handoff_items if item.priority in _HIGH_PRIORITIES]
    created: list[Any] = []
    for item in high_items[:_MAX_FOLLOWUPS]:
        action_label = ACTION_TYPE_LABELS_ZH.get(item.action_type, item.action_type)
        page_hint = f"（第 {item.page_number} 頁）" if item.page_number else ""
        kwargs = {
            "title": f"[{action_label}] {item.title}{page_hint}",
            "description": item.description,
            "project_ref": document.project_ref,
            "source_memory_id": source_memory_id,
            "priority": item.priority,
            "responsible_role": _TEAM_ROLE.get(item.target_team, "CAD／BIM 團隊"),
            "suggested_actions": [item.description] if item.description else [],
        }
        if followup_path is not None:
            kwargs["path"] = followup_path
        if persist:
            created.append(create_followup_from_analysis(**kwargs))
        else:
            created.append(kwargs)
    return created


def save_drawing_analysis(
    document: DrawingDocument,
    *,
    persist: bool = True,
    memory_path: Any = None,
    followup_path: Any = None,
) -> dict[str, Any]:
    """Convenience: register memory + follow-ups for an analyzed document.

    The drawing-store persistence happens in ``analyze_drawing``; this only adds
    the cross-feature links.
    """
    memory = register_drawing_memory(document, persist=persist, memory_path=memory_path)
    memory_id = getattr(memory, "memory_id", None)
    followups = create_followups_for_handoff(
        document,
        source_memory_id=memory_id,
        persist=persist,
        followup_path=followup_path,
    )
    return {"memory": memory, "memory_id": memory_id, "followups": followups}
