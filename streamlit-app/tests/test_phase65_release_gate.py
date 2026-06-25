"""Phase 6.5 — release gate / readiness tests."""

from __future__ import annotations

import json
from pathlib import Path

from utils.release_gate import (
    CHECKED_SECRETS,
    SMOKE_TEST_FLOW,
    evaluate_release_gate,
)


APP_ROOT = Path(__file__).resolve().parents[1]


def test_release_gate_lists_expected_pages():
    report = evaluate_release_gate()
    labels = " ".join(c.label for c in report.checks)
    for page_label in ("AICOS 工作台", "上載分析", "問 AICOS", "記錄", "圖紙分析", "知識匯入"):
        assert page_label in labels
    # Page checks should all pass in a healthy tree.
    page_checks = [c for c in report.checks if c.key.startswith("page:")]
    assert len(page_checks) == 6
    assert all(c.status == "pass" for c in page_checks)


def test_release_gate_never_exposes_secret_values(monkeypatch):
    sentinel = "SENTINEL-SECRET-VALUE-123456"
    monkeypatch.setenv("GEMINI_API_KEY", sentinel)
    monkeypatch.setenv("TAVILY_API_KEY", sentinel)
    report = evaluate_release_gate()
    blob = json.dumps(report.to_dict(), ensure_ascii=False)
    assert sentinel not in blob
    # Configured status is a boolean, not the value.
    assert report.secret_status["GEMINI_API_KEY"] is True
    assert report.secret_status["TAVILY_API_KEY"] is True


def test_missing_secrets_show_unconfigured_not_error(monkeypatch):
    for name, _ in CHECKED_SECRETS:
        monkeypatch.delenv(name, raising=False)
    report = evaluate_release_gate()
    assert all(value is False for value in report.secret_status.values())
    # Unconfigured optional secrets surface as warnings, never as crashes.
    assert any("未設定" in w for w in report.warnings)


def test_readiness_score_is_deterministic():
    a = evaluate_release_gate()
    b = evaluate_release_gate()
    assert a.score == b.score
    assert isinstance(a.score, int) and 0 <= a.score <= 100
    # Healthy tree: all six pages + six modules present.
    assert a.score == 100
    assert a.ready is True
    assert list(a.smoke_test_flow) == list(SMOKE_TEST_FLOW)


def test_release_gate_reports_blocking_when_page_missing(tmp_path):
    # Empty app root -> pages/modules missing -> blocking issues, lower score.
    report = evaluate_release_gate(app_root=tmp_path)
    assert report.blocking_issues
    assert report.ready is False
    assert report.score < 100


def test_release_readiness_page_compiles():
    source = (APP_ROOT / "pages" / "14_Release_Readiness.py").read_text(encoding="utf-8")
    compile(source, "14_Release_Readiness.py", "exec")
    # Normal UI must not dump tracebacks or raw env.
    assert "st.exception(" not in source
    assert "traceback" not in source
