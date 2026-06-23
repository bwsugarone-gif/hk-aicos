"""Drawing page-type and discipline classification (Phase 5.10D).

Classification is deterministic and text-based so it works with no network /
vision access. When vision findings are available (Gemini / Anthropic image
understanding, already part of the app), their text is merged in to strengthen
the signal. Otherwise the classifier falls back to OCR text, sheet-number
prefixes, filename hints and an optional discipline hint.
"""

from __future__ import annotations

import re
from typing import Any

from .drawing_models import DRAWING_DISCIPLINES, DRAWING_PAGE_TYPES


_PAGE_TYPE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "title_sheet": ("title sheet", "cover sheet", "drawing list", "sheet index", "封面", "圖紙目錄", "圖則清單", "標題頁"),
    "reflected_ceiling_plan": ("reflected ceiling", "rcp", "ceiling plan", "天花反射", "天花平面", "天花圖"),
    "floor_plan": ("floor plan", "layout plan", "general arrangement", "key plan", "平面圖", "平面佈置", "樓面平面", "佈置圖"),
    "elevation": ("elevation", "立面圖", "立面"),
    "section": ("section", "cross section", "longitudinal section", "剖面圖", "剖面", "截面圖", "斷面"),
    "detail": ("detail", "typical detail", "enlarged detail", "大樣", "詳圖", "節點圖", "細部"),
    "schedule": ("schedule", "door schedule", "window schedule", "finishes schedule", "明細表", "門窗表", "附表", "一覽表"),
    "specification": ("specification", "general notes", "spec.", "規格", "技術規範", "施工說明", "一般註解"),
    "legend": ("legend", "symbol legend", "abbreviation", "圖例", "符號說明", "縮寫"),
    "diagram": ("diagram", "schematic", "single line", "riser diagram", "示意圖", "系統圖", "原理圖", "圖解"),
}

_DISCIPLINE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "structural": ("structural", "rc detail", "rebar", "reinforcement", "beam", "column", "slab", "footing", "foundation", "pile", "結構", "鋼筋", "梁", "柱", "樓板", "樁", "基礎", "承台"),
    "fire_services": ("fire service", "fire services", "sprinkler", "fire hydrant", "fire alarm", "hose reel", "smoke detector", "fs layout", "f.s.", "消防", "灑水", "消防栓", "消防喉", "火警", "煙感"),
    "drainage": ("drainage", "above ground drainage", "below ground drainage", "sewerage", "manhole", "pipe fall", "stormwater", "storm water", "foul water", "drain", "排水", "渠務", "沙井", "污水", "雨水"),
    "mep": ("mechanical", "electrical", "plumbing", "hvac", "ductwork", "duct", "pipe", "cable tray", "lighting", "mvac", "abwf", "building services", "機電", "屋宇裝備", "通風", "風管", "電氣", "照明", "給排水", "水管", "橋架"),
    "facade": ("facade", "curtain wall", "cladding", "幕牆", "外牆", "包覆"),
    "landscape": ("landscape", "softscape", "hardscape", "planting", "園境", "綠化", "景觀"),
    "interior": ("interior", "fit-out", "fitout", "id layout", "ceiling", "reflected ceiling", "rcp", "partition", "finish schedule", "furniture", "室內", "裝修", "間隔", "天花", "傢俬"),
    "builder_works": ("builder's works", "builders works", "builder's work", "bwic", "blockout", "opening", "penetration", "sleeve", "civil works", "kerb", "pavement", "土木", "建造工程", "預留洞", "穿牆", "套管"),
    "architecture": ("architectural", "architecture", "arch.", "general arrangement", "layout", "floor plan", "room", "door", "wall", "finish", "建築", "則樓", "間隔平面", "房間", "門", "牆", "飾面"),
}

_PREFIX_DISCIPLINE: dict[str, str] = {
    "A": "architecture", "AR": "architecture",
    "S": "structural", "ST": "structural",
    "C": "builder_works", "CW": "builder_works", "BW": "builder_works",
    "M": "mep", "E": "mep", "P": "mep", "ME": "mep", "EL": "mep", "BS": "mep",
    "FS": "fire_services", "FP": "fire_services",
    "D": "drainage", "DR": "drainage", "PD": "drainage",
    "L": "landscape", "LS": "landscape",
    "ID": "interior", "IN": "interior",
    "FA": "facade",
}

# Sheet-code prefixes that are too ambiguous to trust when found loose in text /
# filenames (``BW`` is the Buildway project prefix, not "builder's works" here).
_CODE_PREFIX_DENYLIST = {"BW"}
_CODE_TOKEN = re.compile(r"\b([A-Za-z]{1,3})[-/]\d{2,4}\b")


def _count_hits(text: str, keywords: tuple[str, ...]) -> tuple[int, list[str]]:
    matched = [word for word in keywords if word in text]
    return len(matched), matched


def _discipline_from_sheet(sheet_number: str | None) -> str | None:
    if not sheet_number:
        return None
    match = re.match(r"\s*([A-Za-z]{1,3})", str(sheet_number))
    if not match:
        return None
    return _PREFIX_DISCIPLINE.get(match.group(1).upper())


def _disciplines_from_codes(text: str) -> dict[str, int]:
    """Map drawing-code tokens (e.g. ``A-101``/``FS-03``) found loose in OCR text
    or the filename to disciplines. A light signal that reinforces keywords."""
    scores: dict[str, int] = {}
    for match in _CODE_TOKEN.finditer(text):
        prefix = match.group(1).upper()
        if prefix in _CODE_PREFIX_DENYLIST:
            continue
        discipline = _PREFIX_DISCIPLINE.get(prefix)
        if discipline:
            scores[discipline] = scores.get(discipline, 0) + 1
    return scores


def classify_drawing_page(
    text: str,
    *,
    filename: str | None = None,
    discipline_hint: str | None = None,
    sheet_number: str | None = None,
    sheet_title: str | None = None,
    vision_text: str | None = None,
) -> dict[str, Any]:
    """Classify one page's type and discipline."""
    haystack = " ".join(
        part.lower()
        for part in (text or "", filename or "", sheet_title or "", vision_text or "")
        if part
    )
    basis: list[str] = []

    type_scores: dict[str, int] = {}
    for page_type, keywords in _PAGE_TYPE_KEYWORDS.items():
        count, _matched = _count_hits(haystack, keywords)
        if count:
            type_scores[page_type] = count

    page_type = "unknown"
    if type_scores:
        ordered = sorted(type_scores.items(), key=lambda kv: kv[1], reverse=True)
        strong = [name for name, score in ordered if score == ordered[0][1]]
        if len(strong) > 1 or (len(ordered) > 1 and len([s for _n, s in ordered if s >= 1]) >= 3):
            page_type = "mixed"
            basis.append("頁面類型：偵測到多種圖紙內容")
        else:
            page_type = ordered[0][0]
            basis.append(f"頁面類型關鍵字命中：{page_type}")

    discipline = "unknown"
    hint = str(discipline_hint or "").strip().lower()
    if hint in DRAWING_DISCIPLINES and hint != "unknown":
        discipline = hint
        basis.append("專業範疇來自使用者提示")
    else:
        prefix_discipline = _discipline_from_sheet(sheet_number)
        discipline_scores: dict[str, int] = {}
        for name, keywords in _DISCIPLINE_KEYWORDS.items():
            count, _matched = _count_hits(haystack, keywords)
            if count:
                discipline_scores[name] = count
        for name, count in _disciplines_from_codes(haystack).items():
            discipline_scores[name] = discipline_scores.get(name, 0) + count
        if prefix_discipline:
            discipline_scores[prefix_discipline] = discipline_scores.get(prefix_discipline, 0) + 2
            basis.append(f"專業範疇參考圖紙編號前綴：{prefix_discipline}")
        if discipline_scores:
            discipline = max(discipline_scores.items(), key=lambda kv: kv[1])[0]
            if not any("專業範疇" in line for line in basis):
                basis.append(f"專業範疇關鍵字命中：{discipline}")

    confidence = 0.0
    if page_type != "unknown":
        confidence += 0.3
    if discipline != "unknown":
        confidence += 0.3
    if vision_text:
        confidence += 0.1
        basis.append("已參考 AI 視覺輔助判斷")
    confidence = round(min(0.75, confidence), 3)

    if page_type not in DRAWING_PAGE_TYPES:
        page_type = "unknown"
    if discipline not in DRAWING_DISCIPLINES:
        discipline = "unknown"

    return {"page_type": page_type, "discipline": discipline, "confidence": confidence, "basis": basis}
