"""dashboard/pages/3_Noise_Candidates.py — noise rule suggestions."""
from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="Noise Candidates — AlertLens",
    page_icon="🔇",
    layout="wide",
    initial_sidebar_state="expanded",
)

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from theme import apply_theme, simulated_data_tag
from components import api, charts

apply_theme()

simulated_data_tag()
st.sidebar.header("🔍 AlertLens")
if st.sidebar.button("← Back to Incidents"):
    st.switch_page("pages/1_Incidents.py")
st.sidebar.markdown("---")
st.sidebar.caption("AlertLens v1.0 · Hackathon MVP")

# ── page ──────────────────────────────────────────────────────────────────────
st.markdown("## 🔇 Noise Candidates")

# Mandatory info banner
st.markdown(
    """
    <div style="background:#1a1a2e;border:1px solid #4DB6FF;border-radius:8px;padding:10px 16px;
                font-size:13px;color:#4DB6FF;margin-bottom:16px;">
    ℹ️ <strong>Suggestions only</strong> — nothing is changed automatically.
    Approve or Ignore records your decision. Apply changes in your monitoring tool.
    </div>
    """,
    unsafe_allow_html=True,
)

sort_by = st.selectbox("Sort by", ["volume", "precursor_rate"], key="al_noise_sort")

with st.spinner("Loading noise candidates…"):
    candidates = api.get_noise_candidates(sort=sort_by)

if not candidates:
    st.info("No noise candidates found. Run the pipeline first.")
    st.stop()

# ── bar chart ─────────────────────────────────────────────────────────────────
fig_noise = charts.noise_bar(candidates)
st.plotly_chart(fig_noise, use_container_width=True, config={"displayModeBar": False})
st.caption("Red bars = zero incident involvement. Grey = has preceded incidents (marked 'Keep').")

st.markdown("---")
st.markdown("#### Candidate Rules")

# ── table + action buttons ────────────────────────────────────────────────────
REC_LABELS = {
    "raise_threshold":    "📈 Raise threshold",
    "merge_rule":         "🔀 Merge rule",
    "downgrade_severity": "⬇ Downgrade severity",
    "require_consecutive": "🔁 Require consecutive",
    "keep":               "🔒 Keep",
}

for i, c in enumerate(candidates):
    is_keep = c.get("recommendation_type") == "keep" or c.get("incident_involvement", 0) > 0

    with st.expander(
        f"{'🔒' if is_keep else '⚠'} {c.get('template', '—')[:60]} "
        f"— {c.get('service', 'all')} — {c.get('volume', 0)} fires",
        expanded=(i < 3),
    ):
        col_info, col_action = st.columns([3, 1])

        with col_info:
            st.markdown(f"**Fingerprint:** `{c.get('fingerprint_id','—')}`")
            st.markdown(f"**Service:** `{c.get('service','—')}`")
            st.markdown(f"**Volume:** {c.get('volume',0)} fires (training period)")
            st.markdown(f"**Incident involvement:** {c.get('incident_involvement',0)}")
            prec_rate = c.get('precursor_rate', 0)
            st.markdown(f"**Precursor rate:** {prec_rate:.1%}")
            rec_type = c.get("recommendation_type", "")
            st.markdown(f"**Recommendation:** {REC_LABELS.get(rec_type, rec_type)}")
            st.markdown(f"**Evidence:** {c.get('recommendation_text','—')}")

            # Evidence JSON
            ev = c.get("evidence", {})
            if ev:
                with st.container():
                    st.caption(f"Evidence detail: {ev}")

            # Status chip
            status = c.get("status", "new")
            if status == "approved":
                st.markdown(
                    '<span class="al-badge al-badge-ok">✓ Approved (recorded)</span>',
                    unsafe_allow_html=True,
                )
            elif status == "ignored":
                st.markdown(
                    '<span class="al-badge al-badge-bg">— Ignored (recorded)</span>',
                    unsafe_allow_html=True,
                )
            elif is_keep:
                st.markdown(
                    '<span class="al-badge al-badge-yellow">🔒 KEEP – has preceded incidents</span>',
                    unsafe_allow_html=True,
                )

        with col_action:
            fp_id = c.get("fingerprint_id", f"fp_{i}")
            svc   = c.get("service", "")
            target_id = f"{fp_id}::{svc}" if svc else fp_id

            approve_disabled = is_keep or status == "approved"
            ignore_disabled  = status == "ignored"

            if st.button(
                "✓ Approve",
                key=f"al_approve_{i}",
                disabled=approve_disabled,
                help="Recorded only. No live system is changed.",
                use_container_width=True,
                type="primary",
            ):
                result = api.post_action("noise_candidate", target_id, "approve")
                if result:
                    st.toast(
                        f"✅ Approved — recorded. Apply the change in your monitoring tool.",
                        icon="✅",
                    )
                    api.get_noise_candidates.clear()
                    st.rerun()
                else:
                    st.error("Failed to record. Please retry.")

            st.markdown("")

            if st.button(
                "✗ Ignore",
                key=f"al_ignore_{i}",
                disabled=ignore_disabled,
                help="Recorded only. No live system is changed.",
                use_container_width=True,
            ):
                result = api.post_action("noise_candidate", target_id, "ignore")
                if result:
                    st.toast("— Ignored — recorded.", icon="ℹ️")
                    api.get_noise_candidates.clear()
                    st.rerun()
                else:
                    st.error("Failed to record. Please retry.")
