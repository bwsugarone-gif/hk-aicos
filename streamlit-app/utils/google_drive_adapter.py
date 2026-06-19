"""Google Drive knowledge adapter skeleton; no OAuth or live calls in Phase 5.9C."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from .knowledge_models import KnowledgeSource


@dataclass
class GoogleDriveFileMetadata:
    drive_file_id: str
    name: str
    mime_type: str = ""
    web_url: str = ""
    modified_time: str = ""
    size: int | None = None
    parent_path: str = ""
    tags: list[str] = field(default_factory=list)
    project_ref: str | None = None
    source_type: str = "uploaded_document"
    trust_level: str = "internal"

    def to_dict(self) -> dict:
        return asdict(self)


class GoogleDriveKnowledgeAdapter:
    """Metadata-only boundary ready for a future service-account/OAuth client."""

    def __init__(self, folder_id: str | None = None) -> None:
        self.folder_id = str(folder_id or os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")).strip()
        self.status = "configured_skeleton" if self.folder_id else "not_configured"

    def is_configured(self) -> bool:
        return bool(self.folder_id)

    def list_files(self, folder_id: str | None = None, query: str | None = None, limit: int = 50) -> list[GoogleDriveFileMetadata]:
        # TODO: replace with an injected Drive client after auth design approval.
        self.status = "live_api_not_enabled"
        return []

    def get_file_metadata(self, file_id: str) -> GoogleDriveFileMetadata | None:
        self.status = "live_api_not_enabled"
        return None

    def register_file_as_knowledge_source(self, file_metadata: GoogleDriveFileMetadata) -> KnowledgeSource:
        return self.build_source_from_drive_file(file_metadata)

    def build_source_from_drive_file(self, file_metadata: GoogleDriveFileMetadata) -> KnowledgeSource:
        return KnowledgeSource(
            source_id=f"gdrive:{file_metadata.drive_file_id}",
            title=file_metadata.name,
            source_type=file_metadata.source_type,
            path_or_url=file_metadata.web_url or None,
            trust_level=file_metadata.trust_level,
            jurisdiction="HK" if "hk" in " ".join(file_metadata.tags).lower() else None,
            trade_tags=list(file_metadata.tags),
            topic_tags=[],
            summary=f"Google Drive 檔案 metadata：{file_metadata.name}",
            extracted_refs=[],
            last_indexed_at=datetime.now(timezone.utc).isoformat(),
        )
