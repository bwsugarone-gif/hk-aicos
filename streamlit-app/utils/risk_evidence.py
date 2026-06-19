"""Deterministic, provider-neutral risk evidence traces for AICOS UX."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .evidence_models import AnalysisBasis, RiskEvidenceTrace


_CUTTING_TERMS = ("磨機", "角磨機", "砂輪", "切割", "grinder", "grinding", "cutting")
_SPARK_TERMS = ("火花", "熱工", "燒焊", "焊接", "明火", "sparks", "hot work", "welding")
_HEIGHT_TERMS = ("高空", "高處", "臨邊", "洞口", "棚架", "吊船", "工作平台", "防墮", "墮下", "working at height")


def build_analysis_basis(
    *,
    ocr_text: str = "",
    has_visual_analysis: bool = False,
    visual_observations: Iterable[Any] | None = None,
    manual_description: str = "",
    sources: Iterable[Any] | None = None,
    rules_matched: Iterable[Any] | None = None,
) -> AnalysisBasis:
    """Classify OCR, vision, manual, knowledge, memory, and rule roles."""
    source_items = [_as_dict(item) for item in sources or []]
    source_types = {str(item.get("source_type") or "").lower() for item in source_items}
    trust_levels = {str(item.get("trust_level") or "").lower() for item in source_items}
    has_visual_content = bool(has_visual_analysis or _clean_items(visual_observations))
    rules = _clean_items(rules_matched)
    limitations = []
    if not has_visual_content:
        limitations.append("未有 AI 視覺確認")
    if "official_hk" not in trust_levels:
        limitations.append("未有官方來源章節")
    return AnalysisBasis(
        text_extraction_basis=["文字偵測／文件文字"] if str(ocr_text or "").strip() else [],
        vision_basis=["AI 視覺確認"] if has_visual_content else ["未有 AI 視覺確認"],
        manual_description_basis=["使用者補充描述"] if str(manual_description or "").strip() else [],
        knowledge_basis=(
            ["公司 SOP／知識庫"]
            if (
                source_types.intersection({"local_internal", "knowledge", "local_knowledge"})
                or "local_internal" in trust_levels
            )
            else []
        ) + (["官方來源"] if "official_hk" in trust_levels else ["未有官方來源章節"]),
        memory_basis=["地盤記憶／已上載記錄"] if source_types.intersection(
            {"uploaded_record", "memory", "site_record", "qa_memory"}
        ) else [],
        rule_basis=["AICOS 風險規則：" + "、".join(rules)] if rules else [],
        limitations=limitations,
    )


def summarize_analysis_basis(basis: AnalysisBasis) -> list[str]:
    """Return concise, de-duplicated user-facing analysis basis labels."""
    values = [
        *basis.manual_description_basis,
        *basis.text_extraction_basis,
        *basis.vision_basis,
        *basis.memory_basis,
        *basis.knowledge_basis,
        *basis.rule_basis,
        *basis.limitations,
    ]
    return list(dict.fromkeys(item for item in values if item))[:8]


def build_risk_evidence_trace(
    risk_level: str,
    *,
    question: str = "",
    raw_answer: str = "",
    manual_description: str = "",
    ocr_text: str = "",
    visual_observations: Iterable[Any] | None = None,
    evidence_items: Iterable[Any] | None = None,
    sources: Iterable[Any] | None = None,
    has_visual_analysis: bool = False,
) -> RiskEvidenceTrace:
    """Explain a risk label using observable evidence and matched safety rules."""
    visual_items = _clean_items(visual_observations)
    evidence = _clean_items(evidence_items)
    manual = " ".join(str(manual_description or "").split())
    source_items = [_as_dict(item) for item in sources or []]
    observable = " ".join([question, raw_answer, manual, ocr_text, *visual_items, *evidence]).lower()
    manual_lower = manual.lower()

    cutting = _matched_terms(observable, _CUTTING_TERMS)
    sparks = _matched_terms(observable, _SPARK_TERMS)
    height = _matched_terms(observable, _HEIGHT_TERMS)
    rules = []
    if cutting:
        rules.append("切割／打磨")
    if sparks:
        rules.append("熱工／火花")
    if cutting and sparks:
        rules.append("火警風險")
    if height:
        rules.append("墮下／臨邊風險")

    triggered_by = []
    manual_hits = _matched_terms(manual_lower, (*_CUTTING_TERMS, *_SPARK_TERMS, *_HEIGHT_TERMS))
    if manual_hits:
        triggered_by.append("使用者補充：" + "、".join(manual_hits[:5]))
    elif manual:
        triggered_by.append("使用者補充了現場工序描述")
    if visual_items or (has_visual_analysis and evidence):
        triggered_by.append("相片所見：" + (visual_items or evidence)[0])
    if str(ocr_text or "").strip():
        triggered_by.append("文字偵測找到相關文字")
    if question and not triggered_by:
        question_hits = _matched_terms(question.lower(), (*_CUTTING_TERMS, *_SPARK_TERMS, *_HEIGHT_TERMS))
        if question_hits:
            triggered_by.append("使用者提問：" + "、".join(question_hits[:5]))

    evidence_sources = []
    if manual:
        evidence_sources.append("使用者補充描述")
    if visual_items or has_visual_analysis:
        evidence_sources.extend(["相片內容", "AI 視覺"])
    if str(ocr_text or "").strip():
        evidence_sources.append("OCR／文字偵測")
    source_types = {str(item.get("source_type") or "").lower() for item in source_items}
    trust_levels = {str(item.get("trust_level") or "").lower() for item in source_items}
    if source_types.intersection({"uploaded_record", "memory", "site_record", "qa_memory"}):
        evidence_sources.append("地盤記憶")
    if source_types.intersection({"local_internal", "knowledge", "local_knowledge"}):
        evidence_sources.append("公司 SOP／知識庫")
    if "official_hk" in trust_levels:
        evidence_sources.append("官方來源")
    if rules:
        evidence_sources.append("AICOS 風險規則")

    missing = []
    if cutting or sparks:
        missing.extend(["滅火筒", "防火氈", "熱工許可", "防火監察", "PPE"])
    if height:
        missing.extend(["穩固工作平台", "護欄", "踢腳板", "安全進出通道", "防墮安排"])

    has_evidence = bool(triggered_by or evidence_sources or rules)
    normalized_risk = str(risk_level or "unknown")
    if not has_evidence:
        return RiskEvidenceTrace(
            risk_level=normalized_risk,
            triggered_by=["目前未有足夠相片、描述或文件證據"],
            evidence_sources=[],
            rules_matched=["暫不判斷具體危害"],
            missing_confirmations=["工序、位置、工具、附近物料及現場防護"],
            confidence_reason="沒有足夠可觀察資料支持具體風險分類。",
            final_reason="暫不判斷具體危害；請補充現場資料後由負責人覆核。",
        )

    high = normalized_risk.lower() in {"high", "critical", "高風險", "極高風險"}
    if high and (cutting or sparks):
        final_reason = "因尚未確認防火措施，暫列為高風險，需要人工覆核。"
    elif high and height:
        final_reason = "因涉及墮下風險且防墮措施尚待確認，暫列為高風險。"
    else:
        final_reason = f"風險級別為 {normalized_risk}；請按上述證據及未確認事項現場覆核。"
    return RiskEvidenceTrace(
        risk_level=normalized_risk,
        triggered_by=list(dict.fromkeys(triggered_by))[:4],
        evidence_sources=list(dict.fromkeys(evidence_sources))[:7],
        rules_matched=rules[:5],
        missing_confirmations=list(dict.fromkeys(missing))[:7],
        confidence_reason=(
            "有明確的相片或使用者描述，但現場控制措施仍待確認。"
            if manual or visual_items else
            "判斷來自問題內的可觀察風險詞及已登記資料。"
        ),
        final_reason=final_reason,
    )


def build_trace_from_analysis(data: dict[str, Any]) -> tuple[RiskEvidenceTrace, AnalysisBasis]:
    """Build one trace/basis pair from a saved Upload analysis payload."""
    image = _as_dict(data.get("image_analysis"))
    metadata = _as_dict(image.get("raw_metadata"))
    evidence_context = _as_dict(metadata.get("evidence_context"))
    manual = str(evidence_context.get("user_description") or "")
    ocr_text = str(image.get("ocr_text") or "")
    visual_observations = image.get("visual_observations") or image.get("key_observations") or []
    evidence_items = image.get("evidence_items") or []
    trace = build_risk_evidence_trace(
        str(data.get("risk_level") or "unknown"),
        question=str(data.get("question") or ""),
        raw_answer=" ".join(_clean_items(image.get("risks") or [])),
        manual_description=manual,
        ocr_text=ocr_text,
        visual_observations=visual_observations,
        evidence_items=evidence_items,
        has_visual_analysis=bool(evidence_context.get("has_visual_analysis")),
    )
    basis = build_analysis_basis(
        ocr_text=ocr_text,
        has_visual_analysis=bool(evidence_context.get("has_visual_analysis")),
        visual_observations=visual_observations,
        manual_description=manual,
        rules_matched=trace.rules_matched,
    )
    return trace, basis


def _matched_terms(text: str, terms: Iterable[str]) -> list[str]:
    hits = [term for term in terms if str(term).lower() in text]
    return list(dict.fromkeys(hits))


def _clean_items(values: Iterable[Any] | None) -> list[str]:
    return list(dict.fromkeys(" ".join(str(value or "").split()) for value in values or [] if str(value or "").strip()))


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return {}
