"""dashboard/theme.py — inject CSS once per page load."""
from pathlib import Path
import streamlit as st

_CSS_PATH = Path(__file__).parent / "assets" / "style.css"


def apply_theme() -> None:
    """Call once at the top of every page to apply the AlertLens dark theme."""
    css = _CSS_PATH.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def simulated_data_tag() -> None:
    """Render the mandatory SIMULATED DATA banner in the sidebar."""
    st.sidebar.markdown(
        '<div class="al-sim-banner">⚠ SIMULATED DATA</div>',
        unsafe_allow_html=True,
    )
