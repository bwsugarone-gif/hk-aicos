"""Phase 6.2 — Google Drive Service Account storage tests."""

from __future__ import annotations

import json

from utils.drive_config import load_drive_config
from utils.drive_storage import (
    FOLDER_DRAWINGS,
    FOLDER_KNOWLEDGE,
    FOLDER_PHOTOS,
    DriveStorage,
    DriveUploadResult,
    folder_for_file_type,
    storage_provider_label,
    upload_to_drive_if_configured,
)


_GOOD_SA = json.dumps({
    "type": "service_account",
    "client_email": "aicos@project.iam.gserviceaccount.com",
    "private_key": "-----BEGIN PRIVATE KEY-----\nSECRETKEYMATERIAL\n-----END PRIVATE KEY-----\n",
    "token_uri": "https://oauth2.googleapis.com/token",
})


def _enabled_config():
    return load_drive_config({
        "AICOS_DRIVE_ENABLED": "true",
        "AICOS_DRIVE_ROOT_FOLDER_ID": "ROOT_FOLDER",
        "GOOGLE_SERVICE_ACCOUNT_JSON": _GOOD_SA,
    })


class _FakeUploader:
    """Records folder/upload calls and returns deterministic ids."""

    def __init__(self, *, fail: bool = False):
        self.fail = fail
        self.folders: list[tuple[str, str]] = []
        self.uploads: list[dict] = []

    def ensure_folder(self, name, parent_id):
        if self.fail:
            raise RuntimeError("drive error with secret token sk-shouldnotleak")
        self.folders.append((name, parent_id))
        return f"folder::{name}"

    def upload_file(self, *, local_path, file_name, mime_type, parent_id):
        self.uploads.append({"file_name": file_name, "parent_id": parent_id})
        return "drive-file-123", "https://drive.google.com/file/d/drive-file-123/view"


def test_missing_secrets_returns_not_configured():
    config = load_drive_config({})
    assert config.enabled is False
    assert config.credentials_present is False
    result = upload_to_drive_if_configured(
        "/tmp/x.pdf", file_name="x.pdf", file_type="drawing_pdf", config=config
    )
    assert result.configured is False
    assert result.success is False
    assert result.provider == "local_runtime"
    assert result.warning == ""  # not-configured is benign, no warning


def test_malformed_service_account_json_does_not_crash():
    config = load_drive_config({
        "AICOS_DRIVE_ENABLED": "1",
        "AICOS_DRIVE_ROOT_FOLDER_ID": "ROOT",
        "GOOGLE_SERVICE_ACCOUNT_JSON": "{ this is not valid json",
    })
    assert config.enabled is False
    assert config.credentials_present is False
    # Public status must not contain any of the (absent) secret material.
    assert "private_key" not in json.dumps(config.public_status())


def test_folder_routing_maps_file_types():
    assert folder_for_file_type("drawing_pdf") == FOLDER_DRAWINGS
    assert folder_for_file_type("drawing_image") == FOLDER_DRAWINGS
    assert folder_for_file_type("knowledge_pdf") == FOLDER_KNOWLEDGE
    assert folder_for_file_type("site_photo") == FOLDER_PHOTOS
    assert folder_for_file_type("report") == "Reports"
    assert folder_for_file_type(None, source_module="drawing_analysis") == FOLDER_DRAWINGS


def test_upload_failure_falls_back_to_local_runtime():
    storage = DriveStorage(uploader=_FakeUploader(fail=True), config=_enabled_config())
    result = storage.upload(
        "/tmp/plan.pdf", file_name="plan.pdf", file_type="drawing_pdf", project_ref="BW-001"
    )
    assert result.success is False
    assert result.provider == "local_runtime"
    assert result.warning  # safe warning present
    # The safe warning must not leak the underlying error / secret token.
    assert "sk-" not in result.warning
    assert "Traceback" not in result.warning


def test_mocked_successful_upload_stores_drive_ids():
    uploader = _FakeUploader()
    storage = DriveStorage(uploader=uploader, config=_enabled_config())
    result = storage.upload(
        "/tmp/plan.pdf", file_name="plan.pdf", file_type="drawing_pdf", project_ref="BW-001"
    )
    assert result.success is True
    assert result.provider == "google_drive"
    assert result.drive_file_id == "drive-file-123"
    assert result.drive_web_url.startswith("https://drive.google.com/")
    assert result.folder == FOLDER_DRAWINGS
    # Folders routed under <project>/Drawings.
    assert ("BW-001", "ROOT_FOLDER") in uploader.folders
    assert (FOLDER_DRAWINGS, "folder::BW-001") in uploader.folders


def test_display_helper_does_not_expose_path_or_secrets():
    assert storage_provider_label("google_drive") == "Google Drive"
    assert storage_provider_label("local_runtime") == "本機暫存"
    assert storage_provider_label(None) == "本機暫存"
    result = DriveUploadResult(
        success=True, provider="google_drive",
        drive_file_id="id", drive_web_url="https://drive.google.com/x", folder="Drawings",
    )
    blob = json.dumps(result.to_public_dict(), ensure_ascii=False)
    assert "/tmp/" not in blob and "private_key" not in blob and "client_email" not in blob


def test_drawing_registration_calls_drive_through_mock(tmp_path):
    from utils.drawing_integration import register_drawing_source_file
    from utils.drawing_models import DrawingDocument

    document = DrawingDocument.from_dict({
        "document_id": "draw_drive_1",
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
        "project_ref": "BW-001",
        "source_file_name": "A-101.pdf",
        "disciplines": ["architecture"],
    })
    uploader = _FakeUploader()
    record = register_drawing_source_file(
        document,
        source_path=str(tmp_path / "A-101.pdf"),
        file_name="A-101.pdf",
        registry_path=tmp_path / "reg.jsonl",
        drive_uploader=uploader,
        drive_config=_enabled_config(),
    )
    assert record is not None
    assert record.storage_provider == "google_drive"
    assert record.drive_file_id == "drive-file-123"
    assert record.drive_web_url and record.drive_web_url.startswith("https://drive.google.com/")
    assert uploader.uploads and uploader.uploads[0]["file_name"] == "A-101.pdf"


def test_knowledge_registration_calls_drive_through_mock(tmp_path):
    from utils.knowledge_ingestion import ingest_document

    pdf = tmp_path / "guide.txt"
    pdf.write_text("Hot work permit required. Working at height. " * 8, encoding="utf-8")
    uploader = _FakeUploader()
    result = ingest_document(
        file_path=pdf,
        original_file_name="guide.txt",
        project_ref="BW-001",
        knowledge_path=tmp_path / "k.jsonl",
        rag_path=tmp_path / "r.jsonl",
        registry_path=tmp_path / "reg.jsonl",
        drive_uploader=uploader,
        drive_config=_enabled_config(),
    )
    assert not result.metadata_only
    from utils.file_registry import list_file_records

    files = list_file_records(path=tmp_path / "reg.jsonl")
    assert files and files[0].storage_provider == "google_drive"
    assert files[0].drive_file_id == "drive-file-123"
    assert files[0].linked_knowledge_source_id == result.source_id


def test_registration_without_drive_stays_local(tmp_path):
    from utils.drawing_integration import register_drawing_source_file
    from utils.drawing_models import DrawingDocument

    document = DrawingDocument.from_dict({
        "document_id": "draw_local_1",
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
        "project_ref": "BW-001",
        "source_file_name": "A-102.pdf",
    })
    record = register_drawing_source_file(
        document,
        source_path=str(tmp_path / "A-102.pdf"),
        file_name="A-102.pdf",
        registry_path=tmp_path / "reg.jsonl",
        drive_config=load_drive_config({}),  # not enabled
    )
    assert record is not None
    assert record.storage_provider == "local_runtime"
    assert record.drive_file_id is None
