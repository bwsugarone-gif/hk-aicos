from pathlib import Path

from utils.answer_formatter import format_answer_display
from utils.navigation import PRIMARY_PAGES, SECONDARY_PAGES


APP_ROOT = Path(__file__).resolve().parents[1]
CORE_PAGES = (
    "pages/0_AICOS_Workspace.py",
    "pages/1_Upload.py",
    "pages/2_Report.py",
    "pages/10_Ask_AICOS.py",
    "pages/11_Records.py",
)


def _source(relative: str) -> str:
    return (APP_ROOT / relative).read_text(encoding="utf-8")


def test_core_pages_share_header_and_current_product_footer():
    for relative in CORE_PAGES:
        source = _source(relative)
        assert "page_header(" in source
        assert "render_product_footer()" in source
        assert "HK-AICOS Phase 2.0" not in source
    assert "HK-AICOS Phase 2.0" not in _source("app.py")


def test_photo_text_detection_copy_is_supporting_and_friendly():
    source = _source("pages/1_Upload.py")
    assert "文字偵測：" in source
    assert "未偵測到清晰文字；地盤相片主要會使用 AI 視覺或現場描述作分析。" in source
    assert "相片分析：靠 AI 視覺 + 你補充的工序描述。OCR 只會在相中有清晰文字時輔助。" in source
    assert "OCR 文字：" not in source
    assert "OCR 信心" not in source


def test_unavailable_vision_copy_and_evidence_gate_hide_numeric_scores():
    source = _source("pages/1_Upload.py")
    assert "AI 視覺：未設定" in source
    assert "已使用你提供的現場描述作分析依據。" in source
    assert "if _image_manual_review_only:" in source
    assert "_agent_scores = {}" in source
    assert "_detected_issues = []" in source
    assert "未有足夠證據評分" in source


def test_answer_formatter_removes_technical_failures_and_normalises_actions():
    model = format_answer_display(
        """
        ## 最簡單講
        先停止附近人員靠近火花。
        ModuleNotFoundError: No module named provider_sdk
        Provider error: Tavily unavailable
        ## 即時行動
        清走附近可燃物。
        """,
        answer_mode="site_simple",
        source_available=False,
        fallback_used=True,
    )
    visible = " ".join(
        model.summary_bullets
        + model.site_judgement_bullets
        + model.recommendations_bullets
        + model.notes_bullets
        + model.source_summary
    )
    assert "ModuleNotFoundError" not in visible
    assert "Provider error" not in visible
    assert "即時行動" not in visible
    assert model.recommendations_bullets == ["清走附近可燃物。"]
    assert model.source_summary == ["本次沒有可核實官方來源；請由安全主任按最新指引覆核。"]
    assert "目前使用本機備用回答模式。建議仍須按現場情況及最新官方文件覆核。" in model.warning_labels


def test_ask_and_workspace_use_one_formatter_with_compact_workspace_output():
    ask = _source("pages/10_Ask_AICOS.py")
    workspace = _source("pages/0_AICOS_Workspace.py")
    for source in (ask, workspace):
        assert "from utils.answer_formatter import format_answer_display" in source
        assert "format_answer_display(" in source
        assert "render_answer_card(" in source
    assert "render_answer_card(display, compact=True)" in workspace


def test_phase57l_sidebar_grouping_remains_simplified():
    assert PRIMARY_PAGES[0] == ("workspace", "pages/0_AICOS_Workspace.py")
    assert "upload" not in dict(PRIMARY_PAGES)
    assert "ask" not in dict(PRIMARY_PAGES)
    assert dict(SECONDARY_PAGES)["upload"] == "pages/1_Upload.py"
    assert dict(SECONDARY_PAGES)["ask"] == "pages/10_Ask_AICOS.py"
