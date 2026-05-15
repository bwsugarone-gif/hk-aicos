"""Test font registration for PDF generation."""
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

results = {}

# Test msjh.ttc (Microsoft JhengHei - Traditional Chinese)
try:
    pdfmetrics.registerFont(TTFont("MSJH", "C:/Windows/Fonts/msjh.ttc", subfontIndex=0))
    results["msjh.ttc subfont 0"] = "OK"
except Exception as e:
    results["msjh.ttc subfont 0"] = f"ERROR: {e}"

# Test NotoSansTC-VF.ttf
try:
    pdfmetrics.registerFont(TTFont("NotoSansTC", "C:/Windows/Fonts/NotoSansTC-VF.ttf"))
    results["NotoSansTC-VF.ttf"] = "OK"
except Exception as e:
    results["NotoSansTC-VF.ttf"] = f"ERROR: {e}"

# Test mingliu.ttc
try:
    pdfmetrics.registerFont(TTFont("MingLiu", "C:/Windows/Fonts/mingliu.ttc", subfontIndex=0))
    results["mingliu.ttc subfont 0"] = "OK"
except Exception as e:
    results["mingliu.ttc subfont 0"] = f"ERROR: {e}"

# Test simsun.ttc
try:
    pdfmetrics.registerFont(TTFont("SimSun", "C:/Windows/Fonts/simsun.ttc", subfontIndex=0))
    results["simsun.ttc subfont 0"] = "OK"
except Exception as e:
    results["simsun.ttc subfont 0"] = f"ERROR: {e}"

for name, status in results.items():
    print(f"{name}: {status}")
