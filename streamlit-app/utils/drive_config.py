"""Google Drive Service Account configuration for AICOS (Phase 6.2 storage).

Reads configuration from environment variables or Streamlit secrets:

* ``AICOS_DRIVE_ENABLED``            — truthy to enable live Drive storage
* ``AICOS_DRIVE_ROOT_FOLDER_ID``     — shared Drive folder id (service account has access)
* ``GOOGLE_SERVICE_ACCOUNT_JSON``    — service account credentials (JSON string or a file path)

The parsed service-account info is kept private and is **never** placed into any
public status, UI string, log, or registry record. Public status only exposes
booleans / safe labels — never the key, private key, or client email.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


ENV_ENABLED = "AICOS_DRIVE_ENABLED"
ENV_ROOT_FOLDER = "AICOS_DRIVE_ROOT_FOLDER_ID"
ENV_SERVICE_ACCOUNT = "GOOGLE_SERVICE_ACCOUNT_JSON"

_TRUTHY = {"1", "true", "yes", "on", "enabled"}
_REQUIRED_SA_KEYS = ("client_email", "private_key", "token_uri")


@dataclass
class DriveConfig:
    enabled: bool = False
    root_folder_id: str | None = None
    credentials_present: bool = False
    reason: str = ""
    # Private: parsed service-account info. Never expose in UI / records / logs.
    service_account_info: dict[str, Any] | None = None

    def public_status(self) -> dict[str, Any]:
        """Safe status for admin diagnostics — booleans / labels only."""
        return {
            "enabled": self.enabled,
            "root_folder_set": bool(self.root_folder_id),
            "credentials_present": self.credentials_present,
            "reason": self.reason,
        }


def _get(name: str, secrets: Mapping[str, Any] | None) -> str:
    value = str(os.getenv(name, "") or "").strip()
    if value:
        return value
    if secrets:
        try:
            return str(secrets.get(name, "") or "").strip()
        except Exception:
            return ""
    return ""


def _truthy(value: str) -> bool:
    return str(value or "").strip().lower() in _TRUTHY


def _parse_service_account(raw: str) -> dict[str, Any] | None:
    """Parse the service-account JSON (string or file path). Never raises.

    Returns the parsed dict when it looks like service-account credentials, or
    ``None`` for missing / malformed input.
    """
    raw = str(raw or "").strip()
    if not raw:
        return None
    candidate = raw
    # Allow a path to a JSON file as well as inline JSON.
    if not raw.lstrip().startswith("{"):
        try:
            path = Path(raw)
            if path.exists() and path.is_file() and path.stat().st_size < 1_000_000:
                candidate = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None
    try:
        info = json.loads(candidate)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    if not isinstance(info, dict):
        return None
    return info


def _credentials_valid(info: dict[str, Any] | None) -> bool:
    if not isinstance(info, dict):
        return False
    return all(str(info.get(key) or "").strip() for key in _REQUIRED_SA_KEYS)


def load_drive_config(secrets: Mapping[str, Any] | None = None) -> DriveConfig:
    """Load Drive configuration from env / secrets. Never raises."""
    enabled_flag = _truthy(_get(ENV_ENABLED, secrets))
    root = _get(ENV_ROOT_FOLDER, secrets) or None
    info = _parse_service_account(_get(ENV_SERVICE_ACCOUNT, secrets))
    credentials_present = _credentials_valid(info)

    enabled = bool(enabled_flag and root and credentials_present)
    if not enabled_flag:
        reason = "未啟用 Google Drive（使用本機暫存）"
    elif not root:
        reason = "未設定 Drive 共用資料夾"
    elif not credentials_present:
        reason = "未設定或服務帳戶憑證無效"
    else:
        reason = "已設定 Google Drive"

    return DriveConfig(
        enabled=enabled,
        root_folder_id=root,
        credentials_present=credentials_present,
        reason=reason,
        service_account_info=info if credentials_present else None,
    )


def is_drive_enabled(secrets: Mapping[str, Any] | None = None) -> bool:
    return load_drive_config(secrets).enabled
