import py_compile
from pathlib import Path

from utils.navigation import PRIMARY_PAGES, SECONDARY_PAGES, navigation_labels
from utils.workspace_preview import NO_VISION_PREVIEW, build_recent_analysis_preview


APP_ROOT = Path(__file__).resolve().parents[1]


def test_sidebar_has_workspace_as_only_primary_daily_entry():
    primary_keys = [key for key, _ in PRIMARY_PAGES]
    assert primary_keys == ["workspace", "records", "report", "history", "dashboard", "risk", "actions"]
    assert "upload" not in primary_keys
    assert "ask" not in primary_keys
    assert PRIMARY_PAGES[0] == ("workspace", "pages/0_AICOS_Workspace.py")


def test_upload_and_ask_remain_in_more_tools_with_direct_routes():
    secondary = dict(SECONDARY_PAGES)
    assert secondary["upload"] == "pages/1_Upload.py"
    assert secondary["ask"] == "pages/10_Ask_AICOS.py"
    assert navigation_labels("繁體中文")["more"] == "更多工具"


def test_workspace_keeps_all_three_quick_links_and_full_report_link():
    source = (APP_ROOT / "pages" / "0_AICOS_Workspace.py").read_text(encoding="utf-8")
    assert 'st.page_link("pages/1_Upload.py", label="📤 上載分析"' in source
    assert 'st.page_link("pages/10_Ask_AICOS.py", label="💬 問 AICOS"' in source
    assert 'st.page_link("pages/11_Records.py", label="🗂️ 地盤記錄"' in source
    assert 'st.page_link("pages/2_Report.py", label="查看完整分析報告"' in source


def test_image_preview_is_bounded_to_two_items_per_section():
    data = {
        "file_name": "site.jpg",
        "analysis_display_name": "安全分析",
        "risk_level": "高風險",
        "image_analysis": {
            "image_category": "hot_work",
            "visual_confidence": 0.8,
            "visual_observations": [f"觀察 {index}" for index in range(5)],
            "risks": [f"風險 {index}" for index in range(5)],
            "recommended_followups": [
                {"action": f"建議 {index}", "responsible_role": "管工"}
                for index in range(5)
            ],
            "raw_metadata": {
                "evidence_context": {
                    "has_visual_analysis": True,
                    "visual_confidence": 0.8,
                }
            },
        },
    }
    preview = build_recent_analysis_preview(data)
    assert len(preview["observations"]) <= 2
    assert len(preview["recommendations"]) <= 2
    assert len(preview["confirmations"]) <= 2


def test_zero_visual_confidence_preview_hides_unsupported_raw_report_noise():
    data = {
        "file_name": "site.jpg",
        "risk_level": "高風險",
        "analysis_result": "PM 工程狀態 Delay Concern 高空工作 棚架 安全帶 " * 20,
        "image_analysis": {
            "image_category": "general_site_photo",
            "visual_confidence": 0.0,
            "raw_metadata": {
                "evidence_context": {
                    "has_visual_analysis": False,
                    "visual_confidence": 0.0,
                }
            },
        },
    }
    preview = build_recent_analysis_preview(data)
    flattened = " ".join(
        [*preview["observations"], *preview["recommendations"], *preview["confirmations"]]
    )
    assert preview["risk_level"] == "需人工覆核"
    assert preview["observations"] == [NO_VISION_PREVIEW]
    assert "PM" not in flattened
    assert "Delay" not in flattened
    assert "高空工作" not in flattened
    assert "棚架" not in flattened


def test_legacy_preview_filters_pm_delay_workflow_and_long_paragraphs():
    data = {
        "analysis_result": (
            "PM 工程狀態總結：內容。\n"
            "Delay Concern: high.\n"
            "Workflow Blockage details.\n"
            "相片記錄顯示門框附近需要現場覆核。\n"
            "建議安排管工跟進。"
        )
    }
    preview = build_recent_analysis_preview(data)
    flattened = " ".join([*preview["observations"], *preview["recommendations"], *preview["confirmations"]])
    assert "PM 工程" not in flattened
    assert "Delay Concern" not in flattened
    assert "Workflow" not in flattened
    assert "門框" in flattened


def test_ask_page_compiles_and_keeps_safe_answer_import():
    ask_page = APP_ROOT / "pages" / "10_Ask_AICOS.py"
    py_compile.compile(str(ask_page), doraise=True)
    source = ask_page.read_text(encoding="utf-8")
    assert "from utils.llm_answer_client import safe_answer_question" in source
