"""Phase 5.11 UI wording / deployment sanity hotfix tests.

Guards against stale phase-specific empty-state wording leaking into the normal
user UI, confirms the Drawing Analysis route is reachable from navigation, and
keeps the shared footers free of user-facing phase labels.
"""

from __future__ import annotations

import py_compile
from pathlib import Path

from utils.navigation import PRIMARY_PAGES, SECONDARY_PAGES, navigation_labels
from utils.ui_components import PRODUCT_FOOTER


APP_ROOT = Path(__file__).resolve().parents[1]
PAGES_DIR = APP_ROOT / "pages"


def test_no_stale_phase_empty_state_in_ui():
    for page in PAGES_DIR.glob("*.py"):
        source = page.read_text(encoding="utf-8")
        assert "尚未有 Phase 5.8 工程記憶" not in source, page.name


def test_workspace_uses_neutral_empty_state_wording():
    workspace = (PAGES_DIR / "0_AICOS_Workspace.py").read_text(encoding="utf-8")
    assert "尚未有相關工程記憶。" in workspace
    assert "上載相片、圖紙或向 AICOS 提問後，記憶會顯示在這裡。" in workspace


def test_drawing_analysis_route_exists_and_compiles():
    drawing_page = PAGES_DIR / "12_Drawing_Analysis.py"
    assert drawing_page.exists()
    py_compile.compile(str(drawing_page), doraise=True)


def test_navigation_includes_drawing_analysis():
    registered = dict(PRIMARY_PAGES + SECONDARY_PAGES)
    assert registered.get("drawing") == "pages/12_Drawing_Analysis.py"
    assert navigation_labels("繁體中文")["drawing"] == "📐 圖紙分析"
    assert "Drawing Analysis" in navigation_labels("English")["drawing"]


def test_shared_footer_has_no_user_facing_phase_label():
    assert "Phase" not in PRODUCT_FOOTER
    app_source = (APP_ROOT / "app.py").read_text(encoding="utf-8")
    # The rendered home-page footer must not carry a stale phase label.
    assert "HK-AICOS Phase 5.7 |" not in app_source
