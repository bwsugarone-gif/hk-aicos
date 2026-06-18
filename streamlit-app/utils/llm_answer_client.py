"""Structured construction Q&A client with practical, source-safe answers."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable

from .analysis_models import KnowledgeSnippet, QAResponse, SearchResult, SourceCitation
from .answer_modes import ANSWER_MODE_LABELS, ANSWER_MODE_SECTIONS, DEFAULT_ANSWER_MODE, normalize_answer_mode
from .official_sources import citation_from_source
from .source_reference_extractor import (
    extract_source_reference,
    extract_source_references,
    format_source_reference,
)


SAFETY_TYPES = {"safety", "law_regulation"}


def answer_question(
    question: str,
    question_type: str,
    search_scope: str,
    context_snippets: Iterable[KnowledgeSnippet | SearchResult | dict[str, Any]] | None = None,
    answer_mode: str = DEFAULT_ANSWER_MODE,
) -> QAResponse:
    """Answer through the configured provider or a practical local fallback."""
    question = str(question or "").strip()
    mode = normalize_answer_mode(answer_mode)
    contexts = list(context_snippets or [])[:15]
    if not question:
        return QAResponse(
            answer="請先輸入具體工程問題。",
            practical_recommendations=["加入位置、工序、日期及已知風險，有助提高答案實用性。"],
            risk_level="unknown",
            confidence=0.0,
            used_search_scope=search_scope,
            fallback_used=True,
        )

    provider = _select_provider()
    if provider is None:
        return _fallback_answer(question, question_type, search_scope, contexts, mode)

    provider_name, api_key, model = provider
    system_prompt = _system_prompt(question_type, mode)
    user_message = _user_message(question, question_type, search_scope, contexts, mode)
    try:
        raw_answer = _call_existing_provider_router(provider_name, api_key, model, system_prompt, user_message)
        return _parse_provider_answer(raw_answer, question_type, search_scope, contexts, model, mode, question)
    except Exception as exc:
        response = _fallback_answer(question, question_type, search_scope, contexts, mode)
        response.model_name = f"local-fallback ({provider_name} error)"
        response.answer += f"\n\n> AI 供應商暫時未能回應（{type(exc).__name__}），以上為本機後備結果。"
        return response


def _select_provider() -> tuple[str, str, str] | None:
    configurations = {
        "claude": ("Claude", "ANTHROPIC_API_KEY", "claude-opus-4-5"),
        "anthropic": ("Claude", "ANTHROPIC_API_KEY", "claude-opus-4-5"),
        "openai": ("OpenAI", "OPENAI_API_KEY", "gpt-4.1-mini"),
        "deepseek": ("DeepSeek", "DEEPSEEK_API_KEY", "deepseek-chat"),
        "gemini": ("Gemini", "GEMINI_API_KEY", "gemini-2.5-flash"),
    }
    preferred = os.getenv("AICOS_LLM_PROVIDER", "").strip().lower()
    order = [preferred] if preferred in configurations else []
    order.extend(name for name in ("anthropic", "openai", "deepseek", "gemini") if name not in order)
    for name in order:
        provider, env_name, default_model = configurations[name]
        api_key = os.getenv(env_name, "").strip()
        if not api_key and name == "gemini":
            api_key = os.getenv("GOOGLE_API_KEY", "").strip()
        if api_key:
            model = os.getenv("AICOS_LLM_MODEL", "").strip() or default_model
            return provider, api_key, model
    return None


def _call_existing_provider_router(
    provider: str,
    api_key: str,
    model: str,
    system_prompt: str,
    message: str,
) -> str:
    core_root = Path(__file__).resolve().parents[2] / "buildway-ai-core"
    core_root_text = str(core_root)
    if core_root_text not in sys.path:
        sys.path.insert(0, core_root_text)
    from core.agents.provider_router import call_ai_reply

    result = call_ai_reply(
        provider=provider,
        message=message,
        api_key=api_key,
        model=model,
        system_prompt=system_prompt,
    )
    return str(result.content or "").strip()


def _system_prompt(question_type: str, answer_mode: str = DEFAULT_ANSWER_MODE) -> str:
    mode = normalize_answer_mode(answer_mode)
    sections = "、".join(ANSWER_MODE_SECTIONS[mode])
    caution = (
        " 對安全或法例問題，須提醒用戶在合規決定前查閱香港官方最新版本並由合資格人士覆核；不可聲稱提供正式法律意見。"
        if question_type in SAFETY_TYPES
        else ""
    )
    simple_rule = (
        " 回答核心內容以 5 至 8 個短項目為上限，不要長段落。"
        if mode == "site_simple"
        else ""
    )
    return (
        "你是香港建造業現場助理 AICOS。使用平實繁體中文，像實務管工／安全助理般先講現場做法，"
        "不要以長篇法例文字開場，不要貼出大段法律原文。"
        f"回答模式為「{ANSWER_MODE_LABELS[mode]}」，最終畫面會使用以下結構：{sections}。"
        "只可使用所提供內容，不得聲稱已搜尋未提供的網頁或文件。"
        "如資料提供具體章、節、條、段或頁碼，可簡短引用；未提供時必須明言未能確認，不可創作編號。"
        "不得使用「即時行動」作標題，一律使用「建議」。"
        + caution
        + simple_rule
        + " 只輸出 JSON object，包含 answer、practical_recommendations、risk_level、source_ids、"
        "followup_actions、confidence。source_ids 只可選用所提供資料內的 source_id。"
        "answer 只寫簡潔結論，不要自行加入來源 ID 或長引文；risk_level 使用 low/medium/high/critical/unknown。"
    )


def _user_message(
    question: str,
    question_type: str,
    search_scope: str,
    contexts: list[Any],
    answer_mode: str = DEFAULT_ANSWER_MODE,
) -> str:
    context_text = _format_contexts(contexts, question)
    return (
        f"問題類型：{question_type}\n搜尋範圍：{search_scope}\n回答模式：{normalize_answer_mode(answer_mode)}\n"
        f"問題：{question}\n\n可用資料（可能為空）：\n{context_text or '[沒有可用搜尋結果]'}"
    )


def _parse_provider_answer(
    raw: str,
    question_type: str,
    search_scope: str,
    contexts: list[Any],
    model: str,
    answer_mode: str = DEFAULT_ANSWER_MODE,
    question: str = "",
) -> QAResponse:
    match = re.search(r"\{.*\}", re.sub(r"```(?:json)?|```", "", raw), re.DOTALL)
    parsed: dict[str, Any] = {}
    if match:
        try:
            candidate = json.loads(match.group(0))
            parsed = candidate if isinstance(candidate, dict) else {}
        except json.JSONDecodeError:
            parsed = {}

    requested_ids = set(_string_list(parsed.get("source_ids"))) if parsed else set()
    sources = _context_citations(contexts, requested_ids)
    recommendations = _string_list(parsed.get("practical_recommendations")) or _recommendations(question_type, question)
    followups = _string_list(parsed.get("followup_actions")) or _fallback_actions(question_type)
    risk_level = _risk_level(parsed.get("risk_level")) if parsed else "unknown"
    base_answer = str(parsed.get("answer") or "未能產生答案。") if parsed else (raw or "AI 供應商沒有傳回內容。")
    structured_answer = _structured_answer(
        base_answer,
        question,
        question_type,
        answer_mode,
        risk_level,
        recommendations,
        followups,
        contexts,
    )
    return QAResponse(
        answer=structured_answer,
        practical_recommendations=recommendations,
        risk_level=risk_level,
        sources=sources,
        followup_actions=followups,
        confidence=_confidence(parsed.get("confidence"), 0.65 if parsed else 0.5),
        used_search_scope=search_scope,
        model_name=model,
        fallback_used=False,
    )


def _fallback_answer(
    question: str,
    question_type: str,
    search_scope: str,
    contexts: list[Any],
    answer_mode: str = DEFAULT_ANSWER_MODE,
) -> QAResponse:
    sources = _context_citations(contexts, {_source_id(contexts[0])} if contexts else set())
    risk_level = _infer_risk(question, question_type)
    recommendations = _recommendations(question_type, question)
    followups = _fallback_actions(question_type)
    base_answer = _fallback_conclusion(question, question_type, bool(contexts))
    answer = _structured_answer(
        base_answer,
        question,
        question_type,
        answer_mode,
        risk_level,
        recommendations,
        followups,
        contexts,
    )
    if not contexts:
        sources = [
            SourceCitation(
                source_id="fallback_local_rules",
                source_title="AICOS 本機後備規則",
                source_type="fallback_only",
                trust_level="fallback_only",
                snippet="沒有可引用的本機、已上載或網上來源。",
                used_in_answer=True,
                provider="local_rules",
            )
        ]
    return QAResponse(
        answer=answer,
        practical_recommendations=recommendations,
        risk_level=risk_level,
        sources=sources,
        followup_actions=followups,
        confidence=0.48 if contexts else 0.3,
        used_search_scope=search_scope,
        model_name="local-fallback",
        fallback_used=True,
    )


def _structured_answer(
    base_answer: str,
    question: str,
    question_type: str,
    answer_mode: str,
    risk_level: str,
    recommendations: list[str],
    followups: list[str],
    contexts: list[Any],
) -> str:
    mode = normalize_answer_mode(answer_mode)
    conclusion = _concise_text(base_answer, 320 if mode == "site_simple" else 800, 2 if mode == "site_simple" else 5)
    risk_summary = _risk_summary(question, question_type, risk_level)
    source_lines = _source_reference_lines(contexts, question, 1 if mode == "site_simple" else 3)
    compliance = _compliance_reminder(question_type, contexts)
    safe_recommendations = [_clean_item(item) for item in recommendations if _clean_item(item)]
    safe_followups = [_clean_item(item) for item in followups if _clean_item(item)]

    if mode == "foreman_followup":
        sections = (
            ("結論", [conclusion]),
            ("風險位置", [risk_summary]),
            ("建議", safe_recommendations[:4]),
            ("負責角色", [_responsible_role(question_type)]),
            ("跟進紀錄", ["記錄位置、工序、日期、照片、負責人、完成期限及整改結果。"]),
            ("來源摘要", source_lines),
        )
    elif mode == "safety_officer_detail":
        sections = (
            ("初步判斷", [conclusion]),
            ("主要風險", [risk_summary]),
            ("控制措施", safe_recommendations[:5]),
            ("檢查清單", (safe_followups + ["保存檢查、整改前後照片及通知紀錄。"] )[:4]),
            ("官方來源摘要", source_lines),
            ("合規提醒", [compliance]),
        )
    elif mode == "legal_source_detail":
        sections = (
            ("答案摘要", [conclusion]),
            ("相關官方來源", source_lines),
            ("主要要求", safe_recommendations[:5]),
            ("實務解讀", safe_followups[:4] or [risk_summary]),
            ("限制與免責", [compliance]),
        )
    else:
        attention = _attention_items(question, question_type, contexts, safe_followups)
        sections = (
            ("最簡單講", [conclusion]),
            ("現場判斷", [risk_summary]),
            ("建議", safe_recommendations[:3]),
            ("需要留意", attention[:1]),
            ("來源摘要", source_lines[:1]),
        )
    return _render_sections(sections)


def _render_sections(sections: Iterable[tuple[str, list[str]]]) -> str:
    blocks = []
    for heading, items in sections:
        clean_items = [_clean_item(item) for item in items if _clean_item(item)]
        blocks.append(f"#### {heading}\n" + "\n".join(f"- {item}" for item in clean_items))
    return "\n\n".join(blocks).replace("即時行動", "建議")


def _fallback_conclusion(question: str, question_type: str, has_context: bool) -> str:
    if _is_working_at_height(question):
        return "本機後備判斷：不要只等到某個高度才處理；只要工作位置有墮下受傷風險，就應先設防墮措施。"
    if has_context:
        return "本機後備判斷：已找到相關資料，可先按現場風險採取保守措施，再由負責人核實。"
    if question_type in SAFETY_TYPES:
        return "本機後備判斷：目前沒有可引用搜尋結果；如有即時危險，應先停工、隔離範圍及通知負責人。"
    return "本機後備判斷：目前沒有可引用搜尋結果，請按現場實況、核准文件及負責人意見再作決定。"


def _recommendations(question_type: str, question: str = "") -> list[str]:
    if _is_working_at_height(question):
        return [
            "優先使用穩固工作平台，臨邊設合規護欄及踢腳板。",
            "如集體防護不足，使用合適安全帶、認可錨點或獨立救生繩，並安排救援方法。",
            "開工前由管工／安全主任檢查平台、通道、護欄、錨點及天氣情況。",
        ]
    common = ["記錄位置、日期、工序、照片及負責人。", "執行前核對核准圖則、施工方案及最新文件。"]
    specific = {
        "safety": "如有即時危險，先停工、隔離範圍並通知安全主任。",
        "law_regulation": "查閱香港法例電子版及相關政府部門最新守則或指引。",
        "construction_method": "先核對 method statement、檢查及測試計劃與施工次序。",
        "material": "核對認可材料清單、送貨文件、批次、儲存條件及檢測要求。",
        "document_search": "確認文件名稱、版本、日期及批准狀態。",
        "site_followup": "指定負責人、完成期限及整改前後證據。",
    }.get(question_type, "把問題拆成現況、風險、所需證據及下一步。")
    return [specific] + common


def _fallback_actions(question_type: str) -> list[str]:
    actions = ["由相關地盤專業人員覆核。", "補充現場證據後再次提問。"]
    if question_type in SAFETY_TYPES:
        actions.insert(0, "如存在即時風險，先採取安全控制措施。")
    return actions


def _risk_summary(question: str, question_type: str, risk_level: str) -> str:
    if _is_working_at_height(question):
        return "高空、臨邊或開口工作有墮下風險；高度不是唯一判斷，亦要看是否可能墮下受傷。"
    labels = {"critical": "極高", "high": "高", "medium": "中", "low": "低", "unknown": "未能確定"}
    if question_type == "safety":
        return f"初步屬{labels.get(risk_level, '未能確定')}風險；須按位置、工序、人員暴露及現有控制措施現場覆核。"
    return f"初步風險級別：{labels.get(risk_level, '未能確定')}；仍須核對現場及文件版本。"


def _attention_items(question: str, question_type: str, contexts: list[Any], followups: list[str]) -> list[str]:
    if question_type in SAFETY_TYPES:
        if any(citation_from_source(item).source_url for item in contexts):
            return ["合規決定前仍要核實香港官方文件最新版本及由安全主任／合資格人士確認。"]
        return ["本回答未有即時連線至香港官方網站核實；須由安全主任及官方最新文件覆核。"]
    return followups or ["資料不足時先補充現場照片、位置及文件版本。"]


def _source_reference_lines(contexts: list[Any], question: str, limit: int) -> list[str]:
    references = extract_source_references(contexts, question)
    official = [reference for reference in references if reference.trust_level == "official_hk"]
    trusted = [reference for reference in references if reference.trust_level == "trusted_industry"]
    selected = (official or trusted)[:limit]
    if not selected:
        return ["目前未能確認官方章節來源，請以官方文件及安全主任／合資格人士覆核為準。"]
    lines = [format_source_reference(reference) for reference in selected]
    if not official:
        lines[0] += "；目前未能確認香港官方章節來源，請再以官方文件覆核。"
    return lines[:limit]


def _compliance_reminder(question_type: str, contexts: list[Any]) -> str:
    if question_type in SAFETY_TYPES:
        has_official = any(citation_from_source(item).trust_level == "official_hk" for item in contexts)
        prefix = "已提供官方來源摘要，但" if has_official else "目前未能確認官方來源；"
        return prefix + "合規決定前仍須核對官方最新版本及由合資格人士確認；本回覆並非正式法律意見。"
    return "答案只按目前提供資料整理，執行前須核對核准文件及由相關負責人確認。"


def _responsible_role(question_type: str) -> str:
    return {
        "safety": "管工負責即時控制及通知；安全主任覆核措施；項目管理人員追蹤完成。",
        "law_regulation": "項目管理人員統籌，並由安全主任／相關合資格人士核實法規要求。",
        "material": "物料／品質負責人核對文件，管工確認現場使用及儲存。",
    }.get(question_type, "由管工指定負責人，相關專業人員覆核，項目管理人員追蹤。")


def _infer_risk(question: str, question_type: str) -> str:
    lowered = question.lower()
    critical_terms = ("死亡", "倒塌", "火警", "觸電", "墮下", "collapse", "fatal", "electrocution")
    high_terms = ("危險", "受傷", "高空", "停工", "unsafe", "hazard", "crack", "漏水", "防墮")
    if any(term in lowered for term in critical_terms):
        return "critical"
    if question_type == "safety" or any(term in lowered for term in high_terms):
        return "high"
    if question_type in {"law_regulation", "construction_method", "site_followup"}:
        return "medium"
    return "low"


def _format_contexts(contexts: list[Any], question: str = "") -> str:
    blocks = []
    for item in contexts:
        citation = citation_from_source(item)
        location = citation.source_path or citation.source_url
        reference = format_source_reference(extract_source_reference(citation, question))
        blocks.append(
            f"[{citation.source_id}] {citation.source_title} | trust={citation.trust_level} | {location}\n"
            f"reference_hint={reference}\n{citation.snippet[:700]}"
        )
    return "\n\n".join(blocks)


def _context_citations(contexts: list[Any], used_ids: set[str] | None = None) -> list[SourceCitation]:
    used_ids = used_ids or set()
    sources: list[SourceCitation] = []
    seen: set[str] = set()
    for item in contexts:
        citation = citation_from_source(item, used_in_answer=_source_id(item) in used_ids)
        if citation.source_id not in seen:
            sources.append(citation)
            seen.add(citation.source_id)
    return sources


def _is_working_at_height(question: str) -> bool:
    lowered = str(question or "").lower()
    return any(term in lowered for term in ("高空", "高處", "臨邊", "防墮", "墮下", "working at height", "fall prevention"))


def _concise_text(value: Any, max_chars: int, max_sentences: int) -> str:
    text = re.sub(r"(?m)^#{1,6}\s+.*$", "", str(value or ""))
    text = re.sub(r"(?m)^[-*]\s*", "", text)
    text = " ".join(text.replace("即時行動", "建議").split())
    sentences = [part.strip() for part in re.split(r"(?<=[。！？.!?])\s*", text) if part.strip()]
    concise = " ".join(sentences[:max_sentences]) if sentences else text
    return concise if len(concise) <= max_chars else concise[: max_chars - 1].rstrip() + "…"


def _clean_item(value: Any) -> str:
    return " ".join(str(value or "").replace("即時行動", "建議").split()).strip(" -•")


def _source_id(item: Any) -> str:
    return citation_from_source(item).source_id


def _string_list(value: Any) -> list[str]:
    return [_clean_item(item) for item in value if _clean_item(item)][:10] if isinstance(value, list) else []


def _confidence(value: Any, default: float) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


def _risk_level(value: Any) -> str:
    level = str(value or "unknown").strip().lower()
    return level if level in {"low", "medium", "high", "critical", "unknown"} else "unknown"
