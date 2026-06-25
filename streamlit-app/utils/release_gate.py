"""Release gate / cloud QA / admin readiness checks for AICOS (Phase 6.5).

Pure, dependency-light and Streamlit-free so it can run in CI and unit tests.
The gate verifies that the core trial pages compile, that the key feature
modules are importable and expose their contracts, and that runtime/secret
status is reported as *configured / unconfigured only* — never as secret values.

Nothing here renders UI, performs network calls, or exposes local filesystem
paths or secrets to the normal product surface.
"""

from __future__ import annotations

import importlib
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping


APP_ROOT = Path(__file__).resolve().parents[1]

# key -> (relative page path, Traditional-Chinese label)
CORE_PAGES: tuple[tuple[str, str, str], ...] = (
    ("workspace", "pages/0_AICOS_Workspace.py", "AICOS 工作台"),
    ("upload", "pages/1_Upload.py", "上載分析"),
    ("ask", "pages/10_Ask_AICOS.py", "問 AICOS"),
    ("records", "pages/11_Records.py", "記錄"),
    ("drawing", "pages/12_Drawing_Analysis.py", "圖紙分析"),
    ("knowledge", "pages/13_Knowledge_Ingestion.py", "知識匯入"),
)

# key -> (module, required attributes, label)
READINESS_MODULES: tuple[tuple[str, str, tuple[str, ...], str], ...] = (
    ("runtime_warning", "utils.runtime_storage_health", ("get_runtime_storage_status",), "執行儲存警告"),
    ("file_registry", "utils.file_registry", ("register_file", "list_file_records", "search_file_records"), "檔案登記"),
    ("knowledge_ingestion", "utils.knowledge_ingestion", ("ingest_document", "ingest_text", "read_ingested_knowledge_sources"), "知識匯入"),
    ("drawing_analysis", "utils.drawing_store", ("append_drawing_document", "read_all_drawing_documents"), "圖紙分析"),
    ("cad_bim_handoff", "utils.drawing_handoff", ("generate_handoff_items", "extract_page_findings"), "CAD/BIM 交接"),
    ("records_search", "utils.records_search", ("build_unified_record_index", "search_unified_records"), "記錄統一搜尋"),
)

CHECKED_SECRETS: tuple[tuple[str, str], ...] = (
    ("GEMINI_API_KEY", "文字 / 視覺服務"),
    ("DEEPSEEK_API_KEY", "文字服務"),
    ("TAVILY_API_KEY", "網上搜尋"),
    ("AICOS_ADMIN_DIAGNOSTICS", "管理員診斷"),
)

# Secrets whose absence is a soft warning (app still works in fallback mode).
_OPTIONAL_SECRETS = {"GEMINI_API_KEY", "DEEPSEEK_API_KEY", "TAVILY_API_KEY", "AICOS_ADMIN_DIAGNOSTICS"}

SMOKE_TEST_FLOW: tuple[str, ...] = (
    "開啟 /AICOS_Workspace 工作台",
    "開啟 /Upload 上載地盤相片並完成分析",
    "於 /Drawing_Analysis 上載圖紙或 PDF",
    "確認已產生 CAD/BIM 交接事項",
    "於 /Knowledge_Ingestion 上載 PDF / TXT / MD",
    "確認已產生 RAG 片段",
    "於 /Records 搜尋圖紙 / 交接 / 知識 / 檔案記錄",
    "於 /Ask_AICOS 提問 PDF / 圖紙 / CAD-BIM 問題並取得引用",
)

# UI-safety scan: patterns that would leak internals into the normal product UI.
_UI_FORBIDDEN = ("st.exception(", "traceback.format_exc(", "os.environ)", "print(os.environ")


@dataclass
class CheckResult:
    key: str
    label: str
    status: str  # "pass" | "warn" | "fail"
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReleaseGateReport:
    checks: list[CheckResult] = field(default_factory=list)
    score: int = 0
    blocking_issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    smoke_test_flow: list[str] = field(default_factory=list)
    secret_status: dict[str, bool] = field(default_factory=dict)

    @property
    def ready(self) -> bool:
        return not self.blocking_issues

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["ready"] = self.ready
        return data


def _secret_configured(name: str, secrets: Mapping[str, Any] | None) -> bool:
    """True when a secret is present in env or the supplied secrets mapping.

    Only ever returns a boolean — the secret value is never returned, stored,
    logged, or placed into any report field.
    """
    if str(os.getenv(name, "") or "").strip():
        return True
    if secrets:
        try:
            return bool(str(secrets.get(name, "") or "").strip())
        except Exception:
            return False
    return False


def _check_page(rel_path: str, label: str, app_root: Path) -> CheckResult:
    path = app_root / rel_path
    if not path.exists():
        return CheckResult("page:" + rel_path, label, "fail", "頁面檔案不存在")
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
        compile(source, str(path.name), "exec")
    except SyntaxError:
        return CheckResult("page:" + rel_path, label, "fail", "頁面無法編譯")
    except OSError:
        return CheckResult("page:" + rel_path, label, "fail", "頁面無法讀取")
    return CheckResult("page:" + rel_path, label, "pass", "頁面存在並可編譯")


def _check_module(module_name: str, attrs: tuple[str, ...], label: str) -> CheckResult:
    try:
        module = importlib.import_module(module_name)
    except Exception:
        return CheckResult("module:" + module_name, label, "fail", "模組無法載入")
    missing = [attr for attr in attrs if not hasattr(module, attr)]
    if missing:
        return CheckResult("module:" + module_name, label, "fail", "缺少功能介面")
    return CheckResult("module:" + module_name, label, "pass", "模組已就緒")


def _check_ui_safety(app_root: Path) -> CheckResult:
    flagged: list[str] = []
    for _key, rel_path, _label in CORE_PAGES:
        path = app_root / rel_path
        if not path.exists():
            continue
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if any(token in source for token in _UI_FORBIDDEN):
            flagged.append(rel_path)
    if flagged:
        return CheckResult("ui_safety", "正常介面安全", "warn", "發現可能外洩內部資訊的介面寫法")
    return CheckResult("ui_safety", "正常介面安全", "pass", "未發現外洩 API 金鑰 / traceback / 原始 JSON 的寫法")


def evaluate_release_gate(
    *,
    app_root: str | Path | None = None,
    secrets: Mapping[str, Any] | None = None,
) -> ReleaseGateReport:
    """Run all release-gate checks and return a deterministic report."""
    root = Path(app_root) if app_root else APP_ROOT
    checks: list[CheckResult] = []

    for _key, rel_path, label in CORE_PAGES:
        checks.append(_check_page(rel_path, label, root))
    for _key, module_name, attrs, label in READINESS_MODULES:
        checks.append(_check_module(module_name, attrs, label))

    core_checks = list(checks)  # pages + readiness modules are the scored core
    ui_check = _check_ui_safety(root)
    checks.append(ui_check)

    secret_status = {name: _secret_configured(name, secrets) for name, _label in CHECKED_SECRETS}

    core_pass = sum(1 for c in core_checks if c.status == "pass")
    score = int(round(100 * core_pass / len(core_checks))) if core_checks else 0

    blocking_issues = [c.label for c in core_checks if c.status == "fail"]

    warnings: list[str] = []
    if ui_check.status == "warn":
        warnings.append(ui_check.detail)
    for name, label in CHECKED_SECRETS:
        if name in _OPTIONAL_SECRETS and not secret_status.get(name):
            warnings.append(f"未設定 {label}（{name}）— 將以本機備用模式運作")

    next_actions: list[str] = []
    if blocking_issues:
        next_actions.append("修復下列阻塞項目後再進行雲端冒煙測試：" + "、".join(blocking_issues))
    if not secret_status.get("GEMINI_API_KEY") and not secret_status.get("DEEPSEEK_API_KEY"):
        next_actions.append("設定至少一個文字服務金鑰（GEMINI_API_KEY 或 DEEPSEEK_API_KEY）以啟用完整回答。")
    if not secret_status.get("TAVILY_API_KEY"):
        next_actions.append("如需網上官方來源搜尋，設定 TAVILY_API_KEY。")
    if not blocking_issues:
        next_actions.append("按下方冒煙測試流程逐項驗證後即可開始內部 / 客戶試用。")

    return ReleaseGateReport(
        checks=checks,
        score=score,
        blocking_issues=blocking_issues,
        warnings=warnings,
        next_actions=next_actions,
        smoke_test_flow=list(SMOKE_TEST_FLOW),
        secret_status=secret_status,
    )
