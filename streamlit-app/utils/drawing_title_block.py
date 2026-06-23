"""Deterministic title-block extraction for construction drawings (Phase 5.10C).

Pulls common title-block fields from OCR / selectable text using regex and
heuristics. Supports English and Traditional-Chinese labels. Confidence is kept
deliberately modest -- extraction is best-effort and must be field-verified.
"""

from __future__ import annotations

import re
from typing import Any


_LABEL_PATTERNS: dict[str, list[str]] = {
    "drawing_number": [
        r"(?:drawing\s*(?:no\.?|number|#)|dwg\.?\s*(?:no\.?|number)?)\s*[:：]?\s*([A-Za-z0-9][A-Za-z0-9\-_/().]{1,40})",
        r"(?:圖則編號|圖紙編號|圖號|圖則號)\s*[:：]?\s*([A-Za-z0-9][A-Za-z0-9\-_/().]{1,40})",
    ],
    "sheet_number": [
        r"(?:sheet\s*(?:no\.?|number|#)?)\s*[:：]?\s*([A-Za-z]{0,4}[-_/]?\d[A-Za-z0-9\-_/().]{0,28})",
        r"(?:圖紙頁碼|頁碼|張號|圖紙序號)\s*[:：]?\s*([A-Za-z]{0,4}[-_/]?\d[A-Za-z0-9\-_/().]{0,28})",
    ],
    "revision": [
        r"(?:rev(?:ision)?\.?)\s*[:：]?\s*([A-Za-z0-9]{1,6})",
        r"(?:版本|修訂(?:版)?|修改版)\s*[:：]?\s*([A-Za-z0-9]{1,6})",
    ],
    "scale": [
        r"(?:scale)\s*[:：]?\s*(1\s*[:：]\s*\d{1,5}|N\.?\s*T\.?\s*S\.?|NTS|AS\s*SHOWN|AS\s*INDICATED)",
        r"(?:比例(?:尺)?)\s*[:：]?\s*(1\s*[:：]\s*\d{1,5}|不按比例|另見圖示)",
    ],
    "drawing_date": [
        r"(?:date)\s*[:：]?\s*(\d{1,4}[-/.年]\d{1,2}[-/.月]\d{1,4}日?)",
        r"(?:日期|繪製日期|出圖日期)\s*[:：]?\s*(\d{1,4}[-/.年]\d{1,2}[-/.月]\d{1,4}日?)",
    ],
    "project_number": [
        r"(?:project\s*(?:no\.?|number|#)|contract\s*(?:no\.?|number))\s*[:：]?\s*([A-Za-z0-9][A-Za-z0-9\-_/().]{1,40})",
        r"(?:項目編號|工程編號|合約編號|項目編碼)\s*[:：]?\s*([A-Za-z0-9][A-Za-z0-9\-_/().]{1,40})",
    ],
    "sheet_title": [
        r"(?:sheet\s*title|drawing\s*title|title)\s*[:：]\s*([^\n\r]{2,80})",
        r"(?:圖紙名稱|圖則名稱|圖名|標題)\s*[:：]\s*([^\n\r]{2,80})",
    ],
}

_NOISE_VALUES = {"", "-", "—", "n/a", "na", "tbc", "tbd", "xxx", "待定"}

_TITLE_STOP = re.compile(
    r"\s{2,}|\s+(?:project|scale|date|rev(?:ision)?|drawing|sheet|dwg|no\.?|"
    r"比例|日期|修訂|版本|圖則|圖紙|項目|工程|合約)\b",
    flags=re.IGNORECASE,
)


def _trim_title(value: str) -> str:
    cut = _TITLE_STOP.search(value)
    return value[: cut.start()].strip() if cut else value.strip()


def _first_match(text: str, patterns: list[str], field_name: str = "") -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = " ".join(match.group(1).split()).strip(" :：-_")
            if field_name == "sheet_title":
                value = _trim_title(value)
            if value and value.lower() not in _NOISE_VALUES:
                return value[:80]
    return None


def extract_title_block(text: str, *, filename: str | None = None) -> dict[str, Any]:
    """Extract title-block fields from page text."""
    source = str(text or "")
    fields: dict[str, str] = {}
    basis: list[str] = []

    for field_name, patterns in _LABEL_PATTERNS.items():
        value = _first_match(source, patterns, field_name)
        if value:
            fields[field_name] = value

    if "drawing_number" not in fields and filename:
        stem = re.split(r"[\\/]", str(filename))[-1]
        stem = re.sub(r"\.[A-Za-z0-9]+$", "", stem)
        guess = re.search(r"([A-Za-z]{1,3}[-_]?\d{2,4}[A-Za-z0-9\-_]*)", stem)
        if guess:
            fields["drawing_number"] = guess.group(1)[:80]
            basis.append("圖則編號來自檔名推斷")

    found = [name for name in _LABEL_PATTERNS if name in fields]
    if found:
        basis.append("標題欄欄位：" + "、".join(found))

    core = {"drawing_number", "sheet_number", "sheet_title", "scale", "revision"}
    hits = len(core.intersection(fields))
    confidence = round(min(0.6, 0.12 * hits), 3)

    return {"fields": fields, "confidence": confidence, "basis": basis}
