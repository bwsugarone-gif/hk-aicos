# -*- coding: utf-8 -*-
"""Verify that the generated PDF has the CJK font properly embedded."""
import re
import sys
from pathlib import Path

pdf_path = Path(__file__).parent / "reports" / "HK-AICOS-Report-FONT-TEST.pdf"
if not pdf_path.exists():
    print("ERROR: test PDF not found. Run gen_test_pdf.py first.")
    sys.exit(1)

data = pdf_path.read_bytes()

has_descriptor = b"/FontDescriptor" in data
has_fontfile   = b"/FontFile" in data or b"/FontFile2" in data or b"/FontFile3" in data
has_name       = b"NotoSansTC" in data
has_tounicode  = b"/ToUnicode" in data

print("PDF font embedding verification")
print("=" * 40)
print(f"  FontDescriptor  : {'YES' if has_descriptor else 'NO'}")
print(f"  FontFile embed  : {'YES' if has_fontfile   else 'NO'}")
print(f"  NotoSansTC name : {'YES' if has_name       else 'NO'}")
print(f"  ToUnicode map   : {'YES' if has_tounicode  else 'NO'}")
print(f"  PDF size        : {len(data):,} bytes")

font_names = re.findall(rb"/BaseFont\s*/(\S+)", data)
print()
print("BaseFont entries in PDF:")
for fn in sorted(set(font_names)):
    decoded = fn.decode("latin-1", errors="replace")
    print(f"  - {decoded}")

print()
if has_fontfile and has_name:
    print("RESULT: Font is EMBEDDED. Chinese should render on all platforms.")
elif has_name and not has_fontfile:
    print("RESULT: Font name present but FontFile not detected.")
    print("        This may still work if reportlab embedded it differently.")
    print("        Open the PDF on iPhone/Android to confirm.")
else:
    print("RESULT: WARNING — font embedding not confirmed. Check manually.")
