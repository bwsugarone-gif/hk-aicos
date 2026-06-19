from pathlib import Path

from utils import runtime_storage_health


APP_ROOT = Path(__file__).resolve().parents[1]


def test_records_page_has_four_management_tabs_and_required_controls():
    source = (APP_ROOT / "pages" / "11_Records.py").read_text(encoding="utf-8")
    assert '["地盤記錄", "AICOS 記憶", "跟進事項", "知識來源"]' in source
    for label in (
        "工程編號", "風險級別", "AICOS 記憶", "負責角色", "更新跟進事項",
        "更新本機知識索引", "更新 SOP / RAG 索引", "雲端知識庫：",
    ):
        assert label in source
    assert "update_followup_status(" in source
    assert "read_all_memory()" in source
    assert "read_knowledge_index()" in source


def test_runtime_storage_health_reports_local_writable_status(monkeypatch, tmp_path):
    monkeypatch.delenv("STREAMLIT_CLOUD", raising=False)
    monkeypatch.delenv("STREAMLIT_SHARING_MODE", raising=False)
    monkeypatch.setattr(runtime_storage_health, "DATA_DIR", tmp_path)
    monkeypatch.setattr(runtime_storage_health, "_runtime_mode", lambda: "local_desktop")

    status = runtime_storage_health.get_runtime_storage_status()

    assert status.mode == "local_desktop"
    assert status.writable is True
    assert status.persistent_likely is True
    assert status.warning_message == ""
    assert "aicos_memory.jsonl" in status.affected_files
    assert "site_records.jsonl" in status.affected_files


def test_runtime_storage_health_cloud_warning_is_honest(monkeypatch, tmp_path):
    monkeypatch.setattr(runtime_storage_health, "DATA_DIR", tmp_path)
    monkeypatch.setattr(runtime_storage_health, "_runtime_mode", lambda: "streamlit_cloud_like")

    status = runtime_storage_health.get_runtime_storage_status()

    assert status.persistent_likely is False
    assert status.warning_message == (
        "目前使用暫存本機記憶；重新部署後資料可能消失。正式多人使用應接 Google Drive 或 Supabase。"
    )
    assert status.to_dict()["mode"] == "streamlit_cloud_like"


def test_runtime_storage_health_handles_unwritable_or_missing_storage(monkeypatch, tmp_path):
    missing = tmp_path / "not-created"
    monkeypatch.setattr(runtime_storage_health, "DATA_DIR", missing)
    monkeypatch.setattr(runtime_storage_health, "_runtime_mode", lambda: "unknown")
    monkeypatch.setattr(runtime_storage_health, "_is_writable", lambda _path: False)

    status = runtime_storage_health.get_runtime_storage_status()

    assert status.writable is False
    assert status.persistent_likely is False
    assert status.warning_message


def test_workspace_shows_cloud_warning_without_normal_path_details():
    source = (APP_ROOT / "pages" / "0_AICOS_Workspace.py").read_text(encoding="utf-8")
    assert "get_runtime_storage_status()" in source
    assert "storage_health.warning_message" in source
    assert "storage_health.storage_path" not in source
