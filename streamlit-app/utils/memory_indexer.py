"""Bridges Phase 5.8 project memory into the existing Ask AICOS context."""

from __future__ import annotations

from typing import Any

from .analysis_models import KnowledgeSnippet
from .memory_models import ProjectMemoryRecord
from .project_memory_store import DEFAULT_MEMORY_PATH, append_memory, search_memory


def build_project_memory_context(
    query: str,
    project_ref: str | None = None,
    limit: int = 5,
    *,
    path=DEFAULT_MEMORY_PATH,
) -> list[KnowledgeSnippet]:
    records = search_memory(query, project_ref=project_ref, limit=limit, path=path)
    return [
        KnowledgeSnippet(
            title=record.title,
            path=f"AICOS Project Memory / {record.memory_id}",
            snippet=record.summary,
            score=max(1.0, float(limit - rank)),
            source_type="project_memory",
            source_id=f"project-memory:{record.memory_id}",
            trust_level="uploaded_record",
            provider="project_memory_store",
        )
        for rank, record in enumerate(records)
    ]


def remember_analysis(data: dict[str, Any], *, path=DEFAULT_MEMORY_PATH) -> ProjectMemoryRecord:
    image = data.get("image_analysis") if isinstance(data.get("image_analysis"), dict) else {}
    evidence = image.get("evidence_items") or []
    return append_memory(
        {
            "source_type": "upload_analysis",
            "project_ref": data.get("project_ref") or None,
            "title": f"上載分析：{data.get('file_name') or '未命名檔案'}",
            "summary": str(data.get("analysis_result") or "")[:2500],
            "analysis_type": data.get("analysis_display_name") or data.get("analysis_type"),
            "risk_level": data.get("risk_level"),
            "confidence": image.get("visual_confidence"),
            "evidence_sources": evidence,
            "tags": _analysis_tags(data),
            "status": "open" if str(data.get("risk_level") or "").lower() not in {"low", "低風險"} else "resolved",
            "priority": "high" if str(data.get("risk_level") or "").lower() in {"high", "critical", "高風險", "極高風險"} else "medium",
            "source_file_name": data.get("file_name"),
            "source_route": "/Upload",
            "metadata": {"session_id": data.get("session_id"), "image_category": image.get("image_category")},
        },
        path=path,
    )


def _analysis_tags(data: dict[str, Any]) -> list[str]:
    image = data.get("image_analysis") if isinstance(data.get("image_analysis"), dict) else {}
    text = " ".join([str(data.get("question") or ""), str(data.get("analysis_result") or ""), str(image.get("image_category") or "")]).lower()
    mapping = {
        "熱工": ("熱工", "火花", "hot_work"),
        "切割／打磨": ("磨機", "切割", "cutting_grinding"),
        "高處／防墮": ("高空", "高處", "臨邊", "防墮"),
        "PPE": ("ppe", "安全帽", "護目", "手套"),
    }
    return [label for label, terms in mapping.items() if any(term in text for term in terms)]
