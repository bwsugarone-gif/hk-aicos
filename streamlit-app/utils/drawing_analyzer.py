"""End-to-end drawing analysis orchestrator (Phase 5.10B-E).

Pipeline: ingest -> per-page title-block extraction -> page classification
(optionally enriched by existing AI vision) -> issue / missing-info / coordination
findings -> CAD/BIM handoff items -> aggregated :class:`DrawingDocument`.

Everything degrades gracefully: no OCR, no vision and no rasterisation still
yields a usable (if shallower) result. No raw errors are surfaced to the UI;
technical detail is collected in ``technical_notes`` for a diagnostic expander.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .drawing_classifier import classify_drawing_page
from .drawing_handoff import extract_page_findings, generate_handoff_items
from .drawing_ingest import ingest_drawing, rasterize_pdf_page
from .drawing_models import (
    ANALYSIS_DEPTHS,
    CadBimHandoffItem,
    DrawingDocument,
    DrawingPageAnalysis,
)
from .drawing_store import (
    append_drawing_document,
    append_drawing_pages,
    new_document_id,
    new_page_id,
)
from .drawing_title_block import extract_title_block

_DEPTH_PAGE_CAP = {"quick": 5, "standard": 12, "detailed": 20}


@dataclass
class DrawingAnalysisResult:
    document: DrawingDocument
    pages: list[DrawingPageAnalysis] = field(default_factory=list)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _vision_text_for(image_path: str | None, *, enabled: bool, notes: list[str]) -> str:
    """Best-effort AI-vision enrichment; returns extra text or empty string."""
    if not enabled or not image_path:
        return ""
    try:
        from .vision_client import analyze_image_with_vision

        result = analyze_image_with_vision(image_path)
    except Exception:
        return ""
    if not isinstance(result, dict) or not result.get("performed"):
        return ""
    parts = list(result.get("observations") or [])
    if result.get("extracted_text"):
        parts.append(str(result["extracted_text"]))
    notes.append("已使用 AI 視覺輔助分析部分頁面。")
    return " ".join(parts)


def _vision_ready() -> bool:
    try:
        from .vision_client import get_vision_readiness

        return bool(get_vision_readiness().get("configured"))
    except Exception:
        return False


def analyze_drawing(
    file_path: str | Path,
    *,
    project_ref: str | None = None,
    description: str | None = None,
    discipline_hint: str | None = None,
    file_name: str | None = None,
    max_pages: int = 12,
    depth: str = "standard",
    use_vision: bool | None = None,
    persist: bool = True,
) -> DrawingAnalysisResult:
    """Analyze one drawing file and return (and optionally persist) the result."""
    path = Path(file_path)
    depth = depth if depth in ANALYSIS_DEPTHS else "standard"
    page_cap = min(int(max_pages or 12), _DEPTH_PAGE_CAP.get(depth, 12))
    source_name = file_name or path.name

    vision_enabled = use_vision if use_vision is not None else (depth in {"standard", "detailed"} and _vision_ready())

    ingest = ingest_drawing(path, max_pages=page_cap)
    technical_notes: list[str] = list(ingest.get("notes") or [])
    document_id = new_document_id()
    vision_used = False

    page_models: list[DrawingPageAnalysis] = []
    all_issues: list[str] = []
    all_missing: list[str] = []
    all_coord: list[str] = []
    all_actions: list[str] = []
    handoff_items: list[CadBimHandoffItem] = []
    disciplines: list[str] = []
    page_types: list[str] = []

    for raw_page in ingest.get("pages", []):
        page_number = int(raw_page.get("page_number") or (len(page_models) + 1))
        text = str(raw_page.get("text") or "")
        image_path = raw_page.get("image_path")

        title = extract_title_block(text, filename=source_name)
        fields = title["fields"]

        # Optional vision enrichment (image uploads, or rasterised PDF pages in detailed mode).
        vision_text = ""
        if vision_enabled:
            candidate_image = image_path
            temp_image: Path | None = None
            if not candidate_image and depth == "detailed" and ingest.get("file_type") == "pdf":
                temp_image = rasterize_pdf_page(path, page_number)
                candidate_image = str(temp_image) if temp_image else None
            vision_text = _vision_text_for(candidate_image, enabled=True, notes=technical_notes)
            if vision_text:
                vision_used = True
            if temp_image is not None:
                try:
                    temp_image.unlink()
                except OSError:
                    pass

        classification = classify_drawing_page(
            text,
            filename=source_name,
            discipline_hint=discipline_hint,
            sheet_number=fields.get("sheet_number") or fields.get("drawing_number"),
            sheet_title=fields.get("sheet_title"),
            vision_text=vision_text or None,
        )

        page_payload = {
            "page_number": page_number,
            "text": text,
            "page_type": classification["page_type"],
            "discipline": classification["discipline"],
            "title_block_fields": fields,
        }
        findings = extract_page_findings(page_payload)
        items = generate_handoff_items(page_payload, findings)
        handoff_items.extend(items)
        all_actions.extend(item.title for item in items)

        page_model = DrawingPageAnalysis(
            page_id=new_page_id(document_id, page_number),
            document_id=document_id,
            page_number=page_number,
            created_at=_now(),
            page_type=classification["page_type"],
            discipline=classification["discipline"],
            sheet_number=fields.get("sheet_number"),
            sheet_title=fields.get("sheet_title"),
            drawing_number=fields.get("drawing_number"),
            revision=fields.get("revision"),
            scale=fields.get("scale"),
            drawing_date=fields.get("drawing_date"),
            project_number=fields.get("project_number"),
            level_hint=fields.get("level_hint"),
            classification_confidence=classification["confidence"],
            classification_basis=classification["basis"],
            title_block_fields=fields,
            extracted_text_excerpt=text[:1200],
            drawing_issues=findings["drawing_issues"],
            missing_information=findings["missing_information"],
            coordination_flags=findings["coordination_flags"],
            ocr_status=str(raw_page.get("ocr_status") or "NOT_ATTEMPTED"),
        )
        page_models.append(page_model)
        all_issues.extend(findings["drawing_issues"])
        all_missing.extend(findings["missing_information"])
        all_coord.extend(findings["coordination_flags"])
        if classification["discipline"] != "unknown":
            disciplines.append(classification["discipline"])
        page_types.append(classification["page_type"])

    disciplines = list(dict.fromkeys(disciplines))
    page_types = list(dict.fromkeys(page_types))
    summary = _build_summary(source_name, ingest, disciplines, page_types, handoff_items)

    document = DrawingDocument(
        document_id=document_id,
        created_at=_now(),
        updated_at=_now(),
        project_ref=project_ref,
        source_file_name=source_name,
        description=description,
        discipline_hint=discipline_hint,
        analysis_depth=depth,
        page_count=int(ingest.get("page_count") or len(page_models)),
        analyzed_page_count=len(page_models),
        disciplines=disciplines,
        page_types=page_types,
        summary=summary,
        drawing_issues=list(dict.fromkeys(all_issues)),
        missing_information=list(dict.fromkeys(all_missing)),
        coordination_flags=list(dict.fromkeys(all_coord)),
        cad_bim_actions=list(dict.fromkeys(all_actions)),
        handoff_items=handoff_items,
        page_ids=[page.page_id for page in page_models],
        ingestion_status=str(ingest.get("ingestion_status") or "unknown"),
        vision_used=vision_used,
        technical_notes=list(dict.fromkeys(technical_notes)),
        metadata={
            "file_type": ingest.get("file_type"),
            "depth": depth,
            "pages_without_text": int(ingest.get("pages_without_text") or 0),
            "pdf_metadata": ingest.get("metadata") or {},
        },
    )

    if persist:
        document = append_drawing_document(document)
        append_drawing_pages(page_models)

    return DrawingAnalysisResult(document=document, pages=page_models)


def _build_summary(
    source_name: str,
    ingest: dict[str, Any],
    disciplines: list[str],
    page_types: list[str],
    handoff_items: list[CadBimHandoffItem],
) -> str:
    from .drawing_models import DISCIPLINE_LABELS_ZH, PAGE_TYPE_LABELS_ZH

    page_count = ingest.get("page_count") or 0
    disc_label = "、".join(DISCIPLINE_LABELS_ZH.get(d, d) for d in disciplines) or "未能確定"
    type_label = "、".join(PAGE_TYPE_LABELS_ZH.get(t, t) for t in page_types if t != "unknown") or "未能分類"
    return (
        f"已分析圖紙《{source_name}》，共 {page_count} 頁。"
        f"涵蓋專業：{disc_label}；圖紙類型：{type_label}。"
        f"已產生 {len(handoff_items)} 項 CAD/BIM 交接事項待跟進。"
    )
