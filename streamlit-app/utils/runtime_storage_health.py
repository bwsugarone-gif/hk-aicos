"""Cloud-aware health status for local AICOS JSONL runtime storage."""

from __future__ import annotations

import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = APP_ROOT / "data"
RUNTIME_FILES = (
    "aicos_memory.jsonl",
    "knowledge_index.jsonl",
    "followups.jsonl",
    "site_records.jsonl",
    "rag_index.jsonl",
)
CLOUD_WARNING = "目前使用暫存本機記憶；重新部署後資料可能消失。正式多人使用應接 Google Drive 或 Supabase。"


@dataclass
class RuntimeStorageStatus:
    mode: str
    storage_path: str
    writable: bool
    persistent_likely: bool
    warning_message: str
    affected_files: list[str] = field(default_factory=list)
    recommended_next_step: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def get_runtime_storage_status() -> RuntimeStorageStatus:
    mode = _runtime_mode()
    writable = _is_writable(DATA_DIR)
    persistent = bool(mode == "local_desktop" and writable)
    warning = CLOUD_WARNING if mode == "streamlit_cloud_like" else (
        "本機 JSONL 無法寫入；請檢查資料目錄權限。" if not writable else ""
    )
    return RuntimeStorageStatus(
        mode=mode,
        storage_path=str(DATA_DIR),
        writable=writable,
        persistent_likely=persistent,
        warning_message=warning,
        affected_files=list(RUNTIME_FILES),
        recommended_next_step=(
            "接入 Google Drive 或 Supabase 作持久儲存。"
            if not persistent else "持續備份 runtime JSONL，多人使用前遷移雲端儲存。"
        ),
    )


def _runtime_mode() -> str:
    hints = " ".join((str(Path.cwd()), str(APP_ROOT), os.getenv("HOME", ""))).lower()
    if any(os.getenv(name) for name in ("STREAMLIT_CLOUD", "STREAMLIT_SHARING_MODE")) or "/mount/src" in hints:
        return "streamlit_cloud_like"
    if os.name == "nt" or os.getenv("USERPROFILE"):
        return "local_desktop"
    return "unknown"


def _is_writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(prefix=".aicos-health-", dir=path, delete=True):
            return True
    except OSError:
        return False
