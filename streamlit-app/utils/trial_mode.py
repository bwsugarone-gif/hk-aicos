"""Client trial mode helpers for AICOS (Phase 6.6).

Streamlit-free, deterministic helpers describing the guided trial workflow:
flow cards, a trial checklist (with best-effort completion status), trial
warnings, and the Phase 6.2 *future-hook* fields that records may carry now so
permissions/teams can be layered on later without a schema change.

Nothing here enforces permissions, logs in, or contacts an external service.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


DEMO_PROJECT_REF = "AICOS-DEMO"
ALT_DEMO_PROJECT_REF = "BW-DEMO"
TRIAL_PROJECT_REFS = (DEMO_PROJECT_REF, ALT_DEMO_PROJECT_REF)

# Phase 6.2 preparation: optional fields records may carry now so future
# permission / team / audit work can reuse them. Not enforced in this phase.
FUTURE_HOOK_FIELDS = (
    "project_ref",
    "team_id",
    "role_hint",
    "responsible_team",
    "created_by",
    "updated_by",
    "visibility",
    "trial_mode",
)

TRIAL_WARNINGS = (
    "目前為本機 / Cloud 暫存試用模式，未啟用登入或權限。",
    "正式多人使用前需接入 Supabase / Google Drive / 權限。",
    "資料可能因 Cloud redeploy 清空，請勿存放真實機密客戶資料。",
)


@dataclass
class TrialStep:
    key: str
    order: str
    title: str
    description: str
    page: str
    page_label: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TrialChecklistItem:
    key: str
    label: str
    done: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


TRIAL_FLOW_CARDS = (
    TrialStep("upload_photo", "A", "上載地盤相片",
              "於上載分析頁上載地盤相片，AICOS 會做風險與證據分析。",
              "pages/1_Upload.py", "📤 上載分析"),
    TrialStep("ask_safety", "B", "問 AICOS 安全問題",
              "向 AICOS 提出安全 / 法例問題，查看引用來源。",
              "pages/10_Ask_AICOS.py", "💬 問 AICOS"),
    TrialStep("upload_drawing", "C", "上載圖紙 / PDF",
              "上載圖紙或 PDF，產生問題清單及頁面分析。",
              "pages/12_Drawing_Analysis.py", "📐 圖紙分析"),
    TrialStep("generate_handoff", "D", "產生 CAD/BIM 交接",
              "由圖紙分析自動產生 CAD/BIM 交接事項。",
              "pages/12_Drawing_Analysis.py", "📐 圖紙分析"),
    TrialStep("ingest_knowledge", "E", "上載 Knowledge PDF",
              "於知識匯入頁上載 PDF / TXT / MD，建立知識來源及 RAG 片段。",
              "pages/13_Knowledge_Ingestion.py", "📚 知識匯入"),
    TrialStep("search_records", "F", "去 Records 搜尋",
              "於記錄頁的全部記錄搜尋查回圖紙 / 交接 / 知識 / 檔案。",
              "pages/11_Records.py", "🗂️ 記錄"),
    TrialStep("ask_followup", "G", "問 AICOS 查返資料",
              "再向 AICOS 提問，讓它引用已上載的文件 / 圖紙 / 交接。",
              "pages/10_Ask_AICOS.py", "💬 問 AICOS"),
)

TRIAL_CHECKLIST_ITEMS = (
    ("photo_analysis", "相片分析已完成"),
    ("drawing_analysis", "圖紙分析已完成"),
    ("cad_bim_handoff", "CAD/BIM 交接已建立"),
    ("knowledge_source", "知識來源已匯入"),
    ("records_searchable", "記錄可被搜尋"),
    ("ask_can_reference", "Ask AICOS 可引用已上載資料"),
)


def trial_flow_cards() -> list[TrialStep]:
    return list(TRIAL_FLOW_CARDS)


def trial_warnings() -> list[str]:
    return list(TRIAL_WARNINGS)


def is_trial_project(project_ref: str | None) -> bool:
    return str(project_ref or "").strip().upper() in {ref.upper() for ref in TRIAL_PROJECT_REFS}


def build_future_hooks(
    *,
    project_ref: str | None = None,
    team_id: str | None = None,
    role_hint: str | None = None,
    responsible_team: str | None = None,
    created_by: str | None = None,
    updated_by: str | None = None,
    visibility: str | None = None,
    trial_mode: bool = True,
) -> dict[str, Any]:
    """Return the Phase 6.2 future-hook fields for attaching to a record.

    Permission/team fields default to ``None`` (not enforced); ``trial_mode``
    marks data created during the trial workflow.
    """
    return {
        "project_ref": project_ref,
        "team_id": team_id,
        "role_hint": role_hint,
        "responsible_team": responsible_team,
        "created_by": created_by,
        "updated_by": updated_by,
        "visibility": visibility,
        "trial_mode": bool(trial_mode),
    }


def build_trial_checklist(project_ref: str | None = None) -> list[TrialChecklistItem]:
    """Return the trial checklist with best-effort completion status.

    Each item's ``done`` is computed from the existing local stores. Any read
    error degrades to ``done=False`` rather than raising.
    """
    status = _evaluate_completion(project_ref)
    return [TrialChecklistItem(key, label, bool(status.get(key))) for key, label in TRIAL_CHECKLIST_ITEMS]


def _evaluate_completion(project_ref: str | None) -> dict[str, bool]:
    result = {key: False for key, _ in TRIAL_CHECKLIST_ITEMS}

    def _match(ref: str | None) -> bool:
        return (not project_ref) or (str(ref or "").lower() == str(project_ref).lower())

    try:
        from .project_memory_store import read_all_memory

        memories = read_all_memory()
        result["photo_analysis"] = any(
            m.source_type in {"upload_analysis"} and _match(m.project_ref) for m in memories
        )
    except Exception:
        pass
    try:
        from .drawing_store import read_all_drawing_documents

        docs = [d for d in read_all_drawing_documents() if _match(d.project_ref)]
        result["drawing_analysis"] = bool(docs)
        result["cad_bim_handoff"] = any(d.handoff_items for d in docs)
    except Exception:
        pass
    try:
        from .knowledge_ingestion import read_ingested_knowledge_sources

        result["knowledge_source"] = bool(read_ingested_knowledge_sources())
    except Exception:
        pass
    try:
        from .records_search import build_unified_record_index

        index = build_unified_record_index()
        if project_ref:
            index = [r for r in index if _match(getattr(r, "project_ref", None))]
        result["records_searchable"] = bool(index)
    except Exception:
        pass
    result["ask_can_reference"] = bool(result["knowledge_source"] or result["drawing_analysis"])
    return result
