"""Test session_memory.py — Phase 2.5E"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from utils.session_memory import (
    save_session, get_all_sessions, get_sessions_by_project,
    get_prior_context, clear_all_sessions,
)

# Clean slate
clear_all_sessions()
assert get_all_sessions() == [], "Expected empty after clear"

# Save sessions for BW-001
sid1 = save_session(
    project_ref="BW-001",
    file_names=["plan.pdf", "photo.jpg"],
    file_types=["pdf", "image"],
    selected_agents=["pm", "safety"],
    risk_level="高風險",
    departments=["勞工處", "屋宇署"],
    analysis_result="工地存在高空墮物風險，需立即加設防護網。" * 10,
    analysis_type="安全風險分析",
    question="呢個工地有無安全問題？",
)
sid2 = save_session(
    project_ref="BW-001",
    file_names=["report.docx"],
    file_types=["docx"],
    selected_agents=["qs", "pm"],
    risk_level="中風險",
    departments=["屋宇署"],
    analysis_result="合約條款需要更新，VO 尚未批核。" * 5,
    analysis_type="合約分析",
    question="VO 有無問題？",
)
# Different project
sid3 = save_session(
    project_ref="TKO-P2",
    file_names=["drawing.xlsx"],
    file_types=["xlsx"],
    selected_agents=["engineering"],
    risk_level="低風險",
    departments=["路政署"],
    analysis_result="圖則符合要求。",
    analysis_type="圖則審查",
    question="圖則有無問題？",
)

all_s = get_all_sessions()
bw_s  = get_sessions_by_project("BW-001")
prior = get_prior_context("BW-001")

print(f"Total sessions: {len(all_s)}")
print(f"BW-001 sessions: {len(bw_s)}")
print(f"Session IDs: {[s['session_id'] for s in all_s]}")
print()
print("Prior context preview (first 400 chars):")
print(prior[:400])
print()

# Assertions
assert len(all_s) == 3, f"Expected 3 total, got {len(all_s)}"
assert len(bw_s) == 2, f"Expected 2 for BW-001, got {len(bw_s)}"
assert "BW-001" in prior, "Prior context should mention BW-001"
assert "安全風險分析" in prior, "Prior context should include analysis type"

# No-crash on missing project
empty = get_prior_context("NONEXISTENT")
assert empty == "", f"Expected empty string, got: {repr(empty)}"

# No-crash on empty project ref
empty2 = get_prior_context("")
assert empty2 == "", "Empty project_ref should return empty string"

# Test per-project cap (5 max)
clear_all_sessions()
for i in range(7):
    save_session(
        project_ref="CAP-TEST",
        file_names=[f"file{i}.pdf"],
        file_types=["pdf"],
        selected_agents=["pm"],
        risk_level="低風險",
        departments=[],
        analysis_result=f"Analysis {i}",
        analysis_type="測試",
        question=f"Question {i}",
    )
cap_sessions = get_sessions_by_project("CAP-TEST")
assert len(cap_sessions) <= 5, f"Per-project cap exceeded: {len(cap_sessions)}"
print(f"Per-project cap test: {len(cap_sessions)} sessions (max 5) ✓")

# Test PDF generation with session_id
from utils.report_generator import generate_pdf_report
pdf = generate_pdf_report(
    analysis_type="安全風險分析",
    question="測試問題",
    risk_level="中風險",
    analysis_result="測試分析結果。工地安全需要注意。",
    filename_hint="test.pdf",
    project_ref="BW-001",
    selected_agents=["pm", "safety"],
    session_id="SES-TEST-0001",
)
assert len(pdf) > 1000, "PDF too small"
# PDF metadata (subject/keywords) may be XRef-compressed; check via pypdf instead
try:
    import io as _io
    from pypdf import PdfReader
    reader = PdfReader(_io.BytesIO(pdf))
    meta = reader.metadata or {}
    meta_str = " ".join(str(v) for v in meta.values())
    assert "BW-001" in meta_str or "SES-TEST-0001" in meta_str, (
        f"project_ref/session_id not found in PDF metadata: {meta_str}"
    )
    print(f"PDF metadata check: subject={meta.get('/Subject','')!r} ✓")
except ImportError:
    # pypdf not available — just check PDF is non-empty
    pass
print(f"PDF generation with session_id: {len(pdf)} bytes ✓")

print()
print("ALL TESTS PASSED ✓")
