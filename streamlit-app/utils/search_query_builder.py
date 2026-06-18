"""Build concise Hong Kong-focused web queries for Ask AICOS."""

from __future__ import annotations

import re


_MAX_QUESTION_LENGTH = 220
_MAX_QUERY_LENGTH = 420

_OFFICIAL_DOMAINS = {
    "law_regulation": (
        "elegislation.gov.hk",
        "e-legislation.gov.hk",
        "labour.gov.hk",
        "bd.gov.hk",
        "gov.hk",
    ),
    "safety": (
        "labour.gov.hk",
        "emsd.gov.hk",
        "bd.gov.hk",
        "gov.hk",
    ),
    "construction_method": ("devb.gov.hk", "bd.gov.hk", "emsd.gov.hk", "gov.hk"),
    "material": ("devb.gov.hk", "bd.gov.hk", "emsd.gov.hk", "gov.hk"),
    "document_search": ("devb.gov.hk", "bd.gov.hk", "labour.gov.hk", "gov.hk"),
    "site_followup": ("labour.gov.hk", "bd.gov.hk", "gov.hk"),
    "general": ("gov.hk", "devb.gov.hk", "bd.gov.hk"),
}

_TRUSTED_TERMS = {
    "law_regulation": "香港 建築 法例 規例 指引 Code of Practice",
    "safety": "香港 地盤 安全 勞工處 建造業議會 Code of Practice Guidance Notes",
    "construction_method": "香港 建築 施工方法 屋宇署 發展局 建造業議會 指引",
    "material": "香港 建築 物料 規格 屋宇署 機電工程署 指引",
    "document_search": "香港 建築 文件 指引 守則 屋宇署 發展局",
    "site_followup": "香港 地盤 跟進 安全 指引",
    "general": "香港 建築 地盤 指引",
}

_GENERAL_TERMS = {
    "law_regulation": "香港 法例",
    "safety": "香港 地盤安全",
    "construction_method": "香港 建築施工",
    "material": "香港 建築物料",
    "document_search": "香港 建築文件",
    "site_followup": "香港 地盤跟進",
    "general": "香港 建築",
}


def build_hk_official_query(question: str, question_type: str, mode: str) -> str:
    """Return a bounded query that reflects the selected trust mode."""
    cleaned_question = _clean_text(question)[:_MAX_QUESTION_LENGTH]
    normalized_type = question_type if question_type in _TRUSTED_TERMS else "general"
    normalized_mode = mode if mode in {"official_only", "trusted_first", "general_web"} else "trusted_first"

    if normalized_mode == "official_only":
        domains = _OFFICIAL_DOMAINS[normalized_type]
        domain_clause = "(" + " OR ".join(f"site:{domain}" for domain in domains) + ")"
        terms = _GENERAL_TERMS[normalized_type]
        if normalized_type in {"law_regulation", "safety"}:
            terms = _TRUSTED_TERMS[normalized_type]
        query = f"{cleaned_question} {terms} {domain_clause}"
    elif normalized_mode == "trusted_first":
        query = f"{cleaned_question} {_TRUSTED_TERMS[normalized_type]}"
    else:
        query = f"{cleaned_question} {_GENERAL_TERMS[normalized_type]}"

    return _clean_text(query)[:_MAX_QUERY_LENGTH].strip()


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()
