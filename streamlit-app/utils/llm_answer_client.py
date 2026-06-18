"""Structured construction Q&A client with local, transparent fallback answers."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable

from .analysis_models import KnowledgeSnippet, QAResponse, SearchResult, SourceCitation
from .official_sources import citation_from_source


SAFETY_TYPES = {"safety", "law_regulation"}


def answer_question(
    question: str,
    question_type: str,
    search_scope: str,
    context_snippets: Iterable[KnowledgeSnippet | SearchResult | dict[str, Any]] | None = None,
) -> QAResponse:
    """Answer through the existing core provider router when configured, else locally."""
    question = str(question or "").strip()
    # Ask AICOS supplies at most five local, five record, and five web items.
    # Keep all three groups available so web snippets cannot be truncated in
    # the "all" scope before the provider sees them.
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
        return _fallback_answer(question, question_type, search_scope, contexts)

    provider_name, api_key, model = provider
    system_prompt = _system_prompt(question_type)
    user_message = _user_message(question, question_type, search_scope, contexts)
    try:
        raw_answer = _call_existing_provider_router(provider_name, api_key, model, system_prompt, user_message)
        return _parse_provider_answer(raw_answer, question_type, search_scope, contexts, model)
    except Exception as exc:
        response = _fallback_answer(question, question_type, search_scope, contexts)
        response.model_name = f"local-fallback ({provider_name} error)"
        response.answer += f"\n\nAI 供應商暫時未能回應（{type(exc).__name__}），以上為本機後備結果。"
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


def _system_prompt(question_type: str) -> str:
    caution = (
        " 對安全或法例問題，必須提醒用戶由合資格人士核實，並查閱香港官方最新版本；不可聲稱提供正式法律意見。"
        if question_type in SAFETY_TYPES else ""
    )
    return (
        "你是香港建造業現場助理 AICOS。以繁體中文提供具體、可執行、保守的地盤建議，"
        "只可使用所提供的內容，不得聲稱已搜尋未提供的網頁或文件。"
        + caution
        + " 只輸出 JSON object，包含 answer、practical_recommendations、risk_level、source_ids、"
        "followup_actions、confidence。source_ids 只可選用提供資料內的 source_id，不可創作來源。"
        "risk_level 使用 low/medium/high/critical/unknown，confidence 為 0 至 1。"
    )


def _user_message(question: str, question_type: str, search_scope: str, contexts: list[Any]) -> str:
    context_text = _format_contexts(contexts)
    return (
        f"問題類型：{question_type}\n搜尋範圍：{search_scope}\n問題：{question}\n\n"
        f"可用資料（可能為空）：\n{context_text or '[沒有可用搜尋結果]'}"
    )


def _parse_provider_answer(
    raw: str,
    question_type: str,
    search_scope: str,
    contexts: list[Any],
    model: str,
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
    if parsed:
        return QAResponse(
            answer=str(parsed.get("answer") or "未能產生答案。"),
            practical_recommendations=_string_list(parsed.get("practical_recommendations")),
            risk_level=_risk_level(parsed.get("risk_level")),
            sources=sources,
            followup_actions=_string_list(parsed.get("followup_actions")),
            confidence=_confidence(parsed.get("confidence"), 0.65),
            used_search_scope=search_scope,
            model_name=model,
            fallback_used=False,
        )
    return QAResponse(
        answer=raw or "AI 供應商沒有傳回內容。",
        practical_recommendations=_recommendations(question_type),
        risk_level="unknown",
        sources=sources,
        followup_actions=["由地盤主管覆核答案後再執行。"],
        confidence=0.5,
        used_search_scope=search_scope,
        model_name=model,
        fallback_used=False,
    )


def _fallback_answer(question: str, question_type: str, search_scope: str, contexts: list[Any]) -> QAResponse:
    sources = _context_citations(contexts, {_source_id(contexts[0])} if contexts else set())
    context_preview = _first_context_preview(contexts)
    has_web_context = any(citation_from_source(item).source_url for item in contexts)
    if context_preview:
        answer = (
            "目前使用本機後備模式，未有調用外部 LLM。已找到相關本機／已提供資料，"
            f"可先作現場判斷參考：{context_preview}"
        )
        confidence = 0.48
    else:
        answer = (
            "目前使用本機後備模式，沒有可引用的搜尋結果，亦沒有聲稱已搜尋網頁或文件。"
            "請按現場實況、核准圖則、施工方案及最新官方要求再作判斷。"
        )
        confidence = 0.3
    if question_type in SAFETY_TYPES:
        if has_web_context:
            answer += " 已提供的網上搜尋資料仍須按香港官方最新版本及由合資格人士核實；本回覆並非正式法律意見。"
        else:
            answer += " 本回答未有即時連線至香港官方網站核實。安全及法例資料須向官方來源及合資格人士核實；本回覆並非正式法律意見。"
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
        practical_recommendations=_recommendations(question_type),
        risk_level=_infer_risk(question, question_type),
        sources=sources,
        followup_actions=_fallback_actions(question_type),
        confidence=confidence,
        used_search_scope=search_scope,
        model_name="local-fallback",
        fallback_used=True,
    )


def _recommendations(question_type: str) -> list[str]:
    common = ["記錄位置、日期、工序、照片及負責人。", "執行前由地盤主管核對核准圖則、施工方案及最新文件。"]
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


def _infer_risk(question: str, question_type: str) -> str:
    lowered = question.lower()
    critical_terms = ("死亡", "倒塌", "火警", "觸電", "墮下", "collapse", "fatal", "electrocution")
    high_terms = ("危險", "受傷", "高空", "停工", "unsafe", "hazard", "crack", "漏水")
    if any(term in lowered for term in critical_terms):
        return "critical"
    if question_type == "safety" or any(term in lowered for term in high_terms):
        return "high"
    if question_type in {"law_regulation", "construction_method", "site_followup"}:
        return "medium"
    return "low"


def _format_contexts(contexts: list[Any]) -> str:
    blocks = []
    for item in contexts:
        citation = citation_from_source(item)
        location = citation.source_path or citation.source_url
        blocks.append(
            f"[{citation.source_id}] {citation.source_title} | trust={citation.trust_level} | {location}\n"
            f"{citation.snippet[:1000]}"
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


def _first_context_preview(contexts: list[Any]) -> str:
    if not contexts:
        return ""
    data = _as_dict(contexts[0])
    snippet = " ".join(str(data.get("snippet") or data.get("content_summary") or "").split())
    return snippet[:350] + ("…" if len(snippet) > 350 else "")


def _as_dict(item: Any) -> dict[str, Any]:
    if isinstance(item, dict):
        return item
    if hasattr(item, "to_dict"):
        return item.to_dict()
    return {}


def _source_id(item: Any) -> str:
    return citation_from_source(item).source_id


def _string_list(value: Any) -> list[str]:
    return [str(item).strip() for item in value if str(item).strip()][:10] if isinstance(value, list) else []


def _confidence(value: Any, default: float) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


def _risk_level(value: Any) -> str:
    level = str(value or "unknown").strip().lower()
    return level if level in {"low", "medium", "high", "critical", "unknown"} else "unknown"
