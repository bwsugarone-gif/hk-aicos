"""Link drawing analysis into Project Memory and Follow-up (Phase 5.10G).

Saving a drawing analysis records a ``drawing_analysis`` project-memory entry,
and high-priority CAD/BIM handoff items spin off follow-up items so they surface
in the existing Records / Follow-up workflow. Reuses the existing stores; adds
no new persistence mechanism.
"""

from __future__ import annotations

from pathlib import Path
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


def register_drawing_source_file(
    document: DrawingDocument,
    *,
    source_path: Any = None,
    file_name: str | None = None,
    memory_id: str | None = None,
    persist: bool = True,
    registry_path: Any = None,
    drive_uploader: Any = None,
    drive_config: Any = None,
):
    """Register the uploaded drawing file's metadata in the file registry.

    Stores metadata only (no binary, no path exposed in the normal UI). When
    Google Drive is configured the original file is uploaded to the project's
    ``Drawings`` folder and the Drive id / link are stored; otherwise it falls
    back to ``local_runtime``. Never raises into the analysis flow.
    """
    from .file_registry import register_file_with_optional_drive
    from .file_storage import build_file_metadata
    from .file_storage_models import StoredFileRecord

    name = file_name or document.source_file_name or "未命名圖紙"
    ext = Path(str(name)).suffix.lower()
    file_type = "drawing_pdf" if ext == ".pdf" else "drawing_image"
    payload = build_file_metadata(
        original_file_name=name,
        source_module="drawing_analysis",
        project_ref=document.project_ref,
        local_runtime_path=source_path,
        file_type=file_type,
        tags=list(dict.fromkeys(["圖紙分析", *document.disciplines])),
        linked_memory_id=memory_id,
        linked_drawing_doc_id=document.document_id,
        metadata={
            "ingestion_status": document.ingestion_status,
            "page_count": document.page_count,
        },
    )
    if not persist:
        return StoredFileRecord.from_dict(payload)
    kwargs = {"path": registry_path} if registry_path is not None else {}
    try:
        return register_file_with_optional_drive(
            payload,
            local_path=source_path,
            uploader=drive_uploader,
            drive_config=drive_config,
            **kwargs,
        )
    except Exception:
        return None


def save_drawing_analysis(
    document: DrawingDocument,
    *,
    persist: bool = True,
    memory_path: Any = None,
    followup_path: Any = None,
    source_path: Any = None,
    file_name: str | None = None,
    registry_path: Any = None,
    drive_uploader: Any = None,
    drive_config: Any = None,
) -> dict[str, Any]:
    """Convenience: register memory + follow-ups for an analyzed document.

    The drawing-store persistence happens in ``analyze_drawing``; this adds the
    cross-feature links and, when given the uploaded path, registers the source
    file metadata in the file registry.
    """
    memory = register_drawing_memory(document, persist=persist, memory_path=memory_path)
    memory_id = getattr(memory, "memory_id", None)
    followups = create_followups_for_handoff(
        document,
        source_memory_id=memory_id,
        persist=persist,
        followup_path=followup_path,
    )
    file_record = register_drawing_source_file(
        document,
        source_path=source_path,
        file_name=file_name,
        memory_id=memory_id,
        persist=persist,
        registry_path=registry_path,
        drive_uploader=drive_uploader,
        drive_config=drive_config,
    )
    return {
        "memory": memory,
        "memory_id": memory_id,
        "followups": followups,
        "file_record": file_record,
        "file_id": getattr(file_record, "file_id", None),
    }
