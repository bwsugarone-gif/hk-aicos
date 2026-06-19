import json
from pathlib import Path

from utils import ask_context_bridge
from utils.ask_context_bridge import build_ask_context_selection
from utils.ask_intent_router import classify_ask_intent
from utils.knowledge_models import KnowledgeSource
from utils.knowledge_retriever import search_knowledge
from utils.llm_answer_client import answer_question
from utils.query_expander import expand_safety_query
from utils.rag_indexer import index_text_source
from utils.rag_retriever import search_rag


APP_ROOT = Path(__file__).resolve().parents[1]
LLM_KEYS = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY")


def _empty_bridge_sources(monkeypatch):
    monkeypatch.setattr(ask_context_bridge, "search_local_knowledge", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(ask_context_bridge, "build_knowledge_pack_context", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(ask_context_bridge, "build_knowledge_context", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(ask_context_bridge, "build_rag_context", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(ask_context_bridge, "_latest_upload_memory", lambda *_args, **_kwargs: None)


def _recent_hot_work_analysis():
    return {
        "image_analysis": {
            "visual_observations": ["工人使用磨機切割", "現場可見火花"],
            "evidence_items": ["磨機", "火花"],
            "image_category": "cutting_grinding",
        }
    }


def test_hot_work_definition_intents():
    assert classify_ask_intent("熱工序定義？").intent_type == "safety_definition_question"
    assert classify_ask_intent("咩係熱工？").intent_type == "safety_definition_question"
    assert classify_ask_intent("熱工定義").intent_type == "safety_definition_question"


def test_hot_work_permit_and_process_are_sop_howto():
    assert classify_ask_intent("熱工許可要準備什麼？").intent_type == "sop_howto_question"
    assert classify_ask_intent("做熱工前要做咩？").intent_type == "sop_howto_question"
    assert classify_ask_intent("熱工流程").intent_type == "sop_howto_question"


def test_recent_grinder_sparks_keeps_recent_image_context(monkeypatch):
    _empty_bridge_sources(monkeypatch)
    selection = build_ask_context_selection(
        "剛才磨機火花要跟進什麼？",
        latest_analysis_result=_recent_hot_work_analysis(),
        search_scope="all",
    )
    assert selection.intent.intent_type in {"recent_image_question", "followup_question"}
    assert selection.recent_image_referenced is True
    assert any(item.source_type == "recent_image_analysis" for item in selection.contexts)


def test_plain_hot_work_term_does_not_use_recent_image(monkeypatch):
    _empty_bridge_sources(monkeypatch)
    selection = build_ask_context_selection(
        "熱工序",
        latest_analysis_result=_recent_hot_work_analysis(),
        search_scope="all",
    )
    assert selection.intent.intent_type == "general_safety_question"
    assert selection.recent_image_referenced is False
    assert all(item.source_type != "recent_image_analysis" for item in selection.contexts)


def test_hot_work_query_expansion_contains_required_terms():
    expanded = expand_safety_query("熱工序定義？")
    for term in ("熱工", "火花", "焊接", "切割", "打磨", "防火氈", "滅火筒"):
        assert term in expanded


def test_safety_query_expansion_keeps_hot_work_and_height_separate():
    hot = expand_safety_query("熱工序定義？")
    height = expand_safety_query("高空工作定義？")
    for unrelated in ("高處工作", "高空工作", "墮下", "工作平台", "護欄", "踢腳板", "安全帶"):
        assert unrelated not in hot
    for unrelated in ("熱工", "火花", "焊接", "切割", "防火氈", "滅火筒"):
        assert unrelated not in height


def test_hot_work_fallback_has_complete_definition_without_height_noise(monkeypatch):
    for key in LLM_KEYS:
        monkeypatch.delenv(key, raising=False)
    response = answer_question("熱工序定義？", "safety", "all", context_snippets=[])
    for required in ("明火", "火花", "焊接", "切割", "打磨", "熱工許可", "滅火筒", "防火氈", "工後巡查"):
        assert required in response.answer
    for forbidden in ("高空", "棚架", "臨邊"):
        assert forbidden not in response.answer
    assert "本次未能核實官方具體章節" in response.answer
    assert "AI 視覺" not in response.answer


def test_hot_work_ranking_prefers_hot_work_and_excludes_height_only_sources(tmp_path):
    rag_path = tmp_path / "rag.jsonl"
    index_text_source(
        "hot", "熱工許可及防火監察", "焊接切割及打磨前準備防火氈、滅火筒，完工後巡查。",
        {"source_type": "company_sop", "trust_level": "internal"}, index_path=rag_path,
    )
    index_text_source(
        "height", "棚架高處工作", "臨邊洞口應設工作平台、護欄及踢腳板。",
        {"source_type": "company_sop", "trust_level": "internal"}, index_path=rag_path,
    )
    hits = search_rag("熱工序定義？", index_path=rag_path)
    assert hits and hits[0].source_id == "hot"
    assert all(item.source_id != "height" for item in hits)

    knowledge_path = tmp_path / "knowledge.jsonl"
    sources = [
        KnowledgeSource("hot-k", "熱工安全", "company_sop", None, "internal", "HK", summary="火花、焊接、切割、防火氈及滅火筒。"),
        KnowledgeSource("height-k", "棚架安全", "company_sop", None, "internal", "HK", summary="高處臨邊洞口、護欄及踢腳板。"),
    ]
    knowledge_path.write_text("\n".join(json.dumps(item.to_dict(), ensure_ascii=False) for item in sources), encoding="utf-8")
    knowledge_hits = search_knowledge("熱工序定義？", index_path=knowledge_path)
    assert knowledge_hits and knowledge_hits[0].source_id == "hot-k"
    assert all(item.source_id != "height-k" for item in knowledge_hits)


def test_non_image_hot_work_definition_context_has_no_vision_wording(monkeypatch):
    _empty_bridge_sources(monkeypatch)
    selection = build_ask_context_selection(
        "熱工序定義？",
        latest_analysis_result=_recent_hot_work_analysis(),
        search_scope="all",
    )
    rendered = "\n".join(selection.context_basis)
    assert "問題類型：安全定義 / 知識查詢" in rendered
    assert "最近相片分析：未引用" in rendered
    assert "AI 視覺未設定" not in rendered
    assert "未有 AI 視覺確認" not in rendered
    assert "相片所見" not in rendered


def test_normal_ui_contract_has_no_provider_or_secret_noise(monkeypatch):
    _empty_bridge_sources(monkeypatch)
    selection = build_ask_context_selection("熱工序定義？", search_scope="all")
    rendered = json.dumps(selection.context_basis, ensure_ascii=False)
    for forbidden in ("Gemini", "DeepSeek", "Tavily", "Brave", "API key", "API_KEY", "Traceback"):
        assert forbidden not in rendered


def test_ask_pages_suppress_vision_basis_for_non_image_intents():
    ask = (APP_ROOT / "pages" / "10_Ask_AICOS.py").read_text(encoding="utf-8")
    workspace = (APP_ROOT / "pages" / "0_AICOS_Workspace.py").read_text(encoding="utf-8")
    for source in (ask, workspace):
        assert '"safety_definition_question", "legal_source_question", "sop_howto_question"' in source
        assert 'item != "未有 AI 視覺確認"' in source
