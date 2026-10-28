"""dashboard/components/kpi.py — KPI tile renderer."""
import streamlit as st


def kpi_tile(label: str, value: str, sub: str = "", col=None) -> None:
    """Render a KPI tile.  Pass col=st.columns(...)[n] to place it."""
    html = f"""
    <div class="al-kpi">
      <div class="al-kpi-label">{label}</div>
      <div class="al-kpi-value">{value}</div>
      {"<div class='al-kpi-sub'>" + sub + "</div>" if sub else ""}
    </div>
    """
    target = col if col is not None else st
    target.markdown(html, unsafe_allow_html=True)


def stat_tile(label: str, value: str, col=None) -> None:
    """Smaller stat tile for the detail page stats row."""
    html = f"""
    <div class="al-stat">
      <div class="al-stat-label">{label}</div>
      <div class="al-stat-value">{value}</div>
    </div>
    """
    target = col if col is not None else st
    target.markdown(html, unsafe_allow_html=True)
