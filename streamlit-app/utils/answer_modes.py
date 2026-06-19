"""Answer-mode contracts for practical Ask AICOS responses."""

from __future__ import annotations


DEFAULT_ANSWER_MODE = "site_simple"

ANSWER_MODE_LABELS = {
    "site_simple": "簡明現場版",
    "foreman_followup": "管工跟進版",
    "safety_officer_detail": "安全主任詳細版",
    "legal_source_detail": "法例來源詳細版",
}

ANSWER_MODE_SECTIONS = {
    "site_simple": ("最簡單講", "判斷依據", "主要風險 / 影響", "建議", "需確認事項", "來源 / 限制"),
    "foreman_followup": ("結論", "風險位置", "建議", "負責角色", "跟進紀錄", "來源摘要"),
    "safety_officer_detail": ("初步判斷", "主要風險", "控制措施", "檢查清單", "官方來源摘要", "合規提醒"),
    "legal_source_detail": ("答案摘要", "相關官方來源", "主要要求", "實務解讀", "限制與免責"),
}


def normalize_answer_mode(value: str) -> str:
    mode = str(value or "").strip()
    return mode if mode in ANSWER_MODE_LABELS else DEFAULT_ANSWER_MODE
