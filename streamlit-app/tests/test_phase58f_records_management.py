from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]


def test_records_management_tabs_and_safe_status_update_remain_available():
    source = (APP_ROOT / "pages" / "11_Records.py").read_text(encoding="utf-8")
    assert '["地盤記錄", "AICOS 記憶", "跟進事項", "知識來源"]' in source
    assert "update_followup_status(" in source
    assert "更新本機知識索引" in source


def test_records_route_keeps_runtime_warning_and_rag_status():
    source = (APP_ROOT / "pages" / "11_Records.py").read_text(encoding="utf-8")
    assert "get_runtime_storage_status()" in source
    assert "RAG 片段" in source
