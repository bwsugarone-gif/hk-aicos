from pathlib import Path

from utils import llm_answer_client
from utils.analysis_models import QAResponse
from utils.llm_answer_client import safe_answer_question
from utils.navigation import PRIMARY_PAGES


def test_app_root_redirects_to_workspace_before_old_home_content():
    app_root = Path(__file__).resolve().parents[1]
    source = (app_root / "app.py").read_text(encoding="utf-8")
    redirect = 'st.switch_page("pages/0_AICOS_Workspace.py")'
    assert redirect in source
    assert source.index(redirect) < source.index("# ── Primary workflows")
    assert PRIMARY_PAGES[0] == ("workspace", "pages/0_AICOS_Workspace.py")


def test_safe_answer_flow_calls_current_supported_signature(monkeypatch):
    captured = {}

    def fake_answer_question(*, question, question_type, search_scope, context_snippets, answer_mode):
        captured.update(
            question=question,
            question_type=question_type,
            search_scope=search_scope,
            context_snippets=context_snippets,
            answer_mode=answer_mode,
        )
        return QAResponse(answer="ok", fallback_used=False)

    monkeypatch.setattr(llm_answer_client, "answer_question", fake_answer_question)
    response, recovered = safe_answer_question(
        question="怎樣才算是高空工作",
        question_type="safety",
        search_scope="all",
        context_snippets=[],
        answer_mode="site_simple",
    )

    assert response.answer == "ok"
    assert recovered is False
    assert captured == {
        "question": "怎樣才算是高空工作",
        "question_type": "safety",
        "search_scope": "all",
        "context_snippets": [],
        "answer_mode": "site_simple",
    }


def test_workspace_working_at_height_question_is_practical_and_does_not_crash(monkeypatch):
    for key in (
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "DEEPSEEK_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)

    response, recovered = safe_answer_question(
        question="怎樣才算是高空工作",
        question_type="safety",
        search_scope="all",
        context_snippets=[],
        answer_mode="site_simple",
    )

    assert recovered is False
    assert "#### 建議" in response.answer
    assert "即時行動" not in response.answer
    assert "高空" in response.answer
    assert "本次未能核實官方具體章節，請以最新官方文件及安全主任覆核為準。" in response.answer
    assert len(response.answer) < 1200


def test_safe_answer_flow_recovers_from_type_error_without_raw_exception(monkeypatch):
    def fail_answer_question(**_kwargs):
        raise TypeError("provider-secret-or-signature-detail")

    monkeypatch.setattr(llm_answer_client, "answer_question", fail_answer_question)
    response, recovered = safe_answer_question(
        question="怎樣才算是高空工作",
        question_type="safety",
        search_scope="all",
        context_snippets=[object()],
        answer_mode="site_simple",
    )

    assert recovered is True
    assert response.fallback_used is True
    assert "provider-secret-or-signature-detail" not in response.answer
    assert "#### 建議" in response.answer


def test_workspace_uses_shared_safe_answer_flow_with_keyword_arguments():
    app_root = Path(__file__).resolve().parents[1]
    workspace = (app_root / "pages" / "0_AICOS_Workspace.py").read_text(encoding="utf-8")
    ask_page = (app_root / "pages" / "10_Ask_AICOS.py").read_text(encoding="utf-8")

    for source in (workspace, ask_page):
        assert "safe_answer_question(" in source
        assert "question=" in source
        assert "question_type=" in source
        assert "search_scope=" in source
        assert "context_snippets=" in source
        assert "answer_mode=" in source
