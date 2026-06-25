"""Demo project seed helper for the AICOS client trial (Phase 6.6).

Creates a small, deterministic, *safe* set of sample records (project memory,
a follow-up, a drawing document with one CAD/BIM handoff item, a file-registry
entry and an ingested knowledge source) so a client can try Records / Ask AICOS
without uploading real data.

Rules honoured:
* No external API, no network, no real confidential data.
* Never auto-seeds: the caller (a button) must invoke :func:`seed_demo_data`.
* Idempotent: re-seeding does not duplicate records (gated by fixed demo ids).
* Records carry Phase 6.2 future-hook fields and a ``trial_mode`` marker.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .trial_mode import DEMO_PROJECT_REF, build_future_hooks


DEMO_MEMORY_SAFETY_ID = "pmem_demo_safety"
DEMO_MEMORY_DRAWING_ID = "pmem_demo_drawing"
DEMO_DRAWING_DOC_ID = "draw_demo_001"
DEMO_FILE_ID = "file_demo_001"
DEMO_SAFETY_TEXT = (
    "地盤安全試用樣本：進行熱工序（電焊、切割、打磨）前必須申請熱工許可證，"
    "並安排防火監察及配置滅火筒。高空工作（離地兩米以上）須設置護欄、安全網或使用全身式安全帶。"
    "竹棚 / 金屬棚架須由合資格人員檢查並掛上有效檢查牌。"
)


@dataclass
class DemoSeedResult:
    project_ref: str = DEMO_PROJECT_REF
    already_seeded: bool = False
    created: dict[str, int] = field(default_factory=dict)
    memory_ids: list[str] = field(default_factory=list)
    drawing_doc_id: str | None = None
    file_id: str | None = None
    knowledge_source_id: str | None = None
    followup_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def is_demo_seeded(*, memory_path: Any = None) -> bool:
    """True when the fixed demo memory records already exist."""
    try:
        from .project_memory_store import read_all_memory

        kwargs = {"path": memory_path} if memory_path is not None else {}
        ids = {m.memory_id for m in read_all_memory(**kwargs)}
    except Exception:
        return False
    return DEMO_MEMORY_SAFETY_ID in ids or DEMO_MEMORY_DRAWING_ID in ids


def seed_demo_data(
    *,
    force: bool = False,
    memory_path: Any = None,
    followup_path: Any = None,
    drawing_path: Any = None,
    registry_path: Any = None,
    knowledge_path: Any = None,
    rag_path: Any = None,
) -> DemoSeedResult:
    """Create the demo records once. No-op (returns ``already_seeded``) if present."""
    if is_demo_seeded(memory_path=memory_path) and not force:
        return DemoSeedResult(
            already_seeded=True,
            memory_ids=[DEMO_MEMORY_SAFETY_ID, DEMO_MEMORY_DRAWING_ID],
            drawing_doc_id=DEMO_DRAWING_DOC_ID,
            file_id=DEMO_FILE_ID,
        )

    created: dict[str, int] = {}
    hooks = build_future_hooks(project_ref=DEMO_PROJECT_REF, responsible_team="cad", trial_mode=True)

    # 1) Project memory (safety + drawing summary), fixed ids -> latest-wins.
    from .project_memory_store import append_memory

    mem_kwargs = {"path": memory_path} if memory_path is not None else {}
    append_memory({
        "memory_id": DEMO_MEMORY_SAFETY_ID,
        "source_type": "upload_analysis",
        "project_ref": DEMO_PROJECT_REF,
        "title": "Demo：地盤安全巡查樣本",
        "summary": "示範地盤相片分析：發現熱工序及高空工作風險，需確認許可證、防火監察及防墮措施。",
        "risk_level": "high",
        "tags": ["示範", "安全", "熱工", "高空"],
        "status": "open",
        "priority": "high",
        "source_route": "/Demo",
        "metadata": {**hooks, "demo": True},
    }, **mem_kwargs)
    append_memory({
        "memory_id": DEMO_MEMORY_DRAWING_ID,
        "source_type": "drawing_analysis",
        "project_ref": DEMO_PROJECT_REF,
        "title": "Demo：圖紙分析摘要樣本",
        "summary": "示範圖紙分析：地下層平面圖，需核對尺寸並補充防火分區標註。",
        "tags": ["示範", "圖紙"],
        "status": "open",
        "priority": "medium",
        "source_route": "/Demo",
        "metadata": {**hooks, "demo": True, "document_id": DEMO_DRAWING_DOC_ID},
    }, **mem_kwargs)
    created["memory"] = 2

    # 2) Follow-up linked to the safety memory.
    from .followup_store import create_followup_from_analysis

    fu_kwargs = {"path": followup_path} if followup_path is not None else {}
    followup = create_followup_from_analysis(
        title="Demo：跟進熱工許可及防火監察",
        description="示範跟進事項：確認熱工許可證已簽發並安排防火監察人員。",
        project_ref=DEMO_PROJECT_REF,
        source_memory_id=DEMO_MEMORY_SAFETY_ID,
        priority="high",
        responsible_role="安全主任",
        suggested_actions=["核實熱工許可證", "安排防火監察", "檢查滅火筒"],
        **fu_kwargs,
    )
    created["followup"] = 1

    # 3) Drawing document with one CAD/BIM handoff item, fixed id -> latest-wins.
    from .drawing_models import DrawingDocument
    from .drawing_store import append_drawing_document

    dr_kwargs = {"path": drawing_path} if drawing_path is not None else {}
    document = DrawingDocument.from_dict({
        "document_id": DEMO_DRAWING_DOC_ID,
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
        "project_ref": DEMO_PROJECT_REF,
        "source_file_name": "DEMO-A-101.pdf",
        "summary": "示範地下層建築平面圖一套。",
        "disciplines": ["architecture"],
        "page_types": ["floor_plan"],
        "page_count": 1,
        "analyzed_page_count": 1,
        "ingestion_status": "selectable_text",
        "drawing_issues": ["部分尺寸未標示，需核對。"],
        "handoff_items": [{
            "item_id": "handoff_demo_001",
            "action_type": "verify_dimension",
            "target_team": "cad",
            "title": "核對地下層主要尺寸",
            "description": "示範交接：核對圖示主要尺寸並補回缺漏標註。",
            "priority": "high",
            "status": "open",
            "discipline": "architecture",
            "sheet_number": "A-101",
            "required_output": "已標註齊全的平面圖。",
        }],
        "metadata": {**hooks, "demo": True},
    })
    append_drawing_document(document, **dr_kwargs)
    created["drawing_document"] = 1
    created["handoff"] = 1

    # 4) File-registry entry for the demo drawing (metadata only, no path shown).
    from .file_registry import register_file

    reg_kwargs = {"path": registry_path} if registry_path is not None else {}
    register_file({
        "file_id": DEMO_FILE_ID,
        "original_file_name": "DEMO-A-101.pdf",
        "file_type": "drawing_pdf",
        "source_module": "drawing_analysis",
        "project_ref": DEMO_PROJECT_REF,
        "storage_provider": "local_runtime",
        "tags": ["示範", "圖紙分析"],
        "linked_drawing_doc_id": DEMO_DRAWING_DOC_ID,
        "linked_memory_id": DEMO_MEMORY_DRAWING_ID,
        "metadata": {**hooks, "demo": True},
    }, **reg_kwargs)
    created["file"] = 1

    # 5) Knowledge source + RAG chunks from safe sample text.
    knowledge_source_id = None
    try:
        from .knowledge_ingestion import ingest_text

        ing_kwargs: dict[str, Any] = {}
        if knowledge_path is not None:
            ing_kwargs["knowledge_path"] = knowledge_path
        if rag_path is not None:
            ing_kwargs["rag_path"] = rag_path
        result = ingest_text(
            text=DEMO_SAFETY_TEXT,
            title="Demo：地盤安全作業樣本指引",
            original_file_name="DEMO-safety-guide.txt",
            project_ref=DEMO_PROJECT_REF,
            tags=["示範", "安全"],
            description="示範知識來源：熱工許可、高空工作及棚架檢查要點。",
            **ing_kwargs,
        )
        knowledge_source_id = result.source_id
        created["knowledge_source"] = 1
        created["rag_chunks"] = result.chunk_count
    except Exception:
        pass

    return DemoSeedResult(
        project_ref=DEMO_PROJECT_REF,
        already_seeded=False,
        created=created,
        memory_ids=[DEMO_MEMORY_SAFETY_ID, DEMO_MEMORY_DRAWING_ID],
        drawing_doc_id=DEMO_DRAWING_DOC_ID,
        file_id=DEMO_FILE_ID,
        knowledge_source_id=knowledge_source_id,
        followup_id=getattr(followup, "followup_id", None),
    )
