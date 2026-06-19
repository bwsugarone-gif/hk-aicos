import importlib
import py_compile
import subprocess
import sys
from dataclasses import fields
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_ROOT.parent


def test_analysis_models_stably_reexports_evidence_contracts():
    from utils.analysis_models import AnalysisBasis, RiskEvidenceTrace
    from utils.evidence_models import AnalysisBasis as CanonicalAnalysisBasis
    from utils.evidence_models import RiskEvidenceTrace as CanonicalRiskEvidenceTrace

    assert AnalysisBasis is CanonicalAnalysisBasis
    assert RiskEvidenceTrace is CanonicalRiskEvidenceTrace
    assert [item.name for item in fields(AnalysisBasis)] == [
        "text_extraction_basis",
        "vision_basis",
        "manual_description_basis",
        "knowledge_basis",
        "memory_basis",
        "rule_basis",
        "limitations",
    ]
    assert [item.name for item in fields(RiskEvidenceTrace)] == [
        "risk_level",
        "triggered_by",
        "evidence_sources",
        "rules_matched",
        "missing_confirmations",
        "confidence_reason",
        "final_reason",
    ]


def test_risk_evidence_imports_without_analysis_model_cycle():
    module = importlib.import_module("utils.risk_evidence")
    assert callable(module.build_analysis_basis)
    assert callable(module.build_risk_evidence_trace)
    assert module.build_analysis_basis().limitations


def test_import_smoke_from_repo_root():
    code = (
        "import sys; sys.path.insert(0, 'streamlit-app'); "
        "from utils.analysis_models import AnalysisBasis, RiskEvidenceTrace; "
        "from utils.risk_evidence import build_analysis_basis, build_risk_evidence_trace; "
        "assert AnalysisBasis and RiskEvidenceTrace and build_analysis_basis and build_risk_evidence_trace"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_import_smoke_from_streamlit_app_working_directory():
    code = (
        "from utils.analysis_models import AnalysisBasis, RiskEvidenceTrace; "
        "from utils.risk_evidence import build_analysis_basis; "
        "assert AnalysisBasis and RiskEvidenceTrace and build_analysis_basis"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=APP_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_production_entrypoints_compile_with_stable_imports():
    paths = (
        "app.py",
        "pages/0_AICOS_Workspace.py",
        "pages/1_Upload.py",
        "pages/2_Report.py",
        "pages/10_Ask_AICOS.py",
        "utils/analysis_models.py",
        "utils/evidence_models.py",
        "utils/risk_evidence.py",
    )
    for relative in paths:
        py_compile.compile(str(APP_ROOT / relative), doraise=True)
