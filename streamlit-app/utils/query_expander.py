"""Deterministic safety-query expansion without embeddings or an LLM."""

from __future__ import annotations


HOT_WORK_QUERY_TERMS = (
    "熱工", "熱工序", "熱工許可", "明火", "火花", "焊接", "電焊", "氣焊", "燒焊",
    "切割", "打磨", "磨機", "砂輪機", "防火氈", "滅火筒", "防火監察", "工後巡查",
    "hot work", "permit to work", "fire watch",
)
WORK_AT_HEIGHT_QUERY_TERMS = (
    "高處工作", "高空工作", "離地", "2米", "2 米", "墮下", "工作平台", "護欄", "踢腳板", "安全帶",
    "working at height", "fall prevention",
)


def expand_safety_query(question: str) -> list[str]:
    """Expand only the safety topic(s) explicitly present in the question."""
    text = " ".join(str(question or "").lower().split())
    hot_work, work_at_height = safety_query_profile(text)
    expanded = [str(question or "").strip()] if str(question or "").strip() else []
    if hot_work:
        expanded.extend(HOT_WORK_QUERY_TERMS)
    if work_at_height:
        expanded.extend(WORK_AT_HEIGHT_QUERY_TERMS)
    return list(dict.fromkeys(item for item in expanded if item))


def safety_query_profile(question: str) -> tuple[bool, bool]:
    text = " ".join(str(question or "").lower().split())
    hot_work = any(term in text for term in HOT_WORK_QUERY_TERMS)
    work_at_height = any(term in text for term in WORK_AT_HEIGHT_QUERY_TERMS)
    return hot_work, work_at_height
