from pathlib import Path

import pytest

from utils.analysis_models import SearchResult, SourceCitation
from utils.answer_modes import ANSWER_MODE_SECTIONS
from utils.llm_answer_client import _system_prompt, answer_question
from utils.source_reference_extractor import (
    extract_source_reference,
    format_source_reference,
    has_specific_reference,
)


def _clear_ai_keys(monkeypatch):
    for name in (
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "DEEPSEEK_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)


def test_extracts_specific_chinese_document_section_and_page():
    source = SourceCitation(
        source_id="labour_cop",
        source_title="竹棚架工作安全守則",
        source_url="https://labour.gov.hk/tc/public/pdf/os/B/Bamboo.pdf",
        trust_level="official_hk",
        snippet="勞工處《竹棚架工作安全守則》第 5.3 節說明工作平台要求，詳見第 18 頁。",
    )
    reference = extract_source_reference(source, "高空工作平台有甚麼防墮要求？")
    assert reference.document_title == "竹棚架工作安全守則"
    assert reference.section == "5.3"
    assert reference.page == "18"
    assert reference.reference_confidence == 0.95
    assert "勞工處《竹棚架工作安全守則》" in format_source_reference(reference)
    assert "第 5.3 節" in format_source_reference(reference)


def test_extracts_english_clause_and_page():
    source = {
        "source_id": "suspended_platform_cop",
        "source_title": "Code of Practice for Safe Use and Operation of Suspended Working Platforms",
        "source_url": "https://labour.gov.hk/example.pdf",
        "trust_level": "official_hk",
        "snippet": "Clause 5.6.1 requires inspection before use. See p. 42.",
    }
    reference = extract_source_reference(source, "suspended platform inspection")
    assert reference.clause == "5.6.1"
    assert reference.page == "42"
    assert has_specific_reference(reference) is True


def test_bare_reference_number_is_not_invented_or_promoted_from_title():
    source = {
        "source_id": "guide",
        "source_title": "Phase 5.7 Safety Guide",
        "source_url": "https://labour.gov.hk/guide",
        "trust_level": "official_hk",
        "snippet": "工作守則 5.3.2 提及護欄及踢腳板。",
    }
    reference = extract_source_reference(source, "護欄要求")
    assert reference.clause == "5.3.2"
    assert reference.section == ""


def test_reference_without_specific_location_says_unconfirmed():
    source = {
        "source_id": "general_height_guide",
        "source_title": "高處工作安全指引",
        "source_url": "https://labour.gov.hk/height-guide",
        "trust_level": "official_hk",
        "snippet": "應採取合適防墮措施。",
    }
    reference = extract_source_reference(source, "高空工作")
    assert has_specific_reference(reference) is False
    assert "未能確認具體章節" in format_source_reference(reference)


def test_multiple_clauses_prefers_question_relevant_context():
    source = {
        "source_id": "multi_clause",
        "source_title": "Safety Code of Practice",
        "source_url": "https://labour.gov.hk/safety-code",
        "trust_level": "official_hk",
        "snippet": "Clause 4.1 covers storage. " + ("其他一般內容 " * 30) + "Clause 5.6.1 covers 高空安全帶 and fall protection.",
    }
    reference = extract_source_reference(source, "高空工作安全帶如何使用？")
    assert reference.clause == "5.6.1"


def test_working_at_height_site_simple_is_practical_and_concise(monkeypatch):
    _clear_ai_keys(monkeypatch)
    source = SearchResult(
        title="竹棚架工作安全守則",
        url="https://labour.gov.hk/tc/public/pdf/os/B/Bamboo.pdf",
        snippet="《竹棚架工作安全守則》第 5.3 節要求提供合適工作平台。LONG_SOURCE_MARKER " + ("法律文字 " * 100),
        source="labour.gov.hk",
        source_id="labour_bamboo",
        trust_level="official_hk",
        provider="tavily",
    )
    response = answer_question(
        "香港地盤高空工作幾高需要設置防墮措施？",
        "safety",
        "web_search",
        [source],
        answer_mode="site_simple",
    )
    answer = response.answer
    assert answer.startswith("#### 最簡單講")
    assert "#### 現場判斷" in answer
    assert "#### 建議" in answer
    assert "#### 需要留意" in answer
    assert "#### 來源摘要" in answer
    assert "即時行動" not in answer
    assert "墮下" in answer
    assert "護欄" in answer
    assert "踢腳板" in answer
    assert "安全帶" in answer
    assert "第 5.3 節" in answer
    assert "LONG_SOURCE_MARKER" not in answer
    assert sum(line.startswith("- ") for line in answer.splitlines()) <= 8
    assert response.sources[0].source_id == "labour_bamboo"


def test_working_at_height_does_not_invent_unavailable_clause(monkeypatch):
    _clear_ai_keys(monkeypatch)
    source = SearchResult(
        title="高處工作安全指引",
        url="https://labour.gov.hk/height-guide",
        snippet="高處工作應使用合適工作平台及防墮設備。",
        source="labour.gov.hk",
        source_id="height_guide",
        trust_level="official_hk",
    )
    answer = answer_question(
        "香港地盤高空工作幾高需要設置防墮措施？",
        "safety",
        "web_search",
        [source],
        answer_mode="site_simple",
    ).answer
    assert "未能確認具體章節" in answer
    assert "第 5.3 節" not in answer


@pytest.mark.parametrize(
    ("mode", "expected_headings"),
    list(ANSWER_MODE_SECTIONS.items()),
)
def test_all_answer_modes_use_required_sections(monkeypatch, mode, expected_headings):
    _clear_ai_keys(monkeypatch)
    answer = answer_question("臨邊位置如何跟進？", "safety", "local_knowledge", [], answer_mode=mode).answer
    for heading in expected_headings:
        assert f"#### {heading}" in answer
    assert "即時行動" not in answer


def test_prompt_requires_plain_language_and_non_invented_references():
    prompt = _system_prompt("safety", "site_simple")
    assert "平實繁體中文" in prompt
    assert "不要以長篇法例文字開場" in prompt
    assert "不可創作編號" in prompt
    assert "一律使用「建議」" in prompt


def test_ask_aicos_ui_defaults_and_collapsed_source_contract():
    page_path = Path(__file__).resolve().parents[1] / "pages" / "10_Ask_AICOS.py"
    source = page_path.read_text(encoding="utf-8")
    assert 'with st.container(border=True):' in source
    assert 'index=list(SEARCH_SCOPES).index("all")' in source
    assert 'index=list(ANSWER_MODE_LABELS).index(DEFAULT_ANSWER_MODE)' in source
    assert '"回答模式"' in source
    assert '"查看完整來源摘錄：{title}"' in source
    assert 'st.markdown(response_data["answer"])' in source
