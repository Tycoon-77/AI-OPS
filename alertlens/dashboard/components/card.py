"""dashboard/components/card.py — incident card renderer."""
from __future__ import annotations

import streamlit as st
from .badges import band_badge_html, action_chip_html, BAND_BORDER


def _fmt_time(ts: str) -> str:
    """Format ISO timestamp to HH:MM."""
    if not ts:
        return "—"
    try:
        return ts[11:16]  # 'HH:MM' from '2026-03-18T14:00:05Z'
    except Exception:
        return ts


def incident_card(incident: dict, key_prefix: str = "") -> bool:
    """
    Render a single incident card. Returns True if 'View details' is clicked.

    incident keys: incident_id, title, band, first_ts, last_ts, origin_service,
                   n_services, n_alerts_raw, reason_summary, status
    """
    band = incident.get("band", "YELLOW").upper()
    border_cls = BAND_BORDER.get(band, "al-card-yellow")
    status = incident.get("status", "new")

    ack_chip = ""
    if status == "acknowledged":
        ack_chip = action_chip_html("acknowledge")
    elif status == "escalated":
        ack_chip = action_chip_html("escalate")

    origin = incident.get("origin_service", "Unknown")
    n_svc = incident.get("n_services", 0)
    n_alerts = incident.get("n_alerts_raw", 0)
    first_t = _fmt_time(incident.get("first_ts", ""))
    reason = incident.get("reason_summary", "")

    card_html = f"""
    <div class="al-card {border_cls}">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
        {band_badge_html(band)}
        {ack_chip}
      </div>
      <div style="font-size:16px;font-weight:600;margin-bottom:4px;">
        {incident.get('title', 'Incident')}
      </div>
      <div style="font-size:13px;color:#9AA6C6;margin-bottom:6px;">
        Started {first_t} UTC &nbsp;·&nbsp; {n_svc} services &nbsp;·&nbsp; {n_alerts} alerts
      </div>
      <div style="font-size:13px;margin-bottom:6px;">
        Likely cause: <span class="al-mono">{origin}</span>
      </div>
      <div style="font-size:13px;color:#9AA6C6;">{reason}</div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

    # Button placed just below the card HTML
    col_btn, _ = st.columns([1, 4])
    clicked = col_btn.button(
        "View details →",
        key=f"{key_prefix}view_{incident.get('incident_id', 'unknown')}",
        type="primary",
        help="Open the incident detail page",
    )
    return clicked
