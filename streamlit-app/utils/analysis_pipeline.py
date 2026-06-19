"""Shared OCR, Vision, evidence, memory, and follow-up production pipeline."""

from __future__ import annotations

import tempfile
from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from .evidence_models import AnalysisBasis, RiskEvidenceTrace
from .file_loader import load_file_content
from .followup_store import generate_followups_from_risk_trace
from .image_safety_hardening import HOT_WORK_CATEGORIES, build_concise_image_summary
from .image_understanding import process_image_with_understanding
from .project_memory_store import append_memory
from .provider_health import ProviderHealth, get_provider_health
from .risk_evidence import build_analysis_basis, build_risk_evidence_trace
from .site_record_store import save_image_analysis_record
from .vision_client import get_vision_readiness


@dataclass
class AnalysisPipelineResult:
    text_detection_summary: str
    vision_summary: str
    manual_description_summary: str
    image_category: str
    visual_confidence: float
    analysis_basis: AnalysisBasis
    risk_evidence_trace: RiskEvidenceTrace
    agent_answer: str
    memory_record_id: str = ""
    followup_ids: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    technical_status: dict[str, Any] = field(default_factory=dict)
    risk_level: str = "需人工覆核"
    observations: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    confirmations: list[str] = field(default_factory=list)
    image_analysis: dict[str, Any] = field(default_factory=dict)
    legacy_understanding: dict[str, Any] = field(default_factory=dict)
    site_record_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        # Legacy prompt/context is only for the existing Upload agent chain;
        # it must not leak into normal Workspace/session display payloads.
        payload.pop("legacy_understanding", None)
        return _json_safe(payload)


def process_uploaded_file_for_analysis(
    uploaded_file: Any,
    file_name: str | None = None,
    manual_description: str = "",
    project_ref: str | None = None,
    question: str = "",
    analysis_type: str = "工地安全分析",
    provider_health: ProviderHealth | None = None,
    save_memory: bool = False,
) -> AnalysisPipelineResult:
    """Materialize one user upload temporarily and run the shared pipeline."""
    name = str(file_name or getattr(uploaded_file, "name", "uploaded-file") or "uploaded-file")
    data = _upload_bytes(uploaded_file)
    suffix = Path(name).suffix.lower() or ".bin"
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix="aicos-analysis-", suffix=suffix, delete=False) as handle:
            handle.write(data)
            temporary_path = Path(handle.name)
        file_data = load_file_content(temporary_path)
        file_data["filename"] = name
        return analyze_file_data_for_pipeline(
            file_data,
            file_name=name,
            manual_description=manual_description,
            project_ref=project_ref,
            question=question,
            analysis_type=analysis_type,
            provider_health=provider_health,
            save_memory=save_memory,
        )
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass


def analyze_file_data_for_pipeline(
    file_data: dict[str, Any],
    *,
    file_name: str,
    manual_description: str = "",
    project_ref: str | None = None,
    question: str = "",
    analysis_type: str = "工地安全分析",
    provider_health: ProviderHealth | None = None,
    save_memory: bool = False,
) -> AnalysisPipelineResult:
    """Analyse already-extracted file data; used by Workspace and Upload."""
    health = provider_health or get_provider_health()
    manual = " ".join(str(manual_description or "").split())
    file_type = str(file_data.get("type") or "unknown")
    extracted_text = str(
        file_data.get("extracted_text")
        or (file_data.get("content") if file_type != "image" else "")
        or ""
    ).strip()
    ocr_status = str(file_data.get("ocr_status") or "NOT_ATTEMPTED")
    text_summary = (
        "已偵測到可用文字。" if extracted_text
        else "未偵測到清晰文字。"
    )
    manual_summary = "已使用使用者補充的現場描述。" if manual else "未有使用者補充描述。"

    image_analysis: dict[str, Any] = {}
    legacy: dict[str, Any] = {}
    if file_type == "image":
        image_input = dict(file_data)
        image_input["filename"] = file_name
        image_input["manual_context"] = manual
        image_input["selected_analysis_type"] = analysis_type
        legacy = process_image_with_understanding(image_input)
        image_analysis = dict(legacy.get("analysis_result") or {})
        legacy = _strip_raw_errors(legacy)
        image_analysis = _strip_raw_errors(image_analysis)

    metadata = dict(image_analysis.get("raw_metadata") or {})
    evidence_context = dict(metadata.get("evidence_context") or {})
    vision_status = dict(metadata.get("vision") or {})
    has_visual = bool(evidence_context.get("has_visual_analysis"))
    visual_confidence = float(image_analysis.get("visual_confidence") or 0.0)
    category = str(
        image_analysis.get("image_category")
        or image_analysis.get("detected_category")
        or ("document" if file_type != "image" else "unknown")
    )
    concise = build_concise_image_summary(image_analysis) if image_analysis else {
        "observations": ([extracted_text[:240]] if extracted_text else []),
        "risks": [], "recommendations": [],
        "confirmations": ["文件內容、適用工序及現場狀況"], "risk_level": "需人工覆核",
    }
    risk_level = _safe_risk_level(category, concise, has_visual, manual, extracted_text)
    trace = build_risk_evidence_trace(
        risk_level,
        question=question,
        raw_answer=" ".join(concise.get("risks") or []),
        manual_description=manual,
        ocr_text=extracted_text,
        visual_observations=image_analysis.get("visual_observations") or image_analysis.get("key_observations") or [],
        evidence_items=image_analysis.get("evidence_items") or [],
        has_visual_analysis=has_visual,
    )
    basis = build_analysis_basis(
        ocr_text=extracted_text,
        has_visual_analysis=has_visual,
        visual_observations=image_analysis.get("visual_observations") or [],
        manual_description=manual,
        rules_matched=trace.rules_matched,
    )
    warnings = []
    if file_type == "image" and vision_status.get("status") == "error":
        warnings.append("AI 視覺暫時未能完成；已改用現場描述及人工覆核模式。")
    elif file_type == "image" and not has_visual:
        warnings.append("AI 視覺未設定或未有可用結果；AICOS 沒有假設相片內容。")
    if not has_visual and not manual and not extracted_text:
        warnings.append("未能確認相片中的具體工序；請補充工序描述或啟用 AI 視覺。")

    recommendations = _recommendations(image_analysis, trace)
    confirmations = list(dict.fromkeys([*(concise.get("confirmations") or []), *trace.missing_confirmations]))[:6]
    observations = list(concise.get("observations") or [])[:6]
    agent_answer = _agent_answer(risk_level, observations, trace, recommendations, confirmations)
    vision_summary = (
        "已根據相片可見內容完成分析。" if has_visual
        else ("暫時未能完成，已採用安全備用流程。" if vision_status.get("status") == "error" else "未設定或未有可用結果。")
    )
    readiness = get_vision_readiness()
    technical = {
        "text_llm_available": health.text_llm_available,
        "vision_configured": readiness["configured"],
        "vision_last_attempt": readiness["last_attempt"],
        "vision_error_category": readiness["error_category"],
        "web_search_available": health.web_search_available,
        "ocr_status": ocr_status,
        "vision_provider_label": readiness["provider_label"],
    }
    result = AnalysisPipelineResult(
        text_detection_summary=text_summary,
        vision_summary=vision_summary,
        manual_description_summary=manual_summary,
        image_category=category,
        visual_confidence=visual_confidence,
        analysis_basis=basis,
        risk_evidence_trace=trace,
        agent_answer=agent_answer,
        warnings=warnings,
        technical_status=technical,
        risk_level=risk_level,
        observations=observations,
        recommendations=recommendations,
        confirmations=confirmations,
        image_analysis=image_analysis,
        legacy_understanding=legacy,
    )
    if save_memory:
        try:
            _persist_pipeline_result(result, file_name, project_ref, analysis_type)
        except (OSError, PermissionError, ValueError):
            result.warnings.append("分析已完成，但暫時未能寫入本機記憶；請在 Records 頁確認儲存狀態。")
    return result


def _persist_pipeline_result(
    result: AnalysisPipelineResult,
    file_name: str,
    project_ref: str | None,
    analysis_type: str,
) -> None:
    site_record_id = ""
    if result.image_analysis:
        site_record = save_image_analysis_record(result.image_analysis, filename=file_name)
        site_record_id = site_record.record_id
    memory = append_memory({
        "project_ref": project_ref,
        "source_type": "upload_analysis",
        "title": f"上載分析：{file_name}",
        "summary": result.agent_answer[:2500],
        "analysis_type": analysis_type,
        "risk_level": result.risk_level,
        "confidence": result.visual_confidence,
        "evidence_sources": result.risk_evidence_trace.evidence_sources,
        "tags": result.risk_evidence_trace.rules_matched,
        "status": "open",
        "priority": "high" if result.risk_level == "高風險" else "medium",
        "linked_record_ids": [site_record_id] if site_record_id else [],
        "source_file_name": file_name,
        "source_route": "/AICOS_Workspace",
        "metadata": {"image_category": result.image_category},
    })
    followups = generate_followups_from_risk_trace(
        result.risk_evidence_trace,
        project_ref,
        source_memory_id=memory.memory_id,
    )
    result.memory_record_id = memory.memory_id
    result.followup_ids = [item.followup_id for item in followups]
    result.site_record_id = site_record_id


def _safe_risk_level(category: str, concise: dict, has_visual: bool, manual: str, text: str) -> str:
    evidence_text = " ".join((manual, text, " ".join(concise.get("observations") or []))).lower()
    hot_signal = category in HOT_WORK_CATEGORIES or any(
        term in evidence_text for term in ("磨機", "切割", "火花", "grinder", "cutting", "sparks", "hot work")
    )
    if hot_signal and (has_visual or manual or text):
        return "高風險"
    if not has_visual and not manual and not text:
        return "需人工覆核"
    return str(concise.get("risk_level") or "需人工覆核")


def _recommendations(image_analysis: dict, trace: RiskEvidenceTrace) -> list[str]:
    values = []
    for item in image_analysis.get("recommended_followups") or []:
        if isinstance(item, dict):
            action = str(item.get("action") or item.get("title") or "").strip()
            if action:
                values.append(action)
    if not values and trace.rules_matched:
        values.append("由管工／安全主任按現場工序覆核並落實控制措施。")
    if not values:
        values.append("補充工序、位置、工具及現有防護措施後再作判斷。")
    return list(dict.fromkeys(values))[:5]


def _agent_answer(
    risk_level: str,
    observations: list[str],
    trace: RiskEvidenceTrace,
    recommendations: list[str],
    confirmations: list[str],
) -> str:
    seen = observations or ["目前沒有足夠可觀察資料支持具體工序判斷。"]
    basis = [*trace.triggered_by, *trace.rules_matched] or [trace.confidence_reason]
    return "\n".join((
        "## 最簡單講", f"- 初步風險：{risk_level}",
        "## 判斷依據", *[f"- {item}" for item in basis[:4]],
        "## 相片所見", *[f"- {item}" for item in seen[:4]],
        "## 主要風險 / 影響", f"- {trace.final_reason}",
        "## 建議", *[f"- {item}" for item in recommendations[:4]],
        "## 需確認事項", *[f"- {item}" for item in confirmations[:5]],
        "## 來源 / 限制", "- 分析只使用已偵測文字、可見證據及使用者補充；仍須由現場負責人覆核。",
    ))


def _upload_bytes(uploaded_file: Any) -> bytes:
    if isinstance(uploaded_file, (bytes, bytearray)):
        return bytes(uploaded_file)
    if hasattr(uploaded_file, "getvalue"):
        return bytes(uploaded_file.getvalue())
    if hasattr(uploaded_file, "read"):
        return bytes(uploaded_file.read())
    raise TypeError("Unsupported uploaded file object")


def _strip_raw_errors(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _strip_raw_errors(item)
            for key, item in value.items()
            if str(key).lower() not in {"error", "exception", "traceback"}
        }
    if isinstance(value, list):
        return [_strip_raw_errors(item) for item in value]
    return value


def _json_safe(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return _json_safe(asdict(value))
    if isinstance(value, Path):
        return value.name
    if isinstance(value, dict):
        return {
            str(key): _json_safe(item)
            for key, item in value.items()
            if str(key).lower() not in {"api_key", "secret", "token", "error", "exception", "traceback"}
        }
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)
