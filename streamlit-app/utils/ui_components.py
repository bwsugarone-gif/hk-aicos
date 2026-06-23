"""Shared Streamlit presentation components for the core AICOS pages."""

from __future__ import annotations

from collections.abc import Iterable
from html import escape

import streamlit as st

from .answer_formatter import AnswerDisplayModel
from .evidence_models import AnalysisBasis, RiskEvidenceTrace
from .risk_evidence import summarize_analysis_basis


PRODUCT_FOOTER = "Buildway Tech (HK) Limited | HK-AICOS"


def inject_shared_styles() -> None:
    st.markdown(
        """
        <style>
        .aicos-page-header {background:linear-gradient(135deg,#1a3a5c,#2d5a8e);color:#fff;
            padding:1.45rem 1.65rem;border-radius:14px;margin:0 0 1.2rem 0;}
        .aicos-page-header h1 {font-size:1.65rem;margin:0 0 .3rem 0;}
        .aicos-page-header p {font-size:.96rem;opacity:.92;margin:0;}
        .aicos-review-card {background:#fff8e8;border:1px solid #e4c26a;border-radius:10px;
            padding:.8rem 1rem;margin:.75rem 0;color:#493b18;}
        .aicos-answer-card {background:#fff;border:1px solid #dbe2ea;border-radius:12px;
            padding:1rem 1.15rem;margin:.6rem 0;box-shadow:0 2px 8px rgba(26,58,92,.06);}
        .aicos-footer {text-align:center;color:#7c8794;padding:1.6rem 0 .5rem;font-size:.8rem;}
        .aicos-risk {display:inline-block;border-radius:16px;padding:.2rem .7rem;font-weight:700;}
        .aicos-upload-cta {border:1px solid #d4ad4d !important;background:#fffaf0;
            border-radius:14px;padding:1rem 1.1rem;box-shadow:0 3px 12px rgba(26,58,92,.08);}
        .aicos-upload-cta strong {display:block;color:#1a3a5c;font-size:1.08rem;margin-bottom:.25rem;}
        .aicos-upload-cta p {margin:0;color:#42566a;}
        @media(max-width:768px){.aicos-page-header{padding:1.1rem}.aicos-page-header h1{font-size:1.35rem}}
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str, icon: str = "🏗️") -> None:
    inject_shared_styles()
    st.markdown(
        f'<div class="aicos-page-header"><h1>{escape(icon)} {escape(title)}</h1>'
        f'<p>{escape(subtitle)}</p></div>',
        unsafe_allow_html=True,
    )


def compact_link_row(links: Iterable[tuple[str, str]]) -> None:
    links = list(links)
    if not links:
        return
    columns = st.columns(len(links))
    for column, (path, label) in zip(columns, links):
        with column:
            st.page_link(path, label=label, use_container_width=True)


def render_review_notice(messages: Iterable[str]) -> None:
    clean = list(dict.fromkeys(str(message).strip() for message in messages if str(message).strip()))
    if not clean:
        return
    body = "<br/>".join(f"• {escape(message)}" for message in clean[:4])
    st.markdown(f'<div class="aicos-review-card"><strong>覆核提醒</strong><br/>{body}</div>', unsafe_allow_html=True)


def render_answer_card(model: AnswerDisplayModel, *, compact: bool = False) -> None:
    inject_shared_styles()
    st.markdown(
        f'<div class="aicos-answer-card"><strong>{escape(model.title)}</strong></div>',
        unsafe_allow_html=True,
    )
    sections = [
        ("最簡單講", model.summary_bullets),
        ("判斷依據", model.judgement_basis_bullets),
        ("主要風險 / 影響", model.risk_impact_bullets),
        ("建議", model.recommendations_bullets),
        ("需確認事項", model.confirmation_bullets),
        ("來源 / 限制", model.source_limitations),
    ]
    for heading, items in sections:
        if items:
            st.markdown(f"#### {heading}")
            for item in items[:2] if compact else items:
                st.markdown(f"- {item}")
    render_review_notice(model.warning_labels)
    if model.memory_status:
        st.caption(model.memory_status)
    with st.expander("技術狀態", expanded=False):
        st.caption(f"回答信心：{model.confidence_label} · {model.technical_note}")
        labels = {
            "text_answer": "文字回答",
            "ai_vision": "AI 視覺",
            "web_search": "網上搜尋",
        }
        for key, label in labels.items():
            if key in model.technical_status:
                st.caption(f"{label}：" + ("已設定" if model.technical_status[key] else "未設定"))


def render_risk_evidence_trace(
    trace: RiskEvidenceTrace,
    basis: AnalysisBasis | None = None,
    *,
    compact: bool = False,
) -> None:
    """Render observable risk rationale without provider or chain-of-thought details."""
    st.markdown("#### 風險判斷來源")
    for item in trace.triggered_by[:2 if compact else 4]:
        st.markdown(f"- {item}")
    if trace.rules_matched:
        st.markdown("- 風險規則：" + "、".join(trace.rules_matched))
    if trace.missing_confirmations:
        st.markdown("- 需確認：" + "、".join(trace.missing_confirmations[:4 if compact else 7]))
    if trace.final_reason:
        st.markdown(f"- {trace.final_reason}")
    if basis:
        st.markdown("#### 分析依據")
        for item in summarize_analysis_basis(basis)[:4 if compact else 8]:
            st.markdown(f"- {item}")


def risk_badge(label: str) -> None:
    aliases = {
        "LOW": "低風險",
        "MEDIUM": "中風險",
        "HIGH": "高風險",
        "CRITICAL": "極高風險",
        "UNKNOWN": "需人工覆核",
    }
    label = aliases.get(str(label).strip().upper(), str(label).strip() or "需人工覆核")
    colors = {
        "低風險": ("#e8f6ec", "#24733c"),
        "中風險": ("#fff4df", "#9b5b00"),
        "高風險": ("#fdeaea", "#a62424"),
        "極高風險": ("#f5dede", "#6f0000"),
        "需人工覆核": ("#eef1f5", "#4f5b67"),
    }
    background, foreground = colors.get(str(label), colors["需人工覆核"])
    st.markdown(
        f'<span class="aicos-risk" style="background:{background};color:{foreground};">{escape(label)}</span>',
        unsafe_allow_html=True,
    )


def render_product_footer() -> None:
    st.markdown(f'<div class="aicos-footer">{PRODUCT_FOOTER}</div>', unsafe_allow_html=True)
