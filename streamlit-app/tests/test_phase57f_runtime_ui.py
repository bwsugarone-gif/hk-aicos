from pathlib import Path

from utils.agent_selection_state import (
    agent_checkbox_key,
    build_agent_checkbox_state,
    selected_agents_from_checkbox_state,
)
from utils.navigation import PRIMARY_PAGES, navigation_labels


def test_agent_checkbox_state_has_one_source_of_truth():
    order = ["pm", "safety", "engineering"]
    state = build_agent_checkbox_state(order, ["pm", "safety"])
    assert state == {
        agent_checkbox_key("pm"): True,
        agent_checkbox_key("safety"): True,
        agent_checkbox_key("engineering"): False,
    }
    state[agent_checkbox_key("pm")] = False
    state[agent_checkbox_key("engineering")] = True
    assert selected_agents_from_checkbox_state(order, state) == ["safety", "engineering"]


def test_primary_navigation_is_bilingual_and_keeps_required_routes():
    routes = dict(PRIMARY_PAGES)
    assert routes["upload"] == "pages/1_Upload.py"
    assert routes["ask"] == "pages/10_Ask_AICOS.py"
    assert routes["records"] == "pages/11_Records.py"
    assert navigation_labels("繁體中文")["ask"] == "💬 問 AICOS"
    assert navigation_labels("English")["upload"] == "📤 Upload Analysis"


def test_streamlit_default_navigation_is_disabled():
    config_path = Path(__file__).resolve().parents[2] / ".streamlit" / "config.toml"
    text = config_path.read_text(encoding="utf-8")
    assert "showSidebarNavigation = false" in text
