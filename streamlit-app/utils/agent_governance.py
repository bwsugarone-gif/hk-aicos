# -*- coding: utf-8 -*-
"""
utils/agent_governance.py
HK-AICOS Phase 2.5F+ — Agent Personality & Governance Layer

Responsibilities:
  1. Load agent personality profiles from config/agents.json
  2. Inject personality into prompts (build_prompt_from_agents)
  3. Multi-agent fault tolerance — skip failed agents, continue others
  4. Write incident reports to logs/agent_incident_reports/
  5. PM Agent final authority — consolidate risk level, enforce safety floor
"""

import json
import sys
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Paths ─────────────────────────────────────────────────────────────────────
_BASE_DIR      = Path(__file__).parent.parent          # streamlit-app/
_CONFIG_FILE   = _BASE_DIR / "config" / "agents.json"
_INCIDENT_DIR  = _BASE_DIR / "logs" / "agent_incident_reports"
_INCIDENT_DIR.mkdir(parents=True, exist_ok=True)

# ── Load agent config ─────────────────────────────────────────────────────────
_AGENT_CONFIG: dict = {}
_GOVERNANCE_RULES: dict = {}

try:
    _raw = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
    _AGENT_CONFIG    = _raw.get("agents", {})
    _GOVERNANCE_RULES = _raw.get("governance_rules", {})
except Exception as _e:
    print(f"[agent_governance] WARNING: could not load agents.json: {_e}", file=sys.stderr)


# ── Public helpers ─────────────────────────────────────────────────────────────
def get_agent_personality(agent_id: str) -> str:
    """Return the personality string for an agent, or empty string if not found."""
    cfg = _AGENT_CONFIG.get(agent_id, {})
    return cfg.get("personality", "")


def get_agent_output_rules(agent_id: str) -> list:
    """Return the output_rules list for an agent."""
    cfg = _AGENT_CONFIG.get(agent_id, {})
    return cfg.get("output_rules", [])


def get_agent_fallback_text(agent_id: str) -> str:
    """Return the fallback text when an agent fails."""
    cfg = _AGENT_CONFIG.get(agent_id, {})
    return cfg.get(
        "fallback_behavior",
        f"{agent_id} Agent 未能完成分析，請稍後重試。",
    )


def build_personality_block(agent_id: str, display_name: str) -> str:
    """
    Build a personality + output rules block to inject into the agent prompt.
    Returns empty string if no config found (graceful degradation).
    """
    personality = get_agent_personality(agent_id)
    rules       = get_agent_output_rules(agent_id)
    if not personality and not rules:
        return ""

    lines = [f"性格與工作風格：{personality}"] if personality else []
    if rules:
        lines.append("輸出規則：")
        for r in rules:
            lines.append(f"  - {r}")
    return "\n".join(lines)


# ── Incident reporting ────────────────────────────────────────────────────────
def write_incident_report(
    failed_agent: str,
    error_type: str,
    error_message: str,
    recovery_action: str,
    project_ref: str = "",
    session_id: str = "",
    report_generated: bool = True,
    affected_sections: list = None,
) -> Path:
    """
    Write a JSON incident report to logs/agent_incident_reports/.
    Never raises — if writing fails, logs to stderr and returns None.
    """
    try:
        now = datetime.now(tz=timezone.utc)
        incident_id = f"INC-{now.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
        report = {
            "incident_id":          incident_id,
            "timestamp":            now.isoformat(),
            "project_ref":          str(project_ref or ""),
            "session_id":           str(session_id or ""),
            "failed_agent":         failed_agent,
            "error_type":           error_type,
            "error_message":        str(error_message)[:2000],  # cap length
            "recovery_action":      recovery_action,
            "whether_report_generated": report_generated,
            "affected_sections":    affected_sections or [],
        }
        path = _INCIDENT_DIR / f"{incident_id}.json"
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[agent_governance] Incident report written: {path.name}", file=sys.stderr)
        return path
    except Exception as e:
        print(f"[agent_governance] WARNING: could not write incident report: {e}", file=sys.stderr)
        return None


# ── Fault-tolerant multi-agent runner ────────────────────────────────────────
class AgentResult:
    """Holds the output of a single agent run."""
    def __init__(self, agent_id: str, success: bool, output: str, error: str = ""):
        self.agent_id = agent_id
        self.success  = success
        self.output   = output
        self.error    = error


def run_agents_with_fault_tolerance(
    agent_runners: dict,
    project_ref: str = "",
    session_id: str = "",
) -> tuple[dict, list]:
    """
    Run multiple agent callables with fault tolerance.

    Args:
        agent_runners: dict of {agent_id: callable}
                       Each callable takes no args and returns a string output.
        project_ref:   project reference for incident reports
        session_id:    session ID for incident reports

    Returns:
        (results, incidents)
        results:   dict of {agent_id: AgentResult}
        incidents: list of incident report paths (Path or None)
    """
    results   = {}
    incidents = []

    for agent_id, runner in agent_runners.items():
        try:
            output = runner()
            if not isinstance(output, str):
                output = str(output or "")
            output = output.strip()

            if not output:
                # Empty output — treat as soft failure
                fallback = get_agent_fallback_text(agent_id)
                results[agent_id] = AgentResult(
                    agent_id=agent_id,
                    success=False,
                    output=fallback,
                    error="empty_output",
                )
                inc = write_incident_report(
                    failed_agent=agent_id,
                    error_type="empty_output",
                    error_message="Agent returned empty string.",
                    recovery_action="Used fallback text. Other agents continued.",
                    project_ref=project_ref,
                    session_id=session_id,
                    report_generated=True,
                    affected_sections=[agent_id],
                )
                incidents.append(inc)
            else:
                results[agent_id] = AgentResult(
                    agent_id=agent_id,
                    success=True,
                    output=output,
                )

        except json.JSONDecodeError as e:
            fallback = get_agent_fallback_text(agent_id)
            results[agent_id] = AgentResult(
                agent_id=agent_id,
                success=False,
                output=fallback,
                error="json_parse_error",
            )
            inc = write_incident_report(
                failed_agent=agent_id,
                error_type="json_parse_error",
                error_message=str(e),
                recovery_action="Used fallback text. Other agents continued.",
                project_ref=project_ref,
                session_id=session_id,
                report_generated=True,
                affected_sections=[agent_id],
            )
            incidents.append(inc)

        except TimeoutError as e:
            fallback = get_agent_fallback_text(agent_id)
            results[agent_id] = AgentResult(
                agent_id=agent_id,
                success=False,
                output=fallback,
                error="timeout",
            )
            inc = write_incident_report(
                failed_agent=agent_id,
                error_type="timeout",
                error_message=str(e),
                recovery_action="Agent timed out. Used fallback text. Other agents continued.",
                project_ref=project_ref,
                session_id=session_id,
                report_generated=True,
                affected_sections=[agent_id],
            )
            incidents.append(inc)

        except Exception as e:
            tb = traceback.format_exc()
            fallback = get_agent_fallback_text(agent_id)
            results[agent_id] = AgentResult(
                agent_id=agent_id,
                success=False,
                output=fallback,
                error=type(e).__name__,
            )
            inc = write_incident_report(
                failed_agent=agent_id,
                error_type=type(e).__name__,
                error_message=f"{e}\n{tb[:500]}",
                recovery_action="Exception caught. Used fallback text. Other agents continued.",
                project_ref=project_ref,
                session_id=session_id,
                report_generated=True,
                affected_sections=[agent_id],
            )
            incidents.append(inc)

    return results, incidents


def has_any_failures(results: dict) -> bool:
    """Return True if any agent failed."""
    return any(not r.success for r in results.values())


def get_failure_notice(results: dict) -> str:
    """
    Return a user-facing notice string if any agents failed.
    Returns empty string if all succeeded.
    """
    failed = [aid for aid, r in results.items() if not r.success]
    if not failed:
        return ""
    return "部分 Agent 未能完成分析，詳情已記錄於系統報告。"


# ── PM Agent final authority ──────────────────────────────────────────────────
_RISK_ORDER = {"低風險": 0, "中風險": 1, "高風險": 2}
_RISK_LABELS = ["低風險", "中風險", "高風險"]

# Safety keywords that trigger high-risk floor
_SAFETY_HIGH_RISK_KEYWORDS = [
    "高風險", "高危", "死亡", "重傷", "倒塌", "火警", "停工令",
    "嚴重", "緊急", "立即停止", "重大安全",
]


def _detect_safety_risk_level(safety_output: str) -> str:
    """
    Infer the risk level from Safety Agent output text.
    Returns '高風險', '中風險', or '低風險'.
    """
    text = str(safety_output or "")
    if any(kw in text for kw in _SAFETY_HIGH_RISK_KEYWORDS):
        return "高風險"
    if any(kw in text for kw in ["中風險", "注意", "需要", "建議", "可能"]):
        return "中風險"
    return "低風險"


def pm_final_coordination(
    agent_results: dict,
    proposed_risk_level: str,
    selected_agents: list,
    project_ref: str = "",
    session_id: str = "",
) -> dict:
    """
    PM Agent final authority pass.

    1. Checks Safety Agent output — enforces safety floor on risk level.
    2. Returns final risk level and a coordination note.

    Args:
        agent_results:      dict of {agent_id: AgentResult}
        proposed_risk_level: risk level proposed by AI or upstream logic
        selected_agents:    list of agent IDs that were selected
        project_ref:        for incident reporting
        session_id:         for incident reporting

    Returns:
        dict with keys:
          final_risk_level  — enforced risk level string
          coordination_note — note to append to report (may be empty)
          safety_floor_applied — bool
    """
    safety_floor_applied = False
    coordination_note    = ""

    # Normalise proposed risk
    proposed_norm = str(proposed_risk_level or "中風險").strip()
    if proposed_norm not in _RISK_ORDER:
        proposed_norm = "中風險"

    final_risk = proposed_norm

    # Check Safety Agent output if it was selected and ran
    if "safety" in selected_agents and "safety" in agent_results:
        safety_result = agent_results["safety"]
        safety_inferred = _detect_safety_risk_level(safety_result.output)

        # Rule: if Safety Agent output implies high risk, final cannot be low risk
        if safety_inferred == "高風險":
            if _RISK_ORDER.get(final_risk, 0) < _RISK_ORDER["中風險"]:
                final_risk = "中風險"
                safety_floor_applied = True
                coordination_note = (
                    "Safety Agent 識別高風險事項。"
                    "根據管治規則，最終風險級別已調整為中風險或以上。"
                )
                # Log this as an incident for audit trail
                write_incident_report(
                    failed_agent="pm",
                    error_type="safety_floor_applied",
                    error_message=(
                        f"Proposed risk '{proposed_norm}' overridden to '{final_risk}' "
                        f"due to Safety Agent high-risk output."
                    ),
                    recovery_action="Risk level raised to meet safety floor.",
                    project_ref=project_ref,
                    session_id=session_id,
                    report_generated=True,
                    affected_sections=["risk_level"],
                )

    return {
        "final_risk_level":      final_risk,
        "coordination_note":     coordination_note,
        "safety_floor_applied":  safety_floor_applied,
    }


# ── Personality-enriched prompt builder ──────────────────────────────────────
def enrich_prompt_with_personality(
    base_prompt: str,
    selected_agent_ids: list,
) -> str:
    """
    Inject personality blocks into an existing prompt string.
    Appends a personality section after the agent instructions block.
    Safe to call even if agents.json is missing — returns base_prompt unchanged.
    """
    if not _AGENT_CONFIG:
        return base_prompt

    personality_lines = []
    for agent_id in selected_agent_ids:
        cfg = _AGENT_CONFIG.get(agent_id)
        if not cfg:
            continue
        display = cfg.get("display_name", agent_id)
        block   = build_personality_block(agent_id, display)
        if block:
            personality_lines.append(f"[{display}]\n{block}")

    if not personality_lines:
        return base_prompt

    personality_section = (
        "\n\nAgent 性格與輸出規則（必須遵守）：\n"
        + "\n\n".join(personality_lines)
    )
    return base_prompt + personality_section


# ── Convenience: load all agent configs ──────────────────────────────────────
def get_all_agent_configs() -> dict:
    """Return the full agent config dict (keyed by agent_id)."""
    return dict(_AGENT_CONFIG)


def get_governance_rules() -> dict:
    """Return the governance rules dict."""
    return dict(_GOVERNANCE_RULES)


# ── Self-test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Agent Governance Self-Test ===\n")

    # 1. Load check
    configs = get_all_agent_configs()
    print(f"Loaded {len(configs)} agent configs: {list(configs.keys())}")
    print(f"Governance rules: {get_governance_rules()}\n")

    # 2. Personality block
    block = build_personality_block("safety", "Safety Agent")
    print(f"Safety Agent personality block:\n{block}\n")

    # 3. Fault tolerance — simulate one agent failing
    def _good_agent():
        return "Engineering Agent 分析：工程進度正常，無重大技術風險。"

    def _failing_agent():
        raise ValueError("Simulated agent failure for testing")

    def _empty_agent():
        return ""

    runners = {
        "engineering": _good_agent,
        "safety":      _failing_agent,
        "pm":          _empty_agent,
    }

    results, incidents = run_agents_with_fault_tolerance(
        runners,
        project_ref="BW-TEST-001",
        session_id="test-session-governance",
    )

    print("Agent results:")
    for aid, r in results.items():
        status = "OK" if r.success else f"FAILED ({r.error})"
        print(f"  {aid}: {status} — {r.output[:60]}...")

    print(f"\nFailure notice: '{get_failure_notice(results)}'")
    print(f"Incidents written: {len([i for i in incidents if i])}\n")

    # 4. PM final authority
    pm_result = pm_final_coordination(
        agent_results=results,
        proposed_risk_level="低風險",
        selected_agents=["engineering", "safety", "pm"],
        project_ref="BW-TEST-001",
        session_id="test-session-governance",
    )
    print(f"PM final coordination: {pm_result}\n")

    # 5. Prompt enrichment
    base = "你是 HK-AICOS 分析系統。\n\n請分析以下工程問題。"
    enriched = enrich_prompt_with_personality(base, ["safety", "pm"])
    print(f"Enriched prompt (last 300 chars):\n...{enriched[-300:]}\n")

    print("=== Self-test complete ===")
