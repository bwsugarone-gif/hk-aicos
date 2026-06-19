import json
from pathlib import Path

from utils.evidence_models import RiskEvidenceTrace
from utils.followup_store import (
    generate_followups_from_risk_trace,
    list_followups,
    update_followup_status,
)
from utils.knowledge_pack_store import (
    build_or_refresh_knowledge_index,
    extract_reference_hints,
    scan_local_knowledge_sources,
)
from utils.knowledge_retriever import search_knowledge, summarize_knowledge_hits
from utils.project_memory_store import (
    append_memory,
    link_memory_records,
    read_all_memory,
    search_memory,
    summarize_project_memory,
    update_memory_status,
)


APP_ROOT = Path(__file__).resolve().parents[1]


def _memory_payload(title: str, **overrides):
    payload = {
        "project_ref": "BW-001",
        "source_type": "upload_analysis",
        "title": title,
        "summary": "磨機切割產生火花，需覆核防火措施。",
        "risk_level": "high",
        "evidence_sources": ["使用者補充描述"],
        "tags": ["熱工", "火花"],
        "trade_tags": ["切割／打磨"],
        "status": "open",
        "priority": "high",
    }
    payload.update(overrides)
    return payload


def test_memory_append_read_search_filters_and_corrupt_line(tmp_path):
    path = tmp_path / "memory.jsonl"
    first = append_memory(_memory_payload("門框磨機火花"), path=path)
    append_memory(_memory_payload("另一工程", project_ref="BW-002", status="resolved"), path=path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write("{broken json\n")

    assert len(read_all_memory(path=path)) == 2
    hits = search_memory("磨機 火花", project_ref="BW-001", tags=["熱工"], status="open", path=path)
    assert [item.memory_id for item in hits] == [first.memory_id]
    assert search_memory("火花", project_ref="BW-999", path=path) == []
    natural_hits = search_memory("上次磨機火花問題跟進咗未？", project_ref="BW-001", path=path)
    assert natural_hits and natural_hits[0].memory_id == first.memory_id


def test_memory_missing_file_summary_update_link_and_secret_sanitizing(tmp_path):
    path = tmp_path / "missing" / "memory.jsonl"
    assert read_all_memory(path=path) == []
    first = append_memory(_memory_payload("熱工 1", metadata={"API_KEY": "secret", "note": "ok"}, raw_question="API_KEY=should-not-store"), path=path)
    second = append_memory(_memory_payload("熱工 2"), path=path)
    updated = update_memory_status(first.memory_id, "in_progress", "已指定安全主任", path=path)
    linked_first, linked_second = link_memory_records(first.memory_id, second.memory_id, path=path)
    summary = summarize_project_memory("BW-001", path=path)

    assert updated.status == "in_progress"
    assert second.memory_id in linked_first.linked_record_ids
    assert first.memory_id in linked_second.linked_record_ids
    assert summary.total_records == 2
    assert summary.open_count == 2
    assert summary.high_risk_count == 2
    assert ("熱工", 2) in summary.repeated_tags
    stored = next(item for item in read_all_memory(path=path) if item.memory_id == first.memory_id)
    assert "API_KEY" not in stored.metadata
    assert stored.raw_question == "[敏感資料已移除]"


def test_knowledge_scan_missing_folder_and_search_index(tmp_path):
    assert scan_local_knowledge_sources([tmp_path / "does-not-exist"]) == []
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()
    (knowledge_dir / "hot_work.md").write_text(
        "# 熱工安全指引\n來源 labour.gov.hk\nSection 5.3 要求防火氈及滅火筒。",
        encoding="utf-8",
    )
    (knowledge_dir / "drawing.pdf").write_bytes(b"metadata only")
    index_path = tmp_path / "knowledge_index.jsonl"
    indexed = build_or_refresh_knowledge_index([knowledge_dir], index_path=index_path)
    hits = search_knowledge("熱工 滅火筒", trust_filter=["official"], index_path=index_path)
    summary = summarize_knowledge_hits(indexed)

    assert len(indexed) == 2
    assert hits and hits[0].trust_level == "official"
    assert summary["trust_counts"]["official"] >= 1
    assert any("Section 5.3" in ref for ref in hits[0].extracted_refs)


def test_reference_hint_extraction_is_deterministic():
    refs = extract_reference_hints("Chapter 2 Section 5.3 clause 8.1 page 14 Section 5.3")
    assert any("Chapter 2" in item for item in refs)
    assert any("Section 5.3" in item for item in refs)
    assert any("clause 8.1" in item for item in refs)
    assert any("page 14" in item for item in refs)
    assert len(refs) == len(set(refs))


def test_high_risk_trace_creates_open_hot_work_followup_and_updates(tmp_path):
    path = tmp_path / "followups.jsonl"
    trace = RiskEvidenceTrace(
        risk_level="high",
        triggered_by=["使用者補充：磨機、火花"],
        rules_matched=["切割／打磨", "熱工／火花"],
        missing_confirmations=["滅火筒", "防火氈", "熱工許可"],
        final_reason="暫列為高風險。",
    )
    item = generate_followups_from_risk_trace(trace, "BW-001", path=path)[0]
    assert item.status == "open"
    assert item.priority == "high"
    assert "磨機切割" in item.title
    assert "熱工許可" in item.evidence_required
    updated = update_followup_status(item.followup_id, "resolved", "已上載巡查記錄", path=path)
    assert updated.status == "resolved"
    assert list_followups(project_ref="BW-001", status="resolved", path=path)[0].followup_id == item.followup_id


def test_insufficient_evidence_creates_manual_review_followup_without_specific_hazard(tmp_path):
    path = tmp_path / "followups.jsonl"
    trace = RiskEvidenceTrace(
        risk_level="unknown",
        triggered_by=["目前未有足夠相片、描述或文件證據"],
        rules_matched=[],
        final_reason="暫不判斷具體危害；需人工覆核。",
    )
    item = generate_followups_from_risk_trace(trace, path=path)[0]
    assert item.title == "需補充資料 / 人工覆核"
    encoded = json.dumps(item.to_dict(), ensure_ascii=False)
    for unsupported in ("棚架", "氣樽", "安全帶"):
        assert unsupported not in encoded


def test_ask_and_workspace_have_memory_aware_contracts_and_six_section_formatter():
    ask = (APP_ROOT / "pages/10_Ask_AICOS.py").read_text(encoding="utf-8")
    workspace = (APP_ROOT / "pages/0_AICOS_Workspace.py").read_text(encoding="utf-8")
    bridge = (APP_ROOT / "utils/ask_context_bridge.py").read_text(encoding="utf-8")
    formatter = (APP_ROOT / "utils/answer_formatter.py").read_text(encoding="utf-8")
    for source in (ask, workspace):
        assert "build_ask_context_selection(" in source
        assert "retrieval_counts" in source
        assert "append_memory(" in source
    assert "build_project_memory_context(" in bridge
    assert "build_followup_context(" in bridge
    assert "build_knowledge_pack_context(" in bridge
    for heading in ("最簡單講", "判斷依據", "主要風險 / 影響", "建議", "需確認事項", "來源 / 限制"):
        assert heading in formatter
    for forbidden in ("ModuleNotFoundError", "Tavily 已連接", "Brave 已連接"):
        assert forbidden not in ask


def test_workspace_keeps_upload_and_adds_compact_memory_dashboard():
    source = (APP_ROOT / "pages/0_AICOS_Workspace.py").read_text(encoding="utf-8")
    assert "開始分析" in source
    assert "process_uploaded_file_for_analysis(" in source
    assert "今日 / 最近工程記憶" in source
    assert "未完成跟進" in source
    assert "重複風險提示" in source
    assert "知識來源狀態" in source
    assert "更新本機知識索引" in source
