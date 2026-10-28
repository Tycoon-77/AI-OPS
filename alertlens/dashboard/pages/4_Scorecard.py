"""dashboard/pages/4_Scorecard.py — metrics scorecard."""
from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="Scorecard — AlertLens",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from theme import apply_theme, simulated_data_tag
from components import api, kpi, charts

apply_theme()

simulated_data_tag()
st.sidebar.header("🔍 AlertLens")
if st.sidebar.button("← Back to Incidents"):
    st.switch_page("pages/1_Incidents.py")
st.sidebar.markdown("---")
st.sidebar.caption("AlertLens v1.0 · Hackathon MVP")

# ── page ──────────────────────────────────────────────────────────────────────
st.markdown("## 📊 Scorecard")

# Persistent simulated data banner
st.markdown(
    """
    <div style="background:#1a1a2e;border:1px solid #F5D547;border-radius:8px;padding:10px 16px;
                font-size:13px;color:#F5D547;margin-bottom:16px;text-align:center;font-weight:600;">
    ⚠ ALL METRICS BELOW ARE ON SIMULATED DATA — NOT FROM PRODUCTION
    </div>
    """,
    unsafe_allow_html=True,
)

with st.spinner("Loading metrics…"):
    metrics = api.get_metrics()

if not metrics:
    st.warning("No metrics available yet. Run the full pipeline first:")
    st.code("make pipeline", language="bash")
    # Show placeholder tiles so the page is still useful in demo
    metrics = {
        "compression_ratio": 122.4,
        "recall": 1.0,
        "median_time_to_surface_s": 87,
        "pairwise_precision": 0.94,
        "pairwise_recall": 0.88,
        "bcubed_f1": 0.91,
        "origin_top1": 0.79,
        "origin_top3": 0.93,
        "heldout_recall": 0.92,
        "buried_recall": 1.0,
        "explainability_pct": 1.0,
        "baseline_compression_ratio": 11.2,
        "baseline_recall": 0.83,
        "baseline_pairwise_precision": 0.71,
        "baseline_bcubed_f1": 0.74,
        "baseline_origin_top1": 0.55,
    }
    st.info("Showing placeholder demo values — replace by running `make pipeline`.")

# ── KPI tiles ─────────────────────────────────────────────────────────────────
t1, t2, t3, t4, t5 = st.columns(5)

compression = metrics.get("compression_ratio", 0)
recall = metrics.get("recall", 0)
tts = metrics.get("median_time_to_surface_s", 0)
pprecision = metrics.get("pairwise_precision", 0)
bcubed = metrics.get("bcubed_f1", 0)

kpi.kpi_tile("Compression", f"{compression:.0f}×",
             "target ≥ 50×  ✓" if compression >= 50 else "target ≥ 50×", col=t1)
kpi.kpi_tile("Recall", f"{recall:.0%}",
             "target 100%  ✓" if recall >= 1.0 else f"target 100% — {(1.0-recall):.0%} missed", col=t2)
kpi.kpi_tile("Time-to-surface", f"{tts}s",
             "target ≤ 120 s  ✓" if tts <= 120 else "target ≤ 120 s", col=t3)
kpi.kpi_tile("Pairwise P", f"{pprecision:.2f}",
             "target ≥ 0.90  ✓" if pprecision >= 0.90 else "target ≥ 0.90", col=t4)
kpi.kpi_tile("B-cubed F1", f"{bcubed:.2f}",
             "target ≥ 0.85  ✓" if bcubed >= 0.85 else "target ≥ 0.85", col=t5)

st.markdown("---")

# ── Learned vs baseline ───────────────────────────────────────────────────────
col_chart, col_table = st.columns([6, 4])

with col_chart:
    st.markdown("#### Learned vs Baseline")
    fig_cmp = charts.scorecard_comparison(metrics)
    st.plotly_chart(fig_cmp, use_container_width=True, config={"displayModeBar": False})
    st.caption("LightGBM (trained weeks 1–2) vs rules-only baseline (time gap ≤ 5 min, graph dist ≤ 2)")

with col_table:
    st.markdown("#### Additional Metrics")
    import pandas as pd
    extra = [
        ("Origin top-1",      f"{metrics.get('origin_top1', 0):.0%}", "≥ 75%"),
        ("Origin top-3",      f"{metrics.get('origin_top3', 0):.0%}", "≥ 90%"),
        ("Held-out recall",   f"{metrics.get('heldout_recall', 0):.0%}", "≥ 90%  (cert-expiry)"),
        ("Buried recall",     f"{metrics.get('buried_recall', 0):.0%}", "100%"),
        ("Explainability",    f"{metrics.get('explainability_pct', 0):.0%}", "100%"),
        ("Pairwise recall",   f"{metrics.get('pairwise_recall', 0):.2f}", "≥ 0.80"),
    ]
    df_extra = pd.DataFrame(extra, columns=["Metric", "Value", "Target"])
    st.dataframe(df_extra, use_container_width=True, hide_index=True)

st.markdown("---")

# ── Failure modes ─────────────────────────────────────────────────────────────
st.markdown("#### Known Failure Modes")
st.markdown(
    """
    | Failure mode | Description | Mitigation |
    |---|---|---|
    | Synthetic circularity | Model learns simulator's own rules | Randomised propagation, missing hops, noise overlap, held-out type, explicit disclosure |
    | Wide-blast incidents | DNS failure creates giant clusters | Louvain split + max cluster size guard (150 groups) |
    | Over-compression | Low-priority cluster hides buried incident | Safety net: `n_services ≥ 4` always surfaces |
    | Novel incident types | Cert-expiry has `history_match = 0` | Time + dependency features still catch it |
    | Threshold drift | Thresholds tuned on weeks 1–2 | Calibrated on validation; reported on test week |
    """,
    unsafe_allow_html=False,
)

st.markdown("---")
st.caption(
    "All results are on **simulated data** generated by `alertlens.simulator` (seed=42). "
    "Results would differ on production data. See README for full methodology."
)
