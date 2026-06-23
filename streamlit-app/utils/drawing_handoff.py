"""Drawing issue extraction and CAD/BIM handoff generation (Phase 5.10E).

Produces practical, field-oriented findings and actionable handoff items for the
CAD / BIM team. The wording is deliberately framed as "to verify / to confirm"
rather than asserting that the design has been fully checked for compliance.
"""

from __future__ import annotations

from typing import Any

from .drawing_models import CadBimHandoffItem
from .drawing_store import new_handoff_id


# Page types that should carry dimensions / levels and therefore warrant
# verification actions when handed to CAD/BIM.
_DIMENSIONAL_PAGES = {"floor_plan", "section", "detail", "elevation", "reflected_ceiling_plan"}


def extract_page_findings(page: dict[str, Any]) -> dict[str, list[str]]:
    """Derive issues / missing info / coordination flags for one analyzed page.

    ``page`` is a dict carrying at least ``page_type``, ``discipline``,
    ``title_block_fields`` and ``text`` keys.
    """
    page_type = str(page.get("page_type") or "unknown")
    discipline = str(page.get("discipline") or "unknown")
    fields = page.get("title_block_fields") or {}
    text = str(page.get("text") or "")
    low = text.lower()

    issues: list[str] = []
    missing: list[str] = []
    coordination: list[str] = []

    # Title-block completeness (practical drafting hygiene).
    if not fields.get("drawing_number"):
        missing.append("缺圖紙編號／圖則編號，待 CAD team 補回標題欄。")
    if not fields.get("scale") and page_type in _DIMENSIONAL_PAGES:
        missing.append("此圖未標示比例，需確認比例尺。")
    if not fields.get("revision"):
        missing.append("缺修訂版本（Rev），待確認是否最新版。")

    if page_type == "unknown":
        issues.append("未能判斷圖紙類型，建議人工確認頁面內容。")
    if discipline == "unknown":
        issues.append("未能判斷專業範疇，建議由相關工程師確認。")

    # Light keyword heuristics for common drawing red flags.
    if any(token in low for token in ("tbc", "t.b.c", "to be confirmed", "待定", "待確認")):
        issues.append("圖內標示 TBC／待確認項目，需於出圖前落實。")
    if any(token in low for token in ("hold", "not for construction", "preliminary", "草圖", "不作施工")):
        issues.append("圖紙可能為初步／非施工版本，施工前需確認狀態。")

    # Discipline-driven coordination prompts.
    if discipline == "mep":
        coordination.append("機電圖需與建築及結構圖核對開孔、樓底高度及管線走向。")
    if discipline == "fire_services":
        coordination.append("消防圖需與機電及建築圖核對走火通道、灑水及探測器佈置。")
    if discipline == "drainage":
        coordination.append("排水圖需核對渠管走向、坡度及與結構梁柱是否衝突。")

    return {
        "drawing_issues": issues,
        "missing_information": missing,
        "coordination_flags": coordination,
    }


def _item(action_type: str, team: str, title: str, description: str, *, priority: str,
          page_number: int | None = None, sheet_number: str | None = None,
          discipline: str | None = None, references: list[str] | None = None) -> CadBimHandoffItem:
    return CadBimHandoffItem(
        item_id=new_handoff_id(),
        action_type=action_type,
        target_team=team,
        title=title,
        description=description,
        priority=priority,
        page_number=page_number,
        sheet_number=sheet_number,
        discipline=discipline,
        references=list(references or []),
    )


def generate_handoff_items(page: dict[str, Any], findings: dict[str, list[str]]) -> list[CadBimHandoffItem]:
    """Generate CAD/BIM handoff items for one page from its findings."""
    items: list[CadBimHandoffItem] = []
    page_number = page.get("page_number")
    fields = page.get("title_block_fields") or {}
    sheet_number = fields.get("sheet_number") or fields.get("drawing_number")
    page_type = str(page.get("page_type") or "unknown")
    discipline = str(page.get("discipline") or "unknown")

    # Missing title-block info -> annotation / RFI for CAD team.
    if findings.get("missing_information"):
        items.append(_item(
            "add_annotation", "cad",
            "補回標題欄資料",
            "；".join(findings["missing_information"]),
            priority="medium", page_number=page_number, sheet_number=sheet_number,
            discipline=discipline if discipline != "unknown" else None,
        ))

    # Dimensional pages -> verify dimensions / openings / levels.
    if page_type in _DIMENSIONAL_PAGES:
        items.append(_item(
            "verify_dimension", "bim",
            "核對尺寸與標高",
            "請 BIM team 對照模型核實此頁的主要尺寸、標高及開口位是否一致。",
            priority="medium", page_number=page_number, sheet_number=sheet_number,
            discipline=discipline if discipline != "unknown" else None,
        ))
        if page_type in {"floor_plan", "elevation", "section"}:
            items.append(_item(
                "verify_opening", "bim",
                "核對門窗及開口位",
                "核對門窗、預留孔及開口位的位置與尺寸，並與其他專業圖協調。",
                priority="medium", page_number=page_number, sheet_number=sheet_number,
            ))

    # Coordination flags -> MEP coordination action.
    if findings.get("coordination_flags"):
        items.append(_item(
            "verify_mep_coordination", "both",
            "跨專業協調核對",
            "；".join(findings["coordination_flags"]),
            priority="high", page_number=page_number, sheet_number=sheet_number,
            discipline=discipline if discipline != "unknown" else None,
        ))

    # Discipline-specific checks.
    if discipline == "fire_services":
        items.append(_item(
            "check_fire_protection", "cad",
            "檢查消防保護佈置",
            "核對灑水頭、消防栓、走火指示及防火分區標示是否齊全並符合相關要求。",
            priority="high", page_number=page_number, sheet_number=sheet_number,
            discipline="fire_services",
        ))
    if page_type == "schedule":
        items.append(_item(
            "update_schedule", "cad",
            "核對及更新明細表",
            "核對門窗／物料／裝飾明細表與平面圖是否一致，如有差異需更新。",
            priority="medium", page_number=page_number, sheet_number=sheet_number,
        ))

    # Unresolved issues -> RFI / site verify.
    if findings.get("drawing_issues"):
        items.append(_item(
            "issue_rfi", "cad",
            "就待確認項目發出 RFI",
            "；".join(findings["drawing_issues"]),
            priority="medium", page_number=page_number, sheet_number=sheet_number,
        ))
    if page_type in {"floor_plan", "detail", "section"}:
        items.append(_item(
            "site_verify", "both",
            "現場核實",
            "建議到現場核實此頁的實際尺寸／位置，確保圖則與現場相符。",
            priority="low", page_number=page_number, sheet_number=sheet_number,
        ))

    return items
