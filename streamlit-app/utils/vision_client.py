"""Optional Anthropic vision enrichment with explicit, non-throwing fallbacks."""

from __future__ import annotations

import base64
import json
import os
import re
import urllib.request
from pathlib import Path
from typing import Any


SUPPORTED_IMAGE_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}

_VISION_PROMPT = (
    "Analyse this Hong Kong construction-site image. Return JSON only with keys: "
    "category, confidence, extracted_text, evidence_items, observations, risks, "
    "unsupported_assumptions, needs_manual_review. category must be one of "
    "hot_work, cutting_grinding, fire_risk, ppe_issue, safety_issue, "
    "construction_defect, material_delivery, handwritten_record, "
    "attendance_or_timesheet, general_site_photo, unknown. evidence_items must list only "
    "clearly visible facts in concise Traditional Chinese. Use 已確認 only for clearly "
    "visible facts. Put uncertain guesses in unsupported_assumptions. Never infer scaffold, "
    "working at height, gas cylinders, missing harness, guardrails, or toe boards unless "
    "they are clearly visible. Keep all arrays concise."
)


def get_anthropic_api_key(explicit_key: str | None = None) -> str:
    return str(explicit_key or os.getenv("ANTHROPIC_API_KEY", "")).strip()


def get_gemini_api_key(explicit_key: str | None = None) -> str:
    return str(explicit_key or os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")).strip()


def generate_anthropic_message(
    prompt: str,
    *,
    api_key: str,
    image_path: str | Path | None = None,
    model: str | None = None,
    max_tokens: int = 4096,
) -> str:
    """Reusable Anthropic text/vision message call for the legacy report flow."""
    import anthropic

    selected_model = model or os.getenv("ANTHROPIC_VISION_MODEL", "claude-opus-4-5")
    content: str | list[dict[str, Any]] = prompt
    if image_path is not None:
        path = Path(image_path)
        media_type = SUPPORTED_IMAGE_TYPES.get(path.suffix.lower())
        if not media_type:
            raise ValueError(f"Unsupported image type: {path.suffix}")
        encoded = base64.standard_b64encode(path.read_bytes()).decode("ascii")
        content = [
            {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": encoded}},
            {"type": "text", "text": prompt},
        ]
    client = anthropic.Anthropic(api_key=api_key, timeout=60)
    response = client.messages.create(
        model=selected_model,
        max_tokens=max_tokens,
        temperature=0,
        messages=[{"role": "user", "content": content}],
    )
    return "".join(
        str(getattr(block, "text", ""))
        for block in getattr(response, "content", [])
        if getattr(block, "text", "")
    ).strip()


def analyze_image_with_vision(
    image_path: str | Path | None,
    *,
    api_key: str | None = None,
    gemini_api_key: str | None = None,
    model: str | None = None,
    client: Any | None = None,
) -> dict[str, Any]:
    """Return vision findings plus status metadata; never expose credentials."""
    path = Path(image_path) if image_path else None
    anthropic_key = get_anthropic_api_key(api_key)
    gemini_key = get_gemini_api_key(gemini_api_key)
    configured = bool(anthropic_key or gemini_key or client is not None)
    if path is None or path.suffix.lower() not in SUPPORTED_IMAGE_TYPES:
        return _status("unsupported_image_type", configured=configured)
    if not path.exists() or not path.is_file():
        return _status("image_not_found", configured=configured)

    if not anthropic_key and client is None and gemini_key:
        return _analyze_image_with_gemini(path, gemini_key)
    if not anthropic_key and client is None:
        return _status("not_configured", configured=False)

    selected_model = model or os.getenv("ANTHROPIC_VISION_MODEL", "claude-opus-4-5")
    try:
        if client is None:
            import anthropic

            client = anthropic.Anthropic(api_key=anthropic_key, timeout=30)

        encoded = base64.standard_b64encode(path.read_bytes()).decode("ascii")
        response = client.messages.create(
            model=selected_model,
            max_tokens=1200,
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": SUPPORTED_IMAGE_TYPES[path.suffix.lower()],
                                "data": encoded,
                            },
                        },
                        {
                            "type": "text",
                            "text": _VISION_PROMPT,
                        },
                    ],
                }
            ],
        )
        raw_text = "".join(
            str(getattr(block, "text", ""))
            for block in getattr(response, "content", [])
            if getattr(block, "text", "")
        ).strip()
        parsed = _parse_json_object(raw_text)
        return {
            "configured": True,
            "performed": True,
            "status": "success",
            "provider": "anthropic",
            "model": selected_model,
            "category": parsed.get("category", "unknown"),
            "confidence": _confidence(parsed.get("confidence")),
            "extracted_text": str(parsed.get("extracted_text") or "").strip(),
            "observations": _string_list(parsed.get("observations")),
            "risks": _string_list(parsed.get("risks")),
            "evidence_items": _string_list(parsed.get("evidence_items")),
            "unsupported_assumptions": _string_list(parsed.get("unsupported_assumptions")),
            "needs_manual_review": bool(parsed.get("needs_manual_review")),
        }
    except Exception as exc:
        result = _status("error", configured=True)
        result.update({
            "provider": "anthropic",
            "model": selected_model,
            "error": _safe_error(exc, anthropic_key),
        })
        return result


def _analyze_image_with_gemini(path: Path, api_key: str) -> dict[str, Any]:
    """Minimal Gemini REST vision adapter; no Google SDK dependency required."""
    model = os.getenv("GEMINI_VISION_MODEL", "gemini-2.5-flash")
    encoded = base64.standard_b64encode(path.read_bytes()).decode("ascii")
    payload = json.dumps(
        {
            "contents": [
                {
                    "parts": [
                        {"text": _VISION_PROMPT},
                        {
                            "inline_data": {
                                "mime_type": SUPPORTED_IMAGE_TYPES[path.suffix.lower()],
                                "data": encoded,
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
        parts = body.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        raw_text = "".join(str(part.get("text") or "") for part in parts if isinstance(part, dict))
        parsed = _parse_json_object(raw_text)
        return {
            "configured": True,
            "performed": True,
            "status": "success",
            "provider": "gemini",
            "model": model,
            "category": parsed.get("category", "unknown"),
            "confidence": _confidence(parsed.get("confidence")),
            "extracted_text": str(parsed.get("extracted_text") or "").strip(),
            "observations": _string_list(parsed.get("observations")),
            "risks": _string_list(parsed.get("risks")),
            "evidence_items": _string_list(parsed.get("evidence_items")),
            "unsupported_assumptions": _string_list(parsed.get("unsupported_assumptions")),
            "needs_manual_review": bool(parsed.get("needs_manual_review")),
        }
    except Exception as exc:
        result = _status("error", configured=True)
        result.update({"provider": "gemini", "model": model, "error": _safe_error(exc, api_key)})
        return result


def _status(status: str, *, configured: bool) -> dict[str, Any]:
    return {
        "configured": configured,
        "performed": False,
        "status": status,
        "provider": "anthropic" if configured else "none",
        "model": "",
        "category": "unknown",
        "confidence": 0.0,
        "extracted_text": "",
        "observations": [],
        "risks": [],
        "evidence_items": [],
        "unsupported_assumptions": [],
        "needs_manual_review": True,
    }


def _parse_json_object(text: str) -> dict[str, Any]:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        raise ValueError("Vision response did not contain a JSON object")
    parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("Vision response JSON must be an object")
    return parsed


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()][:8]


def _confidence(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _safe_error(exc: Exception, secret: str) -> str:
    message = f"{type(exc).__name__}: {exc}"[:500]
    return message.replace(secret, "[REDACTED]") if secret else message
