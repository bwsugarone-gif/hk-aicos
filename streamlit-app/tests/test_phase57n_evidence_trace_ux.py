from pathlib import Path

from utils.answer_formatter import format_answer_display
from utils.navigation import PRIMARY_PAGES, SECONDARY_PAGES, SIDEBAR_STYLE_CSS
from utils.risk_evidence import (
    build_analysis_basis,
    build_risk_evidence_trace,
    summarize_analysis_basis,
)
from utils.service_readiness import get_service_readiness


APP_ROOT = Path(__file__).resolve().parents[1]


def _source(relative: str) -> str:
    return (APP_ROOT / relative).read_text(encoding="utf-8")


def test_sidebar_uses_shared_dark_style_and_keeps_simplified_navigation():
    assert "#102a43" in SIDEBAR_STYLE_CSS
    assert "#0b2035" in SIDEBAR_STYLE_CSS
    assert 'a[aria-current="page"]' in SIDEBAR_STYLE_CSS
    assert PRIMARY_PAGES[0] == ("workspace", "pages/0_AICOS_Workspace.py")
    assert [key for key, _ in PRIMARY_PAGES] == [
        "workspace", "records", "report", "history", "dashboard", "risk", "actions"
    ]
    assert dict(SECONDARY_PAGES)["upload"] == "pages/1_Upload.py"
    assert dict(SECONDARY_PAGES)["ask"] == "pages/10_Ask_AICOS.py"


def test_workspace_has_prominent_upload_cta_and_safe_handoff():
    source = _source("pages/0_AICOS_Workspace.py")
    assert "上載相片 / 文件" in source
    assert "立即上載分析" in source
    assert "前往完整上載頁" in source
    assert "st.file_uploader(" in source
    assert 'type=["jpg", "jpeg", "png", "pdf", "docx", "xlsx"]' in source
    assert 'st.session_state["workspace_upload_handoff"]' in source
    assert 'st.switch_page("pages/1_Upload.py")' in source


def test_manual_grinder_sparks_trace_explains_high_risk_without_provider_names():
    trace = build_risk_evidence_trace(
        "high",
        manual_description="工人正用磨機切割門框，現場有火花。",
    )
    rendered = " ".join([
        *trace.triggered_by,
        *trace.evidence_sources,
        *trace.rules_matched,
        *trace.missing_confirmations,
        trace.confidence_reason,
        trace.final_reason,
    ])
    assert "使用者補充" in rendered
    assert "切割／打磨" in trace.rules_matched
    assert "熱工／火花" in trace.rules_matched
    assert "滅火筒" in trace.missing_confirmations
    assert "暫列為高風險" in trace.final_reason
    for provider in ("Gemini", "Anthropic", "Tavily", "Brave"):
        assert provider not in rendered


def test_insufficient_evidence_trace_does_not_invent_specific_hazards():
    trace = build_risk_evidence_trace("unknown")
    rendered = " ".join([
        *trace.triggered_by,
        *trace.rules_matched,
        *trace.missing_confirmations,
        trace.final_reason,
    ])
    assert "目前未有足夠" in rendered
    assert "暫不判斷具體危害" in rendered
    for unsupported in ("棚架", "氣樽", "安全帶", "高空工作"):
        assert unsupported not in rendered


def test_answer_formatter_has_reasoned_flow_and_removes_technical_names():
    trace = build_risk_evidence_trace(
        "high",
        manual_description="磨機切割產生火花",
    )
    basis = build_analysis_basis(
        manual_description="磨機切割產生火花",
        rules_matched=trace.rules_matched,
    )
    model = format_answer_display(
        """
        ## 最簡單講
        火花可能引燃附近物料。
        Gemini API used
        Anthropic failed
        Tavily provider error
        Brave unavailable
        ModuleNotFoundError: missing package
        API key missing
        ## 建議
        清走附近可燃物。
        """,
        risk_level="high",
        risk_trace=trace,
        analysis_basis=basis,
        source_available=False,
        fallback_used=True,
    )
    sections = {
        "最簡單講": model.summary_bullets,
        "判斷依據": model.judgement_basis_bullets,
        "主要風險 / 影響": model.risk_impact_bullets,
        "建議": model.recommendations_bullets,
        "需確認事項": model.confirmation_bullets,
        "來源 / 限制": model.source_limitations,
    }
    assert all(sections.values())
    visible = " ".join(item for values in sections.values() for item in values)
    for forbidden in (
        "ModuleNotFoundError", "API key", "Gemini", "Anthropic", "Tavily", "Brave", "即時行動"
    ):
        assert forbidden not in visible
    assert model.source_limitations == [
        "本次未能核實官方具體章節，請以最新官方文件及安全主任覆核為準。"
    ]


def test_analysis_basis_summarises_roles_without_api_clutter():
    basis = build_analysis_basis(
        ocr_text="Permit 123",
        manual_description="磨機工序",
        rules_matched=["切割／打磨"],
        sources=[{"source_type": "uploaded_record", "trust_level": "local_internal"}],
    )
    summary = summarize_analysis_basis(basis)
    assert "使用者補充描述" in summary
    assert "文字偵測／文件文字" in summary
    assert "未有 AI 視覺確認" in summary
    assert "地盤記憶／已上載記錄" in summary
    assert "公司 SOP／知識庫" in summary
    assert "未有官方來源章節" in summary
    assert any(item.startswith("AICOS 風險規則") for item in summary)


def test_core_pages_render_provider_neutral_evidence_trace():
    ask = _source("pages/10_Ask_AICOS.py")
    workspace = _source("pages/0_AICOS_Workspace.py")
    upload = _source("pages/1_Upload.py")
    report = _source("pages/2_Report.py")
    records = _source("pages/11_Records.py")
    for source in (ask, workspace, upload):
        assert "build_risk_evidence_trace(" in source
        assert "render_risk_evidence_trace(" in source
    assert "build_trace_from_analysis(" in report
    assert "render_risk_evidence_trace(" in report
    assert "build_risk_evidence_trace(" in records
    assert "render_risk_evidence_trace(" in records
    assert "Tavily 已連接" not in ask
    assert "Brave 已連接" not in ask
    assert "vision_status.get('provider')" not in upload


def test_service_readiness_accepts_streamlit_style_secrets_without_exposing_values(monkeypatch):
    for key in (
        "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY",
        "GEMINI_API_KEY", "GOOGLE_API_KEY", "TAVILY_API_KEY", "BRAVE_SEARCH_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    status = get_service_readiness({
        "DEEPSEEK_API_KEY": "configured-text",
        "GEMINI_API_KEY": "configured-vision",
        "TAVILY_API_KEY": "configured-search",
    })
    assert status == {"text_answer": True, "ai_vision": True, "web_search": True}
    assert all(isinstance(value, bool) for value in status.values())
