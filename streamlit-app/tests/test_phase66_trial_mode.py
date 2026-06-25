"""Phase 6.6 — client trial mode / demo project tests."""

from __future__ import annotations

from pathlib import Path

from utils.demo_project import (
    DEMO_DRAWING_DOC_ID,
    DEMO_FILE_ID,
    is_demo_seeded,
    seed_demo_data,
)
from utils.trial_mode import (
    FUTURE_HOOK_FIELDS,
    build_future_hooks,
    build_trial_checklist,
    trial_flow_cards,
    trial_warnings,
)

APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_ROOT.parent


def _demo_paths(tmp_path):
    return dict(
        memory_path=tmp_path / "mem.jsonl",
        followup_path=tmp_path / "fu.jsonl",
        drawing_path=tmp_path / "dr.jsonl",
        registry_path=tmp_path / "reg.jsonl",
        knowledge_path=tmp_path / "k.jsonl",
        rag_path=tmp_path / "r.jsonl",
    )


def test_trial_checklist_covers_required_items():
    keys = {item.key for item in build_trial_checklist()}
    assert {
        "photo_analysis",
        "drawing_analysis",
        "cad_bim_handoff",
        "knowledge_source",
        "records_searchable",
        "ask_can_reference",
    } <= keys


def test_trial_flow_cards_and_warnings():
    cards = trial_flow_cards()
    assert [c.order for c in cards] == ["A", "B", "C", "D", "E", "F", "G"]
    assert all(c.page.startswith("pages/") for c in cards)
    assert len(trial_warnings()) == 3
    assert any("Supabase" in w for w in trial_warnings())


def test_future_hook_fields_present():
    hooks = build_future_hooks(project_ref="AICOS-DEMO")
    assert set(FUTURE_HOOK_FIELDS) == set(hooks)
    assert hooks["trial_mode"] is True
    assert hooks["project_ref"] == "AICOS-DEMO"
    # Permission fields default to None (not enforced this phase).
    assert hooks["role_hint"] is None and hooks["team_id"] is None


def test_demo_seed_creates_deterministic_safe_records(tmp_path):
    paths = _demo_paths(tmp_path)
    result = seed_demo_data(**paths)
    assert result.already_seeded is False
    assert result.project_ref == "AICOS-DEMO"
    assert result.drawing_doc_id == DEMO_DRAWING_DOC_ID
    assert result.file_id == DEMO_FILE_ID
    assert result.created.get("memory") == 2
    assert result.created.get("handoff") == 1
    assert result.created.get("knowledge_source") == 1

    # Records carry the trial_mode marker (Phase 6.2 future hook).
    from utils.project_memory_store import read_all_memory

    memories = read_all_memory(path=paths["memory_path"])
    assert any((m.metadata or {}).get("trial_mode") is True for m in memories)
    assert all(m.project_ref == "AICOS-DEMO" for m in memories)


def test_demo_seed_does_not_auto_seed_repeatedly(tmp_path):
    paths = _demo_paths(tmp_path)
    assert is_demo_seeded(memory_path=paths["memory_path"]) is False
    seed_demo_data(**paths)
    assert is_demo_seeded(memory_path=paths["memory_path"]) is True
    second = seed_demo_data(**paths)
    assert second.already_seeded is True
    assert second.created == {}

    from utils.project_memory_store import read_all_memory
    from utils.drawing_store import read_all_drawing_documents

    assert len(read_all_memory(path=paths["memory_path"])) == 2
    assert len(read_all_drawing_documents(path=paths["drawing_path"])) == 1


def test_client_trial_guide_exists():
    assert (REPO_ROOT / "docs" / "CLIENT_TRIAL_GUIDE.md").exists()
    assert (REPO_ROOT / "docs" / "PHASE6_RELEASE_GATE.md").exists()
