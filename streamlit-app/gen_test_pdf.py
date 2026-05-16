# -*- coding: utf-8 -*-
"""
Cross-platform Chinese PDF test generator.
Generates a test PDF with Traditional Chinese content to verify
font embedding works on Windows, Mac, iPhone, and Android.
"""

import sys
import os
from pathlib import Path

# Run from streamlit-app directory
os.chdir(Path(__file__).parent)
sys.path.insert(0, str(Path(__file__).parent))

from utils.report_generator import generate_pdf_report, save_report, FONT, _font_path_used, _font_registered

print("=" * 60)
print("HK-AICOS Cross-Platform PDF Font Test")
print("=" * 60)
print(f"Font registered : {_font_registered}")
print(f"Font name       : {FONT}")
print(f"Font path       : {_font_path_used or '(fallback)'}")
print("=" * 60)

test_analysis = """工程分析
你好，繁體中文測試。本報告測試跨平台 PDF 中文顯示。

安全風險分析
工地安全需符合勞工處規定。高空工作須配備安全帶及防墮設備。棚架搭建需由合資格人士監督。

法規與合規提醒
屋宇署：結構改動須事先申請批准。
消防處：走火通道不得阻塞，消防裝置須定期檢查。
EMSD：電力裝置須由持牌電工負責。
水務署：水管工程須符合水務設施條例。
渠務署：排水及污水渠工程須事先通知。
勞工處：工地安全計劃須由安全主任審批。"""

pdf_bytes = generate_pdf_report(
    analysis_type="跨平台中文字型測試",
    question="你好，繁體中文測試 — 工程分析、安全風險分析、法規與合規提醒",
    risk_level="中風險",
    analysis_result=test_analysis,
    filename_hint="cross_platform_test.pdf",
    project_ref="TEST-2026-001",
    selected_agents=["safety", "engineering", "hk_legal"],
    session_id="font-test-session",
)

out_path = save_report(pdf_bytes, "FONT-TEST")
print(f"PDF generated   : {out_path}")
print(f"PDF size        : {len(pdf_bytes):,} bytes")
print()

# Verify font is embedded in PDF
pdf_text = pdf_bytes[:4096].decode("latin-1", errors="replace")
if "NotoSansTC" in pdf_text or "NotoSansCJK" in pdf_text or "msjh" in pdf_text.lower() or "msyh" in pdf_text.lower():
    print("✅ Font name found in PDF header — font is embedded")
elif FONT == "Helvetica":
    print("⚠️  WARNING: Using Helvetica fallback — Chinese will NOT render on mobile")
    sys.exit(1)
else:
    print(f"ℹ️  Font '{FONT}' used — check PDF manually to confirm embedding")

print()
print("Cross-platform QA checklist:")
print("  [ ] Windows PDF Viewer — open:", out_path)
print("  [ ] Mac Preview")
print("  [ ] iPhone Files App")
print("  [ ] Android PDF Viewer")
print()
print("Test complete.")
