"""dashboard/app.py — AlertLens entry point (redirects to Incidents page)."""
import streamlit as st

st.set_page_config(
    page_title="AlertLens",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.switch_page("pages/1_Incidents.py")
