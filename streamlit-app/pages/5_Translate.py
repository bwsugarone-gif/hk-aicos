"""
pages/5_Translate.py
HK-AICOS Phase 2.5G — 文件翻譯與格式轉換專區

Buildway Tech (HK) Limited
"""

import streamlit as st
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logo_helper import sidebar_logo

st.set_page_config(
    page_title="文件翻譯與轉換 | HK-AICOS",
    page_icon="📑",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a3a5c 0%, #0f2942 100%);
    }
    [data-testid="stSidebar"] * { color: white !important; }

    .page-header {
        background: linear-gradient(135deg, #1a3a5c 0%, #2d5a8e 100%);
        color: white;
        padding: 1.8rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
    }
    .page-header h2 { font-size: 1.6rem; margin: 0 0 0.3rem 0; }
    .page-header p  { font-size: 1rem; opacity: 0.9; margin: 0; }

    .section-card {
        background: white;
        border-radius: 10px;
        padding: 1.5rem;
        box-shadow: 0 2px 8px rgba(26,58,92,0.08);
        margin-bottom: 1.2rem;
    }
    .section-card h3 {
        color: #1a3a5c;
        font-size: 1.1rem;
        border-bottom: 2px solid #c9a84c;
        padding-bottom: 0.5rem;
        margin-bottom: 1rem;
    }

    .beta-badge {
        display: inline-block;
        background: #fff3cd;
        color: #856404;
        border: 1px solid #ffc107;
        border-radius: 12px;
        padding: 0.1rem 0.6rem;
        font-size: 0.75rem;
        font-weight: 700;
        margin-left: 0.4rem;
        vertical-align: middle;
    }

    .info-box {
        background: #eaf0fb;
        border-left: 4px solid #1a3a5c;
        border-radius: 6px;
        padding: 0.8rem 1rem;
        font-size: 0.9rem;
        color: #1a3a5c;
        margin-bottom: 0.8rem;
    }

    .disclaimer-box {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 1rem 1.5rem;
        border-left: 4px solid #6c757d;
        font-size: 0.82rem;
        color: #555;
        margin-top: 1rem;
    }

    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #1a3a5c 0%, #2d5a8e 100%);
        color: white;
        font-weight: 700;
        font-size: 1rem;
        padding: 0.7rem 1.5rem;
        border: none;
        border-radius: 10px;
        width: 100%;
    }

    @media (max-width: 768px) {
        .page-header h2 { font-size: 1.3rem; }
        .section-card { padding: 1rem; }
    }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    sidebar_logo()
    st.markdown("---")
    st.page_link("app.py",               label="🏠 首頁")
    st.page_link("pages/1_Upload.py",    label="📤 上載分析")
    st.page_link("pages/2_Report.py",    label="📄 分析報告")
    st.page_link("pages/3_History.py",   label="🕘 歷史紀錄")
    st.page_link("pages/5_Translate.py", label="📑 文件翻譯與轉換")
    st.page_link("pages/4_About.py",     label="ℹ️ 關於 Buildway Tech")
    st.markdown("---")
    st.markdown('<div style="font-size:0.78rem; color:#aac4e0;">🔒 所有資料安全處理</div>', unsafe_allow_html=True)

# ── Page Header ───────────────────────────────────────────────────────────────
st.markdown("""
<div class="page-header">
    <h2>📑 文件翻譯與格式轉換</h2>
    <p>工程文書翻譯、合約翻譯、Excel / DOCX / PDF 格式轉換。由 Translator Agent 處理。</p>
</div>
""", unsafe_allow_html=True)

# ── Mode selector ─────────────────────────────────────────────────────────────
MODE_OPTIONS = {
    "🌐 文字翻譯（直接輸入）":               "text_translate",
    "📄 文件翻譯（上載 PDF / DOCX / XLSX）": "file_translate",
    "🔄 格式轉換（Excel → PDF）":            "excel_to_pdf",
    "🔄 格式轉換（DOCX → PDF）":             "docx_to_pdf",
    "🖼️ 圖片 → PowerPoint（Beta）":          "image_to_pptx",
}

selected_mode_label = st.selectbox("選擇功能", list(MODE_OPTIONS.keys()), index=0)
mode = MODE_OPTIONS[selected_mode_label]

st.markdown("---")


# ── Helpers (defined before use) ─────────────────────────────────────────────
def _get_ai_client():
    """
    Return (client, provider) or (None, None) if no key configured.

    Priority: Streamlit secrets → environment variables.
    Supports: Anthropic, DeepSeek (OpenAI-compatible), OpenAI.

    DeepSeek base_url is set to https://api.deepseek.com (no /v1 suffix —
    the OpenAI SDK appends /v1 automatically, preventing /v1/v1 double-path).
    """
    import os

    # ── 1. Streamlit secrets ──────────────────────────────────────────────────
    try:
        key = st.secrets.get("ANTHROPIC_API_KEY", "").strip()
        if key and not key.startswith("your_"):
            import anthropic
            return anthropic.Anthropic(api_key=key), "anthropic"
    except Exception:
        pass

    try:
        key = st.secrets.get("DEEPSEEK_API_KEY", "").strip()
        if key and not key.startswith("your_"):
            from openai import OpenAI as _OAI
            # base_url must NOT end with /v1 — SDK adds it automatically
            return _OAI(api_key=key, base_url="https://api.deepseek.com"), "deepseek"
    except Exception:
        pass

    try:
        key = st.secrets.get("OPENAI_API_KEY", "").strip()
        if key and not key.startswith("your_"):
            from openai import OpenAI as _OAI
            return _OAI(api_key=key), "openai"
    except Exception:
        pass

    # ── 2. Environment variables ──────────────────────────────────────────────
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    deepseek_key  = os.getenv("DEEPSEEK_API_KEY", "").strip()
    openai_key    = os.getenv("OPENAI_API_KEY", "").strip()

    if anthropic_key and not anthropic_key.startswith("your_"):
        try:
            import anthropic
            return anthropic.Anthropic(api_key=anthropic_key), "anthropic"
        except Exception:
            pass

    if deepseek_key and not deepseek_key.startswith("your_"):
        try:
            from openai import OpenAI as _OAI
            return _OAI(api_key=deepseek_key, base_url="https://api.deepseek.com"), "deepseek"
        except Exception:
            pass

    if openai_key and not openai_key.startswith("your_"):
        try:
            from openai import OpenAI as _OAI
            return _OAI(api_key=openai_key), "openai"
        except Exception:
            pass

    return None, None


def _direction_selector(key_suffix: str = "") -> str:
    direction_label = st.radio(
        "翻譯方向",
        ["英文 → 繁體中文", "繁體中文 → 英文"],
        horizontal=True,
        key=f"direction_{key_suffix}",
    )
    return "en_to_tc" if "英文" in direction_label else "tc_to_en"


def _output_format_selector(key_suffix: str = "") -> str:
    return st.selectbox("輸出格式", ["PDF", "DOCX", "TXT"], key=f"output_fmt_{key_suffix}")


def _render_download_buttons(
    translated_text: str,
    source_name: str,
    direction: str,
    output_fmt: str,
    key_suffix: str,
):
    """Render the appropriate download button for translated output."""
    from utils.translator import (
        build_translated_pdf,
        build_translated_docx,
        build_translated_txt,
    )
    safe_src        = Path(source_name).stem if source_name else "翻譯"
    direction_short = "EN-TC" if direction == "en_to_tc" else "TC-EN"

    try:
        if output_fmt == "PDF":
            out_bytes = build_translated_pdf(translated_text, source_name, direction)
            st.download_button(
                label="📄 下載翻譯 PDF",
                data=out_bytes,
                file_name=f"{safe_src}-{direction_short}-翻譯.pdf",
                mime="application/pdf",
                use_container_width=True,
                type="primary",
                key=f"dl_pdf_{key_suffix}",
            )
        elif output_fmt == "DOCX":
            out_bytes = build_translated_docx(translated_text, source_name, direction)
            st.download_button(
                label="📝 下載翻譯 DOCX",
                data=out_bytes,
                file_name=f"{safe_src}-{direction_short}-翻譯.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
                type="primary",
                key=f"dl_docx_{key_suffix}",
            )
        elif output_fmt == "TXT":
            out_bytes = build_translated_txt(translated_text, source_name, direction)
            st.download_button(
                label="📃 下載翻譯 TXT",
                data=out_bytes,
                file_name=f"{safe_src}-{direction_short}-翻譯.txt",
                mime="text/plain; charset=utf-8",
                use_container_width=True,
                type="primary",
                key=f"dl_txt_{key_suffix}",
            )
    except Exception as e:
        st.error(f"輸出生成失敗：{e}")


# ══════════════════════════════════════════════════════════════════════════════
# MODE 1: Text translation
# ══════════════════════════════════════════════════════════════════════════════
if mode == "text_translate":
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<h3>🌐 文字翻譯</h3>', unsafe_allow_html=True)
    st.markdown(
        '<div class="info-box">直接輸入文字，由 Translator Agent 翻譯。適合短段落、條款、術語。</div>',
        unsafe_allow_html=True,
    )

    direction  = _direction_selector("text")
    output_fmt = _output_format_selector("text")

    input_text = st.text_area(
        "輸入原文",
        height=200,
        placeholder="請輸入需要翻譯的文字...",
        key="text_input",
    )

    if st.button("開始翻譯", type="primary", key="btn_text_translate"):
        if not input_text.strip():
            st.warning("請輸入需要翻譯的文字。")
        else:
            ai_client, ai_provider = _get_ai_client()
            if ai_client is None:
                st.error("未找到 AI API Key。請在 .env 檔案中設定 ANTHROPIC_API_KEY 或 OPENAI_API_KEY。")
            else:
                with st.spinner("Translator Agent 翻譯中..."):
                    try:
                        from utils.translator import translate_text_via_ai
                        translated = translate_text_via_ai(
                            text=input_text,
                            direction=direction,
                            ai_client=ai_client,
                            ai_provider=ai_provider,
                        )
                        st.session_state["last_translation"]           = translated
                        st.session_state["last_translation_direction"] = direction
                        st.session_state["last_translation_source"]    = "直接輸入"
                        st.session_state["last_translation_mode"]      = "text_translate"
                        st.success("翻譯完成。")
                    except Exception as e:
                        st.error(f"翻譯失敗：{e}")

    if (
        "last_translation" in st.session_state
        and st.session_state.get("last_translation_mode") == "text_translate"
    ):
        translated       = st.session_state["last_translation"]
        direction_stored = st.session_state.get("last_translation_direction", "en_to_tc")
        source_name      = st.session_state.get("last_translation_source", "直接輸入")

        st.markdown("**翻譯結果：**")
        st.text_area("翻譯結果", value=translated, height=200, key="result_display", disabled=True)
        _render_download_buttons(translated, source_name, direction_stored, output_fmt, "text")

    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# MODE 2: File translation
# ══════════════════════════════════════════════════════════════════════════════
elif mode == "file_translate":
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<h3>📄 文件翻譯</h3>', unsafe_allow_html=True)
    st.markdown(
        '<div class="info-box">上載 PDF、DOCX 或 XLSX 文件，系統抽取文字後由 Translator Agent 翻譯。</div>',
        unsafe_allow_html=True,
    )

    direction  = _direction_selector("file")
    output_fmt = _output_format_selector("file")

    uploaded = st.file_uploader(
        "上載文件（PDF / DOCX / XLSX）",
        type=["pdf", "docx", "xlsx"],
        key="file_upload_translate",
    )

    if uploaded and st.button("抽取文字並翻譯", type="primary", key="btn_file_translate"):
        file_bytes = uploaded.read()
        fname      = uploaded.name
        ext        = Path(fname).suffix.lower()

        ai_client, ai_provider = _get_ai_client()
        if ai_client is None:
            st.error(
                "未找到 AI API Key。請在 Streamlit Cloud Secrets 或 .env 檔案中設定：\n"
                "DEEPSEEK_API_KEY、ANTHROPIC_API_KEY 或 OPENAI_API_KEY。"
            )
        else:
            # ── Step 1: Extract text ──────────────────────────────────────────
            with st.spinner(f"抽取 {fname} 文字中..."):
                try:
                    from utils.translator import (
                        extract_text_from_docx,
                        extract_text_from_xlsx,
                        extract_text_from_pdf,
                        MAX_TOTAL_CHARS,
                        CHUNK_SIZE,
                    )
                    if ext == ".docx":
                        raw_text = extract_text_from_docx(file_bytes)
                    elif ext == ".xlsx":
                        raw_text = extract_text_from_xlsx(file_bytes)
                    elif ext == ".pdf":
                        raw_text = extract_text_from_pdf(file_bytes)
                    else:
                        st.error("不支援的文件格式。")
                        st.stop()

                    if not raw_text.strip():
                        st.warning("未能從文件中抽取文字。請確認文件包含可讀文字（非掃描圖片）。")
                        st.stop()

                except Exception as e:
                    st.error(f"文字抽取失敗：{e}")
                    st.stop()

            # ── Step 2: Size check & user info ────────────────────────────────
            char_count = len(raw_text)
            if char_count > MAX_TOTAL_CHARS:
                st.warning(
                    f"⚠️ 文件過大（{char_count:,} 字），超過單次上限 {MAX_TOTAL_CHARS:,} 字。"
                    f"系統將只翻譯前 {MAX_TOTAL_CHARS:,} 字。"
                    f"建議先分拆章節或只翻譯指定頁面。"
                )
            elif char_count > 20_000:
                st.info(
                    f"ℹ️ 文件共 {char_count:,} 字，將分段翻譯，預計需較長時間。請耐心等候。"
                )

            # ── Step 3: Chunk translation with progress ───────────────────────
            from utils.translator import translate_chunks_via_ai

            # Streamlit progress bar + status text
            progress_bar  = st.progress(0)
            status_text   = st.empty()

            def _on_progress(current: int, total: int, message: str):
                progress_bar.progress(current / total)
                status_text.text(message)

            try:
                result = translate_chunks_via_ai(
                    text=raw_text,
                    direction=direction,
                    ai_client=ai_client,
                    ai_provider=ai_provider,
                    progress_callback=_on_progress,
                )

                progress_bar.progress(1.0)
                status_text.empty()

                translated = result["translated"]

                # ── Summary ───────────────────────────────────────────────────
                if result["is_complete"] and not result["truncated"]:
                    st.success(
                        f"✅ 翻譯完成。共 {result['total_chunks']} 段，全部成功。"
                    )
                else:
                    msgs = []
                    if result["truncated"]:
                        msgs.append(f"文件已截至前 {MAX_TOTAL_CHARS:,} 字")
                    if result["failed_chunks"] > 0:
                        msgs.append(
                            f"成功 {result['success_chunks']} 段 / 失敗 {result['failed_chunks']} 段"
                        )
                        for fd in result["failed_details"]:
                            msgs.append(f"  • 第 {fd['chunk']} 段錯誤：{fd['error']}")
                    st.warning("⚠️ 翻譯部分完成：\n" + "\n".join(msgs))

                st.session_state["last_translation"]           = translated
                st.session_state["last_translation_direction"] = direction
                st.session_state["last_translation_source"]    = fname
                st.session_state["last_translation_mode"]      = "file_translate"

            except Exception as e:
                progress_bar.empty()
                status_text.empty()
                st.error(f"翻譯失敗：{e}")

    if (
        "last_translation" in st.session_state
        and st.session_state.get("last_translation_mode") == "file_translate"
    ):
        translated       = st.session_state["last_translation"]
        direction_stored = st.session_state.get("last_translation_direction", "en_to_tc")
        source_name      = st.session_state.get("last_translation_source", "文件")

        st.markdown("**翻譯結果預覽（前 500 字）：**")
        st.text_area(
            "預覽",
            value=translated[:500] + ("..." if len(translated) > 500 else ""),
            height=150,
            disabled=True,
            key="file_result_preview",
        )
        _render_download_buttons(translated, source_name, direction_stored, output_fmt, "file")

    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# MODE 3: Excel → PDF
# ══════════════════════════════════════════════════════════════════════════════
elif mode == "excel_to_pdf":
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<h3>🔄 Excel → PDF 轉換</h3>', unsafe_allow_html=True)
    st.markdown(
        '<div class="info-box">上載 XLSX 文件，轉換為 PDF。支援多個工作表。'
        '使用嵌入中文字型，手機及電腦均可正常顯示。</div>',
        unsafe_allow_html=True,
    )

    uploaded = st.file_uploader("上載 Excel 文件（.xlsx）", type=["xlsx"], key="excel_upload")

    if uploaded and st.button("轉換為 PDF", type="primary", key="btn_excel_pdf"):
        file_bytes = uploaded.read()
        fname      = uploaded.name
        with st.spinner(f"轉換 {fname} 中..."):
            try:
                from utils.translator import excel_to_pdf as _excel_to_pdf
                pdf_bytes = _excel_to_pdf(file_bytes, fname)
                safe_name = Path(fname).stem
                st.success("轉換完成。")
                st.download_button(
                    label="📄 下載 PDF",
                    data=pdf_bytes,
                    file_name=f"{safe_name}-轉換.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary",
                )
            except Exception as e:
                st.error(f"轉換失敗：{e}")

    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# MODE 4: DOCX → PDF
# ══════════════════════════════════════════════════════════════════════════════
elif mode == "docx_to_pdf":
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<h3>🔄 DOCX → PDF 轉換</h3>', unsafe_allow_html=True)
    st.markdown(
        '<div class="info-box">上載 Word 文件（.docx），轉換為 PDF。保留段落結構，使用嵌入中文字型。</div>',
        unsafe_allow_html=True,
    )

    uploaded = st.file_uploader("上載 Word 文件（.docx）", type=["docx"], key="docx_upload")

    if uploaded and st.button("轉換為 PDF", type="primary", key="btn_docx_pdf"):
        file_bytes = uploaded.read()
        fname      = uploaded.name
        with st.spinner(f"轉換 {fname} 中..."):
            try:
                from utils.translator import docx_to_pdf as _docx_to_pdf
                pdf_bytes = _docx_to_pdf(file_bytes, fname)
                safe_name = Path(fname).stem
                st.success("轉換完成。")
                st.download_button(
                    label="📄 下載 PDF",
                    data=pdf_bytes,
                    file_name=f"{safe_name}-轉換.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary",
                )
            except Exception as e:
                st.error(f"轉換失敗：{e}")

    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# MODE 5: Image → PowerPoint (BETA)
# ══════════════════════════════════════════════════════════════════════════════
elif mode == "image_to_pptx":
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown(
        '<h3>🖼️ 圖片 → PowerPoint <span class="beta-badge">BETA</span></h3>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="info-box">上載圖片（JPG / PNG），生成單頁 PowerPoint 文件。'
        '此功能為 Beta 版，需要安裝 python-pptx。</div>',
        unsafe_allow_html=True,
    )
    st.warning("⚠️ Beta 功能：此功能尚在測試階段，輸出格式可能不完整。")

    uploaded = st.file_uploader(
        "上載圖片（JPG / PNG）",
        type=["jpg", "jpeg", "png"],
        key="image_upload",
    )

    if uploaded and st.button("生成 PowerPoint", type="primary", key="btn_img_pptx"):
        file_bytes = uploaded.read()
        fname      = uploaded.name
        with st.spinner(f"生成 {fname} PowerPoint 中..."):
            try:
                from utils.translator import image_to_pptx_beta
                pptx_bytes = image_to_pptx_beta(file_bytes, fname)
                safe_name  = Path(fname).stem
                st.success("生成完成。")
                st.download_button(
                    label="📊 下載 PowerPoint",
                    data=pptx_bytes,
                    file_name=f"{safe_name}-圖片.pptx",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    use_container_width=True,
                    type="primary",
                )
            except RuntimeError as e:
                if "python-pptx" in str(e):
                    st.error("python-pptx 未安裝。請在 requirements.txt 加入 python-pptx 後重新部署。")
                else:
                    st.error(f"生成失敗：{e}")
            except Exception as e:
                st.error(f"生成失敗：{e}")

    st.markdown('</div>', unsafe_allow_html=True)


# ── Disclaimer ────────────────────────────────────────────────────────────────
st.markdown("""
<div class="disclaimer-box">
<strong>⚠️ 重要提示</strong><br/><br/>
本翻譯由 HK-AICOS Translator Agent（AI）生成，僅供參考及初步使用。<br/><br/>
所有涉及合約、法律、安全、技術規格之文件，必須由香港合資格專業人士最終確認翻譯準確性。<br/><br/>
Buildway Tech (HK) Limited 不對 AI 翻譯結果的準確性承擔法律責任。
</div>
""", unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center; color:#999; padding:1.5rem 0 0.5rem 0; font-size:0.82rem;">
    Buildway Tech (HK) Limited | HK-AICOS Phase 2.5G
</div>
""", unsafe_allow_html=True)
