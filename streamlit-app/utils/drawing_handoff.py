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


# Text markers that justify an explicit dimension check (vs. a site-verify).
_DIM_MARKERS = ("dimension", " mm", "rl ", "ffl", "setting out", "level", "尺寸", "標高", "水平", "定位")
# Markers that suggest a cross-discipline opening / penetration interface.
_OPENING_MARKERS = ("opening", "penetration", "sleeve", "bwic", "blockout", "void", "穿牆", "預留洞", "開孔", "套管", "洞口")

# Who should ultimately verify each discipline's work.
_VERIFY_BY: dict[str, str] = {
    "structural": "結構工程師",
    "mep": "機電工程師",
    "fire_services": "消防工程師 / 註冊消防",
    "drainage": "排水 / 渠務工程師",
    "facade": "幕牆工程師 / 建築師",
    "landscape": "園境師",
    "interior": "室內設計 / 建築師",
    "builder_works": "結構 / 建築工程師",
    "architecture": "建築師 / 項目主管",
}


def _verifier(discipline: str | None) -> str:
    return _VERIFY_BY.get(discipline or "", "項目主管 / 合資格人員")


def _item(action_type: str, team: str, title: str, description: str, *, priority: str,
          required_output: str = "", evidence: str = "", verify_by: str = "",
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
        required_output=required_output,
        evidence=evidence,
        verify_by=verify_by,
    )


def generate_handoff_items(page: dict[str, Any], findings: dict[str, list[str]]) -> list[CadBimHandoffItem]:
    """Generate practical, task-oriented CAD/BIM handoff items for one page.

    Each item reads like a real work order: a clear task title, what the team
    must do, the ``required_output``, the ``evidence`` (why) and who should
    ``verify``. Wording stays "to verify / to confirm" -- it never claims the
    design has already been checked.
    """
    items: list[CadBimHandoffItem] = []
    page_number = page.get("page_number")
    fields = page.get("title_block_fields") or {}
    sheet_number = fields.get("sheet_number") or fields.get("drawing_number")
    page_type = str(page.get("page_type") or "unknown")
    discipline = str(page.get("discipline") or "unknown")
    disc = discipline if discipline != "unknown" else None
    text_low = str(page.get("text") or "").lower()
    has_dim = any(token in text_low for token in _DIM_MARKERS)
    has_opening = any(token in text_low for token in _OPENING_MARKERS)
    verifier = _verifier(disc)

    # Missing drawing number -> CAD must restore the title block.
    if not fields.get("drawing_number"):
        items.append(_item(
            "add_annotation", "cad", "補回圖號 / 標題欄資料",
            "本頁未能抽取圖紙編號。請 CAD team 核對原圖 title block 並補回圖號，方便圖紙管理及追蹤。",
            priority="medium", required_output="已補回圖號的圖紙及更新後的圖紙清單",
            evidence="未能抽取圖紙編號 / 圖則編號", verify_by="出圖負責人 / 項目主管",
            page_number=page_number, sheet_number=sheet_number, discipline=disc,
        ))

    # Missing / unclear revision -> revise the existing sheet & sheet list.
    if not fields.get("revision"):
        items.append(_item(
            "revise_existing_sheet", "cad", "核對圖號及修訂版本",
            "本頁未能清楚抽取 revision。請 CAD team 核對原圖 title block，確認是否為最新修訂，並於圖紙清單更新。",
            priority="medium", required_output="已確認並標明修訂版本的圖紙及圖紙清單",
            evidence="未能可靠抽取修訂版本（Rev）", verify_by="出圖負責人 / 項目主管",
            page_number=page_number, sheet_number=sheet_number, discipline=disc,
        ))

    # Missing scale on a dimensional page -> annotate before issue.
    if not fields.get("scale") and page_type in _DIMENSIONAL_PAGES:
        items.append(_item(
            "add_annotation", "cad", "補充 / 核對比例",
            "本頁未能可靠抽取 scale。請 CAD team 在出圖前核對比例及列印尺寸，避免現場按錯比例施工。",
            priority="medium", required_output="已標示正確比例並核對列印尺寸的圖紙",
            evidence="未能可靠抽取比例（Scale）", verify_by="出圖負責人",
            page_number=page_number, sheet_number=sheet_number, discipline=disc,
        ))

    # Cross-discipline coordination (openings / services interface) -> BIM.
    if findings.get("coordination_flags") or has_opening:
        evidence = "；".join(findings.get("coordination_flags") or []) or "圖紙可能涉及洞口 / 機電穿牆 / 專業介面"
        items.append(_item(
            "verify_mep_coordination", "both", "BIM 協調：洞口 / 機電穿牆位置",
            "圖紙顯示可能涉及 opening / penetration / services interface。請 BIM team 核對建築、結構及機電模型是否一致。",
            priority="high", required_output="已協調且無衝突的 BIM 模型或協調報告",
            evidence=evidence, verify_by="BIM 協調員 / 機電工程師",
            page_number=page_number, sheet_number=sheet_number, discipline=disc,
        ))

    # Dimensional pages: verify dimensions only when dimension notes are present,
    # otherwise hand off a site-verify -- do not claim dimensions were checked.
    if page_type in _DIMENSIONAL_PAGES:
        if has_dim:
            items.append(_item(
                "verify_dimension", "bim", "核對尺寸與標高",
                "本頁載有尺寸 / 標高標註。請 BIM team 對照模型核實主要尺寸、標高及開口位是否一致。",
                priority="medium", required_output="已與模型核對一致的尺寸 / 標高記錄",
                evidence="圖內載有尺寸 / 標高標註，需與模型核對", verify_by=verifier,
                page_number=page_number, sheet_number=sheet_number, discipline=disc,
            ))
        else:
            items.append(_item(
                "site_verify", "both", "Site Verify：現場尺寸覆核",
                "圖紙資訊不足以確認實際尺寸。請現場量度後回填 CAD / BIM。",
                priority="medium", required_output="現場實測尺寸記錄並回填圖紙 / 模型",
                evidence="圖內未見明確尺寸標註，未能單憑圖紙確認尺寸", verify_by="現場工程師 / 工地管理",
                page_number=page_number, sheet_number=sheet_number, discipline=disc,
            ))

    # Fire-services pages: dedicated protection check.
    if discipline == "fire_services":
        items.append(_item(
            "check_fire_protection", "cad", "檢查消防保護佈置",
            "核對灑水頭、消防栓、走火指示及防火分區標示是否齊全並符合相關要求。",
            priority="high", required_output="完整且符合要求的消防佈置圖",
            evidence="消防圖須核對保護裝置佈置是否齊全", verify_by="消防工程師 / 註冊消防",
            page_number=page_number, sheet_number=sheet_number, discipline="fire_services",
        ))

    # Schedule pages: reconcile schedule against plans.
    if page_type == "schedule":
        items.append(_item(
            "update_schedule", "cad", "核對及更新明細表",
            "核對門窗／物料／裝飾明細表與平面圖是否一致，如有差異需更新。",
            priority="medium", required_output="與平面圖一致的明細表",
            evidence="明細表須與平面圖核對一致", verify_by="建築師 / 項目主管",
            page_number=page_number, sheet_number=sheet_number, discipline=disc,
        ))

    # Unresolved / TBC issues -> raise an RFI before issuing for construction.
    if findings.get("drawing_issues"):
        items.append(_item(
            "issue_rfi", "cad", "就待確認項目發出 RFI",
            "本頁有待確認 / TBC 項目，建議向設計團隊發出 RFI 釐清後才出圖。",
            priority="medium", required_output="已回覆並落實的 RFI 記錄",
            evidence="；".join(findings["drawing_issues"][:4]), verify_by="設計團隊 / 項目主管",
            page_number=page_number, sheet_number=sheet_number, discipline=disc,
        ))

    return items
