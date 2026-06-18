"""
utils/logo_helper.py
Logo display helper for HK-AICOS

Buildway Tech (HK) Limited
"""

import streamlit as st
from pathlib import Path

# Logo path relative to streamlit-app/
_LOGO_PATH = Path(__file__).parent.parent / "assets" / "Logo.png"


def sidebar_logo():
    """Display logo in sidebar; fallback to text brand if logo not found."""
    if _LOGO_PATH.exists():
        st.image(str(_LOGO_PATH), use_container_width=True)
    else:
        st.markdown("""
        <div style="text-align:center; padding: 1rem 0 0.5rem 0;">
            <div style="font-size:2.5rem;">🏗️</div>
            <div style="font-size:1.1rem; font-weight:700; color:white;">Buildway Tech</div>
            <div style="font-size:0.85rem; color:#c9a84c;">(HK) Limited</div>
        </div>
        """, unsafe_allow_html=True)


def get_logo_path():
    """Return logo path if exists, otherwise None."""
    return _LOGO_PATH if _LOGO_PATH.exists() else None
