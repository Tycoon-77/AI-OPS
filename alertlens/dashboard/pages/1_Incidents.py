"""dashboard/pages/1_Incidents.py — Incidents page (home) for AlertLens."""
from __future__ import annotations

import time
from datetime import date

import streamlit as st

# ── page config (must be first st call) ──────────────────────────────────────
st.set_page_config(
    page_title="Incidents — AlertLens",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── local imports ─────────────────────────────────────────────────────────────
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from theme import apply_theme, simulated_data_tag
from components import api, badges, kpi, charts, card as card_mod

# ── theme ─────────────────────────────────────────────────────────────────────
apply_theme()

# ── session-state defaults ────────────────────────────────────────────────────
if "al_day" not in st.session_state:
    st.session_state["al_day"] = "2026-03-18"
if "al_redact" not in st.session_state:
    st.session_state["al_redact"] = True
if "al_replay_running" not in st.session_state:
    st.session_state["al_replay_running"] = False
if "al_replay_idx" not in st.session_state:
    st.session_state["al_replay_idx"] = 0
if "al_replay_speed" not in st.session_state:
    st.session_state["al_replay_speed"] = 10
if "al_replay_events" not in st.session_state:
    st.session_state["al_replay_events"] = []
if "al_band_filter" not in st.session_state:
    st.session_state["al_band_filter"] = "All"

# ── sidebar ───────────────────────────────────────────────────────────────────
simulated_data_tag()
st.sidebar.markdown("---")
st.sidebar.header("🔍 AlertLens")

# Date picker
days_data = api.get_days()
day_options = [d["day"] for d in days_data] if days_data else ["2026-03-18"]
selected_day = st.sidebar.selectbox(
    "📅 Date",
    options=day_options,
    index=day_options.index(st.session_state["al_day"]) if st.session_state["al_day"] in day_options else 0,
    key="_sidebar_day",
)
st.session_state["al_day"] = selected_day

# Redact toggle
is_demo = api.is_demo_mode()
redact = st.sidebar.toggle(
    "🔒 Redact sensitive values",
    value=st.session_state["al_redact"],
    disabled=is_demo,
    key="_sidebar_redact",
    help="Always ON in demo mode" if is_demo else "Mask hostnames, IPs, customer IDs",
)
st.session_state["al_redact"] = True if is_demo else redact

# Band filter
band_filter = st.sidebar.radio(
    "Filter by band",
    options=["All", "RED", "ORANGE", "YELLOW"],
    index=["All", "RED", "ORANGE", "YELLOW"].index(st.session_state["al_band_filter"]),
    key="_sidebar_band",
)
st.session_state["al_band_filter"] = band_filter

st.sidebar.markdown("---")
st.sidebar.caption("AlertLens v1.0 · Hackathon MVP")

# ── main content ──────────────────────────────────────────────────────────────
day = st.session_state["al_day"]

# Fetch data
with st.spinner("Loading incidents…"):
    summary = api.get_summary(day)
    band_arg = None if band_filter == "All" else band_filter
    incidents = api.get_incidents(day, band=band_arg)
    background = api.get_incidents(day, include_background=True)
    background = [i for i in background if i.get("band") == "BACKGROUND"]

raw_alerts = summary.get("raw_alerts", 0)
surfaced = summary.get("surfaced_incidents", len(incidents))
reduction = summary.get("reduction_pct", 0.0)
hourly = summary.get("hourly", [])

# ── KPI strip ─────────────────────────────────────────────────────────────────
st.markdown(f"## 🚨 Incidents — {day}")
k1, k2, k3 = st.columns(3)
kpi.kpi_tile("Raw alerts", str(raw_alerts), f"on {day}", col=k1)
kpi.kpi_tile(
    "Incidents surfaced",
    f"{raw_alerts} → {surfaced}",
    f"{len(incidents)} shown, {summary.get('background_clusters',0)} in background",
    col=k2,
)
kpi.kpi_tile("Reduction", f"{reduction:.1f}%", "signal ÷ noise", col=k3)

st.markdown("---")

# ── Charts row ────────────────────────────────────────────────────────────────
if hourly:
    col_line, col_bar = st.columns([6, 4])
    with col_line:
        fig_line = charts.hourly_line(hourly)
        st.plotly_chart(fig_line, use_container_width=True, config={"displayModeBar": False})
        st.caption(f"{surfaced} incidents surfaced; largest began at {hourly[0]['hour'][11:16]} UTC")
    with col_bar:
        fig_bar = charts.before_after_bar(raw_alerts, surfaced)
        st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})
        st.caption(f"{reduction:.1f}% reduction — from {raw_alerts} alerts to {surfaced} incidents")

# ── Replay bar ────────────────────────────────────────────────────────────────
st.markdown("#### ▶ Replay")
with st.container():
    rcol1, rcol2, rcol3, rcol4, rcol5 = st.columns([1, 1, 1, 2, 3])

    play_btn = rcol1.button(
        "▶ Play" if not st.session_state["al_replay_running"] else "⏸ Pause",
        key="replay_play",
        type="primary" if not st.session_state["al_replay_running"] else "secondary",
    )
    reset_btn = rcol2.button("↺ Reset", key="replay_reset")
    speed = rcol3.selectbox(
        "Speed",
        options=[10, 60, 300],
        format_func=lambda x: f"{x}×",
        key="replay_speed_select",
        label_visibility="collapsed",
    )
    st.session_state["al_replay_speed"] = speed

    # Replay clock display
    replay_placeholder = rcol4.empty()
    if st.session_state["al_replay_running"]:
        idx = st.session_state["al_replay_idx"]
        events = st.session_state["al_replay_events"]
        if events and idx < len(events):
            t = events[idx].get("t", "")[:19].replace("T", " ")
        else:
            t = "—"
        replay_placeholder.markdown(
            f'<span class="al-replay-chip">▶ REPLAY · {t} · {speed}×</span>',
            unsafe_allow_html=True,
        )

    if play_btn:
        if not st.session_state["al_replay_running"]:
            # Start: load events
            st.session_state["al_replay_running"] = True
            if not st.session_state["al_replay_events"]:
                replay_data = api.get_replay(day)
                st.session_state["al_replay_events"] = replay_data.get("events", [])
                st.session_state["al_replay_idx"] = 0
        else:
            # Pause
            st.session_state["al_replay_running"] = False

    if reset_btn:
        st.session_state["al_replay_running"] = False
        st.session_state["al_replay_idx"] = 0
        st.session_state["al_replay_events"] = []

st.markdown("---")

# ── Incident cards ────────────────────────────────────────────────────────────
# During replay, only show incidents surfaced so far
def _incidents_for_display() -> list[dict]:
    if not st.session_state["al_replay_running"] and st.session_state["al_replay_idx"] == 0:
        return incidents

    events = st.session_state["al_replay_events"]
    idx = st.session_state["al_replay_idx"]
    surfaced_ids = {
        e["incident_id"]
        for e in events[:idx]
        if e.get("type") == "incident_surfaced"
    }
    return [i for i in incidents if i["incident_id"] in surfaced_ids]

displayed = _incidents_for_display()

if not displayed:
    if st.session_state["al_replay_running"]:
        raw_so_far = sum(
            e.get("raw_total", 0)
            for e in st.session_state["al_replay_events"][: st.session_state["al_replay_idx"]]
            if e.get("type") == "alert"
        )
        st.info(f"⏳ Replay in progress — {raw_so_far} raw alerts processed, no incidents surfaced yet.")
    else:
        st.info("✅ No incidents need attention right now.")
        if background:
            st.caption(f"→ {len(background)} clusters in Background")
else:
    # Replay counter
    if st.session_state["al_replay_running"]:
        events = st.session_state["al_replay_events"]
        idx = st.session_state["al_replay_idx"]
        raw_so_far = next(
            (e.get("raw_total", 0) for e in reversed(events[:idx]) if e.get("type") == "alert"),
            0,
        )
        st.markdown(
            f'<span class="al-replay-chip">Raw alerts: {raw_so_far} &nbsp;→&nbsp; Incidents: {len(displayed)}</span>',
            unsafe_allow_html=True,
        )
        st.markdown("")

    for inc in displayed:
        clicked = card_mod.incident_card(inc, key_prefix=f"{day}_")
        if clicked:
            st.session_state["al_nav_incident_id"] = inc["incident_id"]
            st.switch_page("pages/2_Incident_Detail.py")

# ── Background expander ───────────────────────────────────────────────────────
if background:
    with st.expander(f"Background ({len(background)} clusters — low priority, not surfaced)"):
        for inc in background:
            card_mod.incident_card(inc, key_prefix="bg_")

# ── Replay auto-advance ───────────────────────────────────────────────────────
if st.session_state["al_replay_running"]:
    events = st.session_state["al_replay_events"]
    idx = st.session_state["al_replay_idx"]
    if idx < len(events):
        # Advance by a few steps per tick (batch for performance)
        advance = max(1, speed // 10)
        st.session_state["al_replay_idx"] = min(idx + advance, len(events))
        time.sleep(0.25)
        st.rerun()
    else:
        st.session_state["al_replay_running"] = False
        raw_total = summary.get("raw_alerts", raw_alerts)
        st.success(f"✅ Day complete: {raw_total} → {surfaced} incidents")
