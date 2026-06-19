"""Evidence guardrails, credible risk floors, and concise image summaries."""

from __future__ import annotations

import re
from typing import Any, Iterable


HOT_WORK_CATEGORIES = {"hot_work", "cutting_grinding", "fire_risk"}

_GUARDED_ASSUMPTIONS = {
    "棚架": ("棚架", "scaffold"),
    "氣樽": ("氣樽", "氣瓶", "gas cylinder", "cylinder"),
    "高空工作": ("高空工作", "高處工作", "working at height", "elevated work"),
    "安全帶": ("安全帶", "harness", "fall arrest"),
    "護欄": ("護欄", "guardrail"),
    "踢腳板": ("踢腳板", "toe board", "toeboard"),
}

_RISK_RANK = {"低風險": 1, "中風險": 2, "高風險": 3, "極高風險": 4}
_RISK_ALIASES = {
    "low": "低風險",
    "medium": "中風險",
    "high": "高風險",
    "critical": "極高風險",
    "低": "低風險",
    "中": "中風險",
    "高": "高風險",
    "極高": "極高風險",
}


def filter_unsupported_assumptions(
    claims: Iterable[Any],
    evidence_items: Iterable[Any] | None = None,
    explicit_context: str = "",
) -> tuple[list[str], list[str]]:
    """Keep guarded claims only when independent evidence supports the term."""
    evidence_text = " ".join([*_string_items(evidence_items), str(explicit_context or "")]).lower()
    kept: list[str] = []
    unsupported: list[str] = []
    for value in claims or []:
        claim = " ".join(str(value or "").split())
        if not claim:
            continue
        missing = [
            label
            for label, terms in _GUARDED_ASSUMPTIONS.items()
            if any(term.lower() in claim.lower() for term in terms)
            and not _has_positive_evidence(evidence_text, terms, label)
        ]
        if missing:
            unsupported.append(f"{claim}（缺乏可見或明確提供的{'／'.join(missing)}證據）")
        else:
            kept.append(claim)
    return _dedupe(kept), _dedupe(unsupported)


def sanitize_generated_analysis(
    text: str,
    evidence_items: Iterable[Any] | None = None,
    explicit_context: str = "",
) -> tuple[str, list[str]]:
    """Remove unsupported guarded assumptions from generated report prose."""
    segments = [part.strip() for part in re.split(r"(?<=[。！？!?])\s*|\r?\n", str(text or "")) if part.strip()]
    kept, unsupported = filter_unsupported_assumptions(segments, evidence_items, explicit_context)
    if not kept:
        kept = ["目前只有有限相片證據，請以可見內容及現場覆核結果作判斷。"]
    return "\n".join(kept), unsupported


def filter_unsupported_payload(
    payload: Any,
    evidence_items: Iterable[Any] | None = None,
    explicit_context: str = "",
) -> tuple[Any, list[str]]:
    """Recursively remove unsupported guarded claims from merged/action data."""
    unsupported: list[str] = []

    def clean(value: Any) -> Any:
        if isinstance(value, str):
            kept, rejected = filter_unsupported_assumptions([value], evidence_items, explicit_context)
            unsupported.extend(rejected)
            return kept[0] if kept else ""
        if isinstance(value, list):
            cleaned = [clean(item) for item in value]
            return [item for item in cleaned if item not in (None, "", [], {})]
        if isinstance(value, tuple):
            return tuple(item for item in (clean(entry) for entry in value) if item not in (None, "", [], {}))
        if isinstance(value, dict):
            cleaned_dict = {key: clean(item) for key, item in value.items()}
            for claim_key in ("label", "description", "action", "recommendation"):
                if str(value.get(claim_key) or "").strip() and not str(cleaned_dict.get(claim_key) or "").strip():
                    return {}
            return cleaned_dict
        return value

    return clean(payload), _dedupe(unsupported)


def credible_visual_risk(image_analysis: Any) -> str:
    data = _as_dict(image_analysis)
    category = str(data.get("image_category") or data.get("detected_category") or "unknown")
    evidence_text = " ".join(
        [
            *_string_items(data.get("evidence_items")),
            *_string_items(data.get("visual_observations") or data.get("key_observations")),
            *_string_items(data.get("risks")),
        ]
    ).lower()
    if category in {"fire_risk"}:
        return "高風險"
    if category in {"hot_work", "cutting_grinding"}:
        high_indicators = (
            "室內", "狹窄", "enclosed", "combustible", "易燃", "可燃",
            "缺乏防火", "沒有滅火", "no fire", "face protection missing",
        )
        return "高風險" if any(term in evidence_text for term in high_indicators) else "中風險"
    if category in {"ppe_issue", "safety_issue"}:
        return "中風險"
    return "低風險"


def merge_credible_risk(
    final_risk: str,
    raw_risk: str,
    image_analysis: Any = None,
    *,
    mitigation_evidence: bool = False,
) -> str:
    """Prevent unexplained downgrade below credible raw/visual safety risk."""
    final_level = _normalise_risk(final_risk)
    raw_level = _normalise_risk(raw_risk)
    visual_level = credible_visual_risk(image_analysis) if image_analysis else "低風險"
    floor = visual_level if mitigation_evidence else max((raw_level, visual_level), key=_risk_rank)
    return max((final_level, floor), key=_risk_rank)


def build_concise_image_summary(image_analysis: Any) -> dict[str, Any]:
    """Create a bounded, practical report summary from image evidence only."""
    data = _as_dict(image_analysis)
    category = str(data.get("image_category") or data.get("detected_category") or "unknown")
    observations = _string_items(data.get("visual_observations") or data.get("key_observations"))
    evidence_items = _string_items(data.get("evidence_items"))
    risks = _string_items(data.get("risks"))
    unsupported = _string_items(data.get("unsupported_assumptions"))
    raw_metadata = data.get("raw_metadata") if isinstance(data.get("raw_metadata"), dict) else {}
    evidence_context = raw_metadata.get("evidence_context") if isinstance(raw_metadata.get("evidence_context"), dict) else {}
    no_specific_evidence = bool(
        evidence_context
        and
        not evidence_context.get("has_visual_analysis")
        and not evidence_context.get("has_ocr_text")
        and not str(evidence_context.get("user_description") or "").strip()
        and not evidence_context.get("evidenced_terms")
    )

    if category in HOT_WORK_CATEGORIES:
        observations = observations or _hot_work_observations(evidence_items)
        risks = risks or [
            "火花可能引燃附近物料或裝修材料。",
            "火花可能損壞門框、牆身或已完成飾面。",
            "金屬碎屑或火花可能造成眼部及面部受傷。",
            "電動工具操作有割傷或反彈風險。",
            "室內位置的通風及走火通道需要確認。",
        ]
        confirmations = [
            "未能從相片確認是否有防火氈、滅火筒、熱工許可證或防火監護人。",
            "未能從相片確認附近易燃物是否已完全移走或遮蓋。",
        ]
    else:
        confirmations = []

    followups = data.get("recommended_followups") if isinstance(data.get("recommended_followups"), list) else []
    recommendations = []
    responsible = []
    for item in followups:
        if isinstance(item, dict):
            action = str(item.get("action") or item.get("title") or "").strip()
            role = str(item.get("responsible_role") or "").strip()
        else:
            action, role = str(item).strip(), ""
        if action:
            recommendations.append(action)
        if role:
            responsible.append(role)
    if category in HOT_WORK_CATEGORIES and not recommendations:
        recommendations = [
            "確認是否需要熱工許可證，並在開工前完成審批。",
            "清走或遮蓋附近可燃物，並保護門框、牆身及已完成飾面。",
            "放置合適滅火筒及防火氈，按需要安排防火監察及工後巡查。",
            "確認工人使用眼罩或面罩、手套、長袖及適合該工具的 PPE。",
            "拍攝整改、防火措施及工後狀況照片作記錄。",
        ]
        responsible = ["管工／安全主任／熱工許可證簽發人"]

    if no_specific_evidence:
        observations = ["未能確認相片中的具體工序；請補充位置、工序及需跟進事項。"]
        risks = []
        recommendations = ["補充現場描述或啟用 Vision API，再由管工／安全主任作人工覆核。"]
        confirmations = ["未有足夠 OCR、AI 視覺或使用者描述證據，暫不判斷具體危害。"]
        responsible = ["相片提交者／管工"]

    # Unsupported assumptions remain available in the typed analysis payload
    # and collapsed debug/evidence UI, but do not enter the client summary.
    ocr_text = str(data.get("ocr_text") or "").strip()
    limitations = [
        "OCR 文字：已偵測到文字，仍須對照原圖。" if ocr_text else "OCR 文字：未偵測到清晰文字。",
        (
            "視覺分析：已根據可見內容分析；未顯示的控制措施不可當作不存在。"
            if evidence_context.get("has_visual_analysis")
            else "未能進行 AI 視覺辨識；請補充工序描述或啟用 Vision API。"
        ),
    ]
    return {
        "observations": _dedupe(observations)[:5],
        "risk_level": "需人工覆核" if no_specific_evidence else credible_visual_risk(data),
        "risks": _dedupe(risks)[:5],
        "recommendations": _dedupe(recommendations)[:5],
        "confirmations": _dedupe(confirmations)[:5],
        "responsible": _dedupe(responsible)[:5],
        "limitations": limitations[:5],
    }


def render_concise_image_summary(image_analysis: Any) -> str:
    summary = build_concise_image_summary(image_analysis)
    sections = (
        ("相片所見", summary["observations"]),
        ("初步風險級別", [summary["risk_level"]]),
        ("主要風險", summary["risks"]),
        ("建議", summary["recommendations"]),
        ("需確認事項", summary["confirmations"]),
        ("負責跟進", summary["responsible"]),
        ("來源 / 限制", summary["limitations"]),
    )
    blocks = []
    for heading, items in sections:
        if items:
            blocks.append(heading + "\n" + "\n".join(f"- {item}" for item in items[:5]))
    return "\n\n".join(blocks)


def _hot_work_observations(evidence_items: list[str]) -> list[str]:
    text = " ".join(evidence_items).lower()
    observations = []
    if any(term in text for term in ("磨機", "切割", "grinder", "grinding", "cutting")):
        observations.append("已確認：工人正在使用磨機或切割工具。")
    if any(term in text for term in ("火花", "sparks", "spark")):
        observations.append("已確認：工序產生明顯火花。")
    if any(term in text for term in ("安全帽", "手套", "長袖", "helmet", "gloves", "long sleeve")):
        observations.append("已確認：相片可見部分個人防護裝備；眼部及面部保護仍需現場確認。")
    return observations or ["相片顯示可能涉及熱工或切割工序，需由現場人員確認。"]


def _has_positive_evidence(evidence_text: str, terms: Iterable[str], label: str = "") -> bool:
    if not any(term.lower() in evidence_text for term in terms):
        return False
    if label == "安全帶":
        return any(
            term in evidence_text
            for term in ("防墮", "墮下", "高空", "高處", "臨邊", "fall arrest", "fall protection", "working at height")
        )
    return True


def _normalise_risk(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in _RISK_RANK:
        return text
    return _RISK_ALIASES.get(text, "中風險")


def _risk_rank(value: str) -> int:
    return _RISK_RANK.get(value, 2)


def _string_items(values: Any) -> list[str]:
    if not isinstance(values, (list, tuple, set)):
        return []
    items = []
    for value in values:
        if isinstance(value, dict):
            text = value.get("text") or value.get("description") or value.get("label") or ""
        else:
            text = value
        text = " ".join(str(text or "").split())
        if text:
            items.append(text)
    return items


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return {}


def _dedupe(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))
