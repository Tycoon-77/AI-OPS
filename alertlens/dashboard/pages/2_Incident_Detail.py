"""dashboard/pages/2_Incident_Detail.py — full incident detail view."""
from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="Incident Detail — AlertLens",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from theme import apply_theme, simulated_data_tag
from components import api, badges, kpi, charts

apply_theme()

# ── sidebar ───────────────────────────────────────────────────────────────────
simulated_data_tag()
st.sidebar.header("🔍 AlertLens")
if st.sidebar.button("← Back to Incidents"):
    st.switch_page("pages/1_Incidents.py")
st.sidebar.markdown("---")
st.sidebar.caption("AlertLens v1.0 · Hackathon MVP")

# ── get incident id ───────────────────────────────────────────────────────────
# Accept from query params OR from session state (card click)
params = st.query_params
incident_id = params.get("incident_id", "") or st.session_state.get("al_nav_incident_id", "")

if not incident_id:
    st.warning("No incident selected. Please click **View details** from the Incidents page.")
    if st.button("← Go to Incidents"):
        st.switch_page("pages/1_Incidents.py")
    st.stop()

# ── fetch detail ──────────────────────────────────────────────────────────────
with st.spinner("Loading incident…"):
    detail = api.get_incident(incident_id)

if not detail:
    st.error(f"Incident `{incident_id}` not found.")
    if st.button("← Go to Incidents"):
        st.switch_page("pages/1_Incidents.py")
    st.stop()

# ── extract fields ────────────────────────────────────────────────────────────
band    = detail.get("band", "YELLOW").upper()
title   = detail.get("title", "Incident")
origin  = detail.get("origin", {})
stats   = detail.get("stats", {})
timeline_data = detail.get("timeline", [])
graph_data    = detail.get("graph", {})
reasons       = detail.get("reasons", [])
actions_log   = detail.get("actions", [])
strong_edges  = detail.get("strong_edges", [])

origin_service = origin.get("service", "")

# Already-acknowledged?
last_action = actions_log[-1]["action_type"] if actions_log else None

def _fmt(ts: str) -> str:
    return ts[:19].replace("T", " ") + " UTC" if ts else "—"

# ── title row ─────────────────────────────────────────────────────────────────
band_html = badges.band_badge_html(band)
st.markdown(
    f"""
    <div style="display:flex;align-items:center;gap:14px;margin-bottom:8px;">
        {band_html}
        <span style="font-size:24px;font-weight:700;">{title}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# Breadcrumb
st.caption(f"Incident ID: `{incident_id}` · Priority: {detail.get('priority_score', 0):.2f}")

st.markdown("---")

# ── stats row ─────────────────────────────────────────────────────────────────
s1, s2, s3, s4, s5 = st.columns(5)
kpi.stat_tile("First seen",       _fmt(stats.get("first_ts", "")),           col=s1)
kpi.stat_tile("Last seen",        _fmt(stats.get("last_ts", "")),             col=s2)
kpi.stat_tile("Raw alerts",       str(stats.get("n_alerts_raw", "—")),       col=s3)
kpi.stat_tile("Services",         str(stats.get("n_services", "—")),         col=s4)
kpi.stat_tile("Blast radius",     str(stats.get("blast_radius", "—")),       col=s5)

st.markdown("---")

# ── timeline + service map ────────────────────────────────────────────────────
col_tl, col_map = st.columns(2)

with col_tl:
    st.markdown("#### Alert Timeline")
    fig_tl = charts.alert_timeline(timeline_data, origin_service=origin_service)
    st.plotly_chart(fig_tl, use_container_width=True, config={"displayModeBar": False})
    st.caption(f"★ = probable origin ({origin_service})")

with col_map:
    st.markdown("#### Service Map")
    fig_map = charts.service_map(graph_data, origin_service=origin_service)
    st.plotly_chart(fig_map, use_container_width=True, config={"displayModeBar": False})
    st.caption("🔴 origin · 🟠 affected · ⬜ other · highlighted edges = dependency path")

st.markdown("---")

# ── why grouped panel ─────────────────────────────────────────────────────────
st.markdown("#### Why These Were Grouped")
REASON_ICONS = {"time": "⏱", "dependency": "🔗", "template": "📝"}
if reasons:
    with st.container():
        for r in reasons:
            # r might be a dict {kind, text} or plain string
            if isinstance(r, dict):
                kind = r.get("kind", "")
                text = r.get("text", "")
                icon = REASON_ICONS.get(kind, "•")
            else:
                text = str(r)
                icon = "•"
            st.markdown(
                f'<div class="al-why-reason"><span class="icon">{icon}</span><span>{text}</span></div>',
                unsafe_allow_html=True,
            )
else:
    st.info("No reasons available yet.")

# Weak-link note
weak_edges = [e for e in strong_edges if e.get("weak")]
if weak_edges:
    st.markdown(
        '<span class="al-badge al-badge-yellow">⚠ WEAK LINK</span> '
        f'This cluster has {len(weak_edges)} weak edge(s) — grouping confidence is lower.',
        unsafe_allow_html=True,
    )

st.markdown("---")

# ── alerts table ──────────────────────────────────────────────────────────────
st.markdown("#### Alerts")
if timeline_data:
    # Pagination
    PAGE_SIZE = 50
    total = len(timeline_data)
    max_page = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = st.number_input("Page", min_value=1, max_value=max_page, value=1, step=1, key="al_alert_page")
    start = (page - 1) * PAGE_SIZE
    page_items = timeline_data[start: start + PAGE_SIZE]

    import pandas as pd
    df = pd.DataFrame([{
        "Time":     item.get("ts", "")[:19].replace("T", " "),
        "Service":  item.get("service", ""),
        "Source":   item.get("source", ""),
        "Severity": item.get("severity", ""),
        "Message":  item.get("message", ""),
        "Count":    item.get("count", 1),
    } for item in page_items])
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption(f"Showing {start + 1}–{min(start + PAGE_SIZE, total)} of {total} alerts")
else:
    st.info("No alert detail available.")

st.markdown("---")

# ── action buttons ────────────────────────────────────────────────────────────
st.markdown("#### Actions")
st.info("💡 Actions are recorded locally only. No live monitoring system is changed.")

note = st.text_area(
    "Optional note (≤ 500 chars)",
    max_chars=500,
    key="al_action_note",
    placeholder="Add context before acknowledging or escalating…",
)

acol1, acol2, _ = st.columns([2, 2, 6])

ack_label = "✓ Acknowledged" if last_action == "acknowledge" else "Acknowledge"
esc_label = "⬆ Escalated"   if last_action == "escalate"   else "Escalate"

with acol1:
    ack_disabled = last_action == "acknowledge"
    if st.button(
        ack_label,
        disabled=ack_disabled,
        key="al_btn_ack",
        help="Recorded only. No live system is changed.",
        use_container_width=True,
    ):
        result = api.post_action("incident", incident_id, "acknowledge", note or None)
        if result:
            st.toast("✅ Acknowledged. Recorded only — no live system was changed.", icon="✅")
            api.get_incident.clear()  # bust cache
            st.rerun()
        else:
            st.error("Failed to record action. Please retry.")

with acol2:
    if st.button(
        esc_label,
        key="al_btn_esc",
        help="Recorded only. No live system is changed.",
        use_container_width=True,
        type="secondary" if last_action != "escalate" else "secondary",
    ):
        result = api.post_action("incident", incident_id, "escalate", note or None)
        if result:
            st.toast("⬆ Escalated. Recorded only — no live system was changed.", icon="⬆")
            api.get_incident.clear()
            st.rerun()
        else:
            st.error("Failed to record action. Please retry.")

# Action history
if actions_log:
    st.markdown("**Action history:**")
    for a in actions_log:
        ts = _fmt(a.get("ts", ""))
        atype = a.get("action_type", "").upper()
        n = a.get("note", "")
        st.markdown(f"- `{atype}` at {ts}" + (f" — {n}" if n else ""))
