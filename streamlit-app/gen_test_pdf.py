# -*- coding: utf-8 -*-
"""
gen_test_pdf.py — generate a cross-platform Chinese test PDF.
Run from streamlit-app/:  python gen_test_pdf.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils.report_generator import generate_pdf_report, _font_registered, _font_path_used, FONT

print(f"Font registered : {_font_registered}")
print(f"Font name       : {FONT}")
print(f"Font path       : {_font_path_used}")

pdf = generate_pdf_report(
    analysis_type="安全風險分析",
    question="你好，繁體中文測試",
    risk_level="高風險",
    analysis_result=(
        "工程分析\n"
        "安全風險分析\n"
        "法規與合規提醒\n\n"
        "勞工處\n"
        "屋宇署\n"
        "消防處\n"
        "EMSD\n"
        "水務署\n"
        "渠務署"
    ),
    filename_hint="test.pdf",
    professionals_required=["認可人士 (AP)", "安全主任"],
    project_ref="BW-TEST-001",
    selected_agents=["safety", "engineering", "pm"],
    session_id="test-session-001",
)

out = Path(__file__).parent / "reports" / "test_chinese_mobile.pdf"
out.parent.mkdir(exist_ok=True)
out.write_bytes(pdf)
print(f"PDF generated   : {out}  ({len(pdf):,} bytes)")
