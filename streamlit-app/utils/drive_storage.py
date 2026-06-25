"""Google Drive Service Account storage adapter for AICOS (Phase 6.2 storage).

Uploads original uploaded files to a shared Drive folder using a service
account, organising them under ``<root>/<project>/<subfolder>`` where subfolder
is one of: Photos, Drawings, Knowledge, Reports, CAD-BIM Handoff.

Design notes:
* The actual Google API client is imported lazily inside the real uploader, so
  this module imports cleanly even when ``google-api-python-client`` is absent.
* A ``DriveUploader`` can be injected for testing — no network in tests.
* Any configuration / network / API failure degrades to ``local_runtime`` with a
  safe Traditional-Chinese warning. It never raises into the upload flow, and
  never exposes secrets, private keys, client emails, paths, JSON or tracebacks.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .drive_config import DriveConfig, load_drive_config


# file_type -> Drive subfolder name (English folder names, stable on Drive).
FOLDER_PHOTOS = "Photos"
FOLDER_DRAWINGS = "Drawings"
FOLDER_KNOWLEDGE = "Knowledge"
FOLDER_REPORTS = "Reports"
FOLDER_HANDOFF = "CAD-BIM Handoff"
PROJECT_SUBFOLDERS = (FOLDER_PHOTOS, FOLDER_DRAWINGS, FOLDER_KNOWLEDGE, FOLDER_REPORTS, FOLDER_HANDOFF)

_FILE_TYPE_FOLDER = {
    "site_photo": FOLDER_PHOTOS,
    "drawing_pdf": FOLDER_DRAWINGS,
    "drawing_image": FOLDER_DRAWINGS,
    "knowledge_pdf": FOLDER_KNOWLEDGE,
    "knowledge_doc": FOLDER_KNOWLEDGE,
    "report": FOLDER_REPORTS,
}

_DRIVE_SCOPES = ("https://www.googleapis.com/auth/drive.file",)
_UNSORTED_PROJECT = "Unsorted"
_FALLBACK_WARNING = "雲端儲存暫時未能完成，檔案已存於本機暫存。"


@dataclass
class DriveUploadResult:
    success: bool = False
    configured: bool = False
    provider: str = "local_runtime"
    drive_file_id: str | None = None
    drive_web_url: str | None = None
    folder: str | None = None
    warning: str = ""

    def to_public_dict(self) -> dict[str, Any]:
        """Safe view: provider/link/folder only — no paths, secrets or JSON."""
        return {
            "provider": self.provider,
            "drive_web_url": self.drive_web_url,
            "folder": self.folder,
            "warning": self.warning,
        }


def folder_for_file_type(file_type: str | None, *, source_module: str | None = None) -> str:
    """Map a file_type (and optional source module) to a Drive subfolder."""
    folder = _FILE_TYPE_FOLDER.get(str(file_type or "").strip().lower())
    if folder:
        return folder
    module = str(source_module or "").strip().lower()
    if module == "report_generation":
        return FOLDER_REPORTS
    if module == "drawing_analysis":
        return FOLDER_DRAWINGS
    if module == "knowledge_ingestion":
        return FOLDER_KNOWLEDGE
    if module == "upload_analysis":
        return FOLDER_PHOTOS
    return FOLDER_PHOTOS


class DriveUploader:
    """Uploader contract. Implementations must not raise secrets into errors."""

    def ensure_folder(self, name: str, parent_id: str) -> str:  # pragma: no cover - interface
        raise NotImplementedError

    def upload_file(self, *, local_path: str, file_name: str, mime_type: str | None, parent_id: str) -> tuple[str, str]:  # pragma: no cover - interface
        raise NotImplementedError


class GoogleDriveUploader(DriveUploader):
    """Real Drive uploader; imports the Google client lazily on construction."""

    def __init__(self, service_account_info: dict[str, Any]):
        from google.oauth2 import service_account  # type: ignore
        from googleapiclient.discovery import build  # type: ignore

        credentials = service_account.Credentials.from_service_account_info(
            service_account_info, scopes=list(_DRIVE_SCOPES)
        )
        self._service = build("drive", "v3", credentials=credentials, cache_discovery=False)

    def ensure_folder(self, name: str, parent_id: str) -> str:
        safe_name = str(name or "").replace("'", "\\'")
        query = (
            "mimeType='application/vnd.google-apps.folder' and trashed=false "
            f"and name='{safe_name}' and '{parent_id}' in parents"
        )
        response = self._service.files().list(
            q=query, spaces="drive", fields="files(id,name)", pageSize=1,
            supportsAllDrives=True, includeItemsFromAllDrives=True,
        ).execute()
        files = response.get("files", [])
        if files:
            return files[0]["id"]
        created = self._service.files().create(
            body={"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]},
            fields="id", supportsAllDrives=True,
        ).execute()
        return created["id"]

    def upload_file(self, *, local_path: str, file_name: str, mime_type: str | None, parent_id: str) -> tuple[str, str]:
        from googleapiclient.http import MediaFileUpload  # type: ignore

        media = MediaFileUpload(local_path, mimetype=mime_type or "application/octet-stream", resumable=False)
        created = self._service.files().create(
            body={"name": file_name, "parents": [parent_id]},
            media_body=media, fields="id,webViewLink", supportsAllDrives=True,
        ).execute()
        return created["id"], created.get("webViewLink", "")


class DriveStorage:
    """Routes an uploaded file to ``<root>/<project>/<subfolder>`` on Drive."""

    def __init__(self, *, uploader: DriveUploader, config: DriveConfig):
        self._uploader = uploader
        self._config = config

    def upload(
        self,
        local_path: str | Path,
        *,
        file_name: str,
        file_type: str | None,
        project_ref: str | None,
        mime_type: str | None = None,
        source_module: str | None = None,
    ) -> DriveUploadResult:
        folder = folder_for_file_type(file_type, source_module=source_module)
        try:
            root_id = self._config.root_folder_id
            project_id = self._uploader.ensure_folder(str(project_ref or _UNSORTED_PROJECT), root_id)
            subfolder_id = self._uploader.ensure_folder(folder, project_id)
            file_id, web_url = self._uploader.upload_file(
                local_path=str(local_path),
                file_name=str(file_name or "upload"),
                mime_type=mime_type,
                parent_id=subfolder_id,
            )
        except Exception:
            return DriveUploadResult(
                success=False, configured=True, provider="local_runtime",
                folder=folder, warning=_FALLBACK_WARNING,
            )
        if not file_id:
            return DriveUploadResult(
                success=False, configured=True, provider="local_runtime",
                folder=folder, warning=_FALLBACK_WARNING,
            )
        return DriveUploadResult(
            success=True, configured=True, provider="google_drive",
            drive_file_id=str(file_id), drive_web_url=(web_url or None), folder=folder,
        )


def _build_real_uploader(config: DriveConfig) -> DriveUploader | None:
    if not config.service_account_info:
        return None
    try:
        return GoogleDriveUploader(config.service_account_info)
    except Exception:
        return None


def upload_to_drive_if_configured(
    local_path: str | Path,
    *,
    file_name: str,
    file_type: str | None,
    project_ref: str | None = None,
    mime_type: str | None = None,
    source_module: str | None = None,
    uploader: DriveUploader | None = None,
    config: DriveConfig | None = None,
    secrets: Any = None,
) -> DriveUploadResult:
    """Upload to Drive when configured; otherwise return a safe local fallback.

    Never raises. When Drive is not configured the result is a benign
    ``local_runtime`` fallback with no warning; when configured but the upload
    fails, the result carries a safe Traditional-Chinese warning only.
    """
    cfg = config or load_drive_config(secrets)
    if not cfg.enabled:
        return DriveUploadResult(success=False, configured=False, provider="local_runtime")
    active_uploader = uploader or _build_real_uploader(cfg)
    if active_uploader is None:
        return DriveUploadResult(
            success=False, configured=True, provider="local_runtime", warning=_FALLBACK_WARNING,
        )
    return DriveStorage(uploader=active_uploader, config=cfg).upload(
        local_path,
        file_name=file_name,
        file_type=file_type,
        project_ref=project_ref,
        mime_type=mime_type,
        source_module=source_module,
    )


def storage_provider_label(provider: str | None) -> str:
    """Traditional-Chinese label for a storage provider (UI-safe)."""
    return {
        "google_drive": "Google Drive",
        "google_drive_ready": "Drive-ready",
        "local_runtime": "本機暫存",
        "external_reference": "外部連結",
    }.get(str(provider or "").strip(), "本機暫存")
