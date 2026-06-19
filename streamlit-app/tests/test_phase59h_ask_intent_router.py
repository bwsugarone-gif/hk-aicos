import json
from pathlib import Path

from utils import ask_context_bridge
from utils.analysis_models import KnowledgeSnippet
from utils.ask_context_bridge import build_ask_context_selection
from utils.ask_intent_router import classify_ask_intent
from utils.llm_answer_client import answer_question
from utils.provider_health import get_provider_health


APP_ROOT = Path(__file__).resolve().parents[1]
LLM_KEYS = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY")


def _empty_bridge_sources(monkeypatch):
    monkeypatch.setattr(ask_context_bridge, "search_local_knowledge", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(ask_context_bridge, "build_knowledge_pack_context", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(ask_context_bridge, "build_knowledge_context", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(ask_context_bridge, "build_rag_context", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(ask_context_bridge, "_latest_upload_memory", lambda *_args, **_kwargs: None)


def _latest_grinder_analysis():
    return {
        "risk_level": "高風險",
        "image_analysis": {
            "visual_observations": ["工人使用磨機切割", "現場可見火花"],
            "evidence_items": ["磨機", "火花"],
            "image_category": "cutting_grinding",
        },
    }


def test_high_work_definition_intents_are_classified_correctly():
    assert classify_ask_intent("高空工作定義？").intent_type == "safety_definition_question"
    assert classify_ask_intent("高處工作定義").intent_type == "safety_definition_question"


def test_recent_image_question_is_classified_correctly():
    intent = classify_ask_intent("這張相有咩問題？")
    assert intent.intent_type == "recent_image_question"
    assert intent.use_recent_upload is True


def test_recent_grinder_followup_prefers_recent_image_context():
    intent = classify_ask_intent("剛才磨機火花要跟進什麼？")
    assert intent.intent_type in {"recent_image_question", "followup_question"}
    assert intent.use_recent_upload is True


def test_hot_work_permit_preparation_is_sop_howto():
    assert classify_ask_intent("熱工許可要準備什麼？").intent_type == "sop_howto_question"


def test_definition_question_excludes_latest_upload_analysis(monkeypatch):
    _empty_bridge_sources(monkeypatch)
    monkeypatch.setattr(
        ask_context_bridge,
        "build_knowledge_pack_context",
        lambda *_args, **_kwargs: [KnowledgeSnippet(
            title="高處工作安全指引", path="knowledge", snippet="高處工作定義及防墮要求",
            score=5.0, source_type="company_sop", source_id="knowledge:height",
            trust_level="local_internal", provider="local_knowledge",
        )],
    )

    selection = build_ask_context_selection(
        "高空工作定義？",
        latest_analysis_result=_latest_grinder_analysis(),
        search_scope="all",
    )

    assert selection.intent.intent_type == "safety_definition_question"
    assert selection.recent_image_referenced is False
    assert all(item.source_type != "recent_image_analysis" for item in selection.contexts)
    assert all("磨機" not in item.snippet and "火花" not in item.snippet for item in selection.contexts)


def test_recent_image_question_includes_latest_upload_analysis(monkeypatch):
    _empty_bridge_sources(monkeypatch)
    selection = build_ask_context_selection(
        "這張相有咩問題？",
        latest_analysis_result=_latest_grinder_analysis(),
        search_scope="all",
    )

    assert selection.recent_image_referenced is True
    recent = next(item for item in selection.contexts if item.source_type == "recent_image_analysis")
    assert "磨機" in recent.snippet
    assert selection.retrieval_counts["visual_evidence"] == 2


def test_high_work_definition_fallback_is_relevant_and_not_photo_driven(monkeypatch):
    for key in LLM_KEYS:
        monkeypatch.delenv(key, raising=False)
    response = answer_question(
        "高空工作定義？",
        "safety",
        "all",
        context_snippets=[],
    )

    assert "離地面不少於 2 米" in response.answer
    assert "少於 2 米" in response.answer
    assert "護欄" in response.answer
    assert "踢腳板" in response.answer
    assert "安全帶" in response.answer
    assert "本次未能核實官方具體章節" in response.answer
    lowered = response.answer.lower()
    for forbidden in ("磨機", "火花", "熱工", "grinder", "sparks", "hot work"):
        assert forbidden not in lowered


def test_definition_context_basis_says_recent_image_not_referenced(monkeypatch):
    _empty_bridge_sources(monkeypatch)
    selection = build_ask_context_selection(
        "高處工作定義",
        latest_analysis_result=_latest_grinder_analysis(),
        search_scope="all",
    )
    rendered = "\n".join(selection.context_basis)
    assert "問題類型：安全定義 / 知識查詢" in rendered
    assert "最近相片分析：未引用" in rendered
    assert "知識來源：" in rendered
    assert "RAG 片段：" in rendered
    assert "官方來源：" in rendered


def test_recent_image_context_basis_shows_visual_and_followup_counts(monkeypatch):
    _empty_bridge_sources(monkeypatch)
    selection = build_ask_context_selection(
        "剛才相片有咩風險？",
        latest_analysis_result=_latest_grinder_analysis(),
        search_scope="all",
    )
    rendered = "\n".join(selection.context_basis)
    assert "問題類型：最近相片跟進" in rendered
    assert "最近相片分析：已引用" in rendered
    assert "視覺證據：2 項" in rendered
    assert "未完成跟進：" in rendered


def test_normal_context_basis_and_ui_status_do_not_expose_technical_noise(monkeypatch):
    _empty_bridge_sources(monkeypatch)
    selection = build_ask_context_selection("高空工作定義？", search_scope="all")
    health = get_provider_health({})
    rendered = json.dumps({
        "basis": selection.context_basis,
        "message": health.user_message,
    }, ensure_ascii=False)
    for forbidden in ("Gemini", "DeepSeek", "Tavily", "Brave", "API key", "API_KEY", "Traceback"):
        assert forbidden not in rendered


def test_ask_and_workspace_use_shared_intent_aware_context_bridge():
    ask = (APP_ROOT / "pages" / "10_Ask_AICOS.py").read_text(encoding="utf-8")
    workspace = (APP_ROOT / "pages" / "0_AICOS_Workspace.py").read_text(encoding="utf-8")
    for source in (ask, workspace):
        assert "build_ask_context_selection(" in source
        assert '"context_basis"' in source
        assert '"intent_type"' in source
