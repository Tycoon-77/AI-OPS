"""dashboard/components/charts.py — all Plotly chart builders for AlertLens."""
from __future__ import annotations

import math
from typing import Any

import plotly.graph_objects as go

# ── Design tokens ──────────────────────────────────────────────────────────────
BG        = "#0B1020"
SURFACE   = "#121A2F"
BORDER    = "#2A3558"
TEXT      = "#E6EAF5"
MUTED     = "#9AA6C6"
ACCENT    = "#6C8CFF"
RED       = "#FF4D5E"
ORANGE    = "#FF9F43"
YELLOW    = "#F5D547"
GREY      = "#7C8AAE"
OK        = "#3DDC97"

SEV_COLOR = {"critical": RED, "high": ORANGE, "medium": YELLOW, "low": GREY}
BAND_COLOR = {"RED": RED, "ORANGE": ORANGE, "YELLOW": YELLOW, "BACKGROUND": GREY}

_PLOTLY_TEMPLATE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, system-ui, sans-serif", size=12, color=TEXT),
    xaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER),
    yaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER),
)


def _apply_template(fig: go.Figure) -> go.Figure:
    fig.update_layout(**_PLOTLY_TEMPLATE, margin=dict(l=8, r=8, t=32, b=8))
    return fig


# ── Hourly line chart ──────────────────────────────────────────────────────────

def hourly_line(hourly: list[dict]) -> go.Figure:
    """Line chart: alert volume per hour, with incident markers."""
    hours = [h["hour"][-8:-3] for h in hourly]  # HH:MM
    counts = [h["alerts"] for h in hourly]
    incident_hours = [h["hour"][-8:-3] for h in hourly if h.get("incidents_started", 0) > 0]
    incident_counts = [h["alerts"] for h in hourly if h.get("incidents_started", 0) > 0]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hours, y=counts,
        mode="lines+markers",
        line=dict(color=ACCENT, width=2),
        marker=dict(size=5, color=ACCENT),
        name="Alerts",
        hovertemplate="%{x}: %{y} alerts<extra></extra>",
    ))
    if incident_hours:
        fig.add_trace(go.Scatter(
            x=incident_hours, y=incident_counts,
            mode="markers",
            marker=dict(size=12, symbol="star", color=RED, line=dict(color="#fff", width=1)),
            name="Incident started",
            hovertemplate="%{x}: incident surfaced<extra></extra>",
        ))
    fig.update_layout(
        title=dict(text="Alert volume by hour", font=dict(size=14)),
        xaxis_title="Hour (UTC)",
        yaxis_title="Alerts",
        showlegend=True,
        legend=dict(font=dict(size=11), bgcolor="rgba(0,0,0,0)"),
        height=220,
    )
    return _apply_template(fig)


# ── Before / after bar ─────────────────────────────────────────────────────────

def before_after_bar(raw_alerts: int, surfaced_incidents: int) -> go.Figure:
    """Horizontal two-bar chart showing compression."""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[raw_alerts], y=["Raw alerts"],
        orientation="h",
        marker_color=GREY,
        text=[str(raw_alerts)],
        textposition="outside",
        hovertemplate=f"Raw: {raw_alerts}<extra></extra>",
        name="Before",
    ))
    fig.add_trace(go.Bar(
        x=[surfaced_incidents], y=["Incidents"],
        orientation="h",
        marker_color=ACCENT,
        text=[str(surfaced_incidents)],
        textposition="outside",
        hovertemplate=f"Incidents: {surfaced_incidents}<extra></extra>",
        name="After",
    ))
    fig.update_layout(
        title=dict(text="Before vs after", font=dict(size=14)),
        xaxis_title="Count",
        showlegend=False,
        height=160,
        bargap=0.4,
    )
    return _apply_template(fig)


# ── Alert timeline ─────────────────────────────────────────────────────────────

def alert_timeline(timeline: list[dict], origin_service: str = "") -> go.Figure:
    """Scatter: x=time, y=service, size=count, origin=star."""
    if not timeline:
        return go.Figure()

    services = sorted({t["service"] for t in timeline})
    svc_idx = {s: i for i, s in enumerate(services)}

    xs, ys, sizes, colors, symbols, texts = [], [], [], [], [], []
    for t in timeline:
        xs.append(t["ts"])
        ys.append(svc_idx[t["service"]])
        sizes.append(max(8, min(30, 6 + t.get("count", 1) * 1.5)))
        sev = t.get("severity", "medium")
        colors.append(RED if t["service"] == origin_service and t.get("origin_rank", 99) == 1 else SEV_COLOR.get(sev, GREY))
        symbols.append("star" if t["service"] == origin_service and t.get("origin_rank", 99) == 1 else "circle")
        texts.append(
            f"{t['service']}<br>{t['ts']}<br>{t.get('message','')}<br>×{t.get('count',1)}"
        )

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=xs, y=ys,
        mode="markers",
        marker=dict(size=sizes, color=colors, symbol=symbols,
                    line=dict(color="#fff", width=0.5)),
        text=texts,
        hovertemplate="%{text}<extra></extra>",
        name="Alerts",
    ))
    fig.update_layout(
        title=dict(text="Alert timeline (★ = probable origin)", font=dict(size=14)),
        yaxis=dict(
            tickvals=list(range(len(services))),
            ticktext=services,
            gridcolor=BORDER,
        ),
        xaxis=dict(title="Time (UTC)", type="date"),
        height=300,
    )
    return _apply_template(fig)


# ── Service map (networkx-style via Plotly) ────────────────────────────────────

def service_map(graph: dict, origin_service: str = "") -> go.Figure:
    """
    Draws the incident's service graph.
    graph = {"nodes": [{id, tier, role}], "edges": [{src, dst, on_path}]}
    """
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    if not nodes:
        return go.Figure()

    # Layout: tier on Y-axis, spread by hash on X
    pos: dict[str, tuple[float, float]] = {}
    by_tier: dict[int, list[str]] = {}
    for n in nodes:
        by_tier.setdefault(n["tier"], []).append(n["id"])

    for tier, ids in by_tier.items():
        for j, nid in enumerate(ids):
            x = (j - len(ids) / 2) * 1.5 + (hash(nid) % 100) / 300
            pos[nid] = (x, -tier)  # tier 0 (infra) at bottom

    # Edge traces
    edge_traces = []
    for e in edges:
        src, dst = e.get("src", ""), e.get("dst", "")
        if src not in pos or dst not in pos:
            continue
        x0, y0 = pos[src]
        x1, y1 = pos[dst]
        color = ACCENT if e.get("on_path") else BORDER
        edge_traces.append(go.Scatter(
            x=[x0, x1, None], y=[y0, y1, None],
            mode="lines",
            line=dict(width=1.5, color=color),
            hoverinfo="none",
            showlegend=False,
        ))

    # Node trace
    nx_list = [pos[n["id"]] for n in nodes if n["id"] in pos]
    if not nx_list:
        return go.Figure()

    node_x = [p[0] for p in nx_list]
    node_y = [p[1] for p in nx_list]
    node_colors, node_symbols, node_sizes, node_texts, node_labels = [], [], [], [], []

    for n in nodes:
        if n["id"] not in pos:
            continue
        role = n.get("role", "other")
        if role == "origin":
            node_colors.append(RED)
            node_sizes.append(22)
        elif role == "affected":
            node_colors.append(ORANGE)
            node_sizes.append(16)
        else:
            node_colors.append(GREY)
            node_sizes.append(10)
        node_symbols.append("circle")
        node_texts.append(f"{n['id']}<br>Tier {n['tier']}<br>{role}")
        node_labels.append(n["id"] if role in ("origin", "affected") else "")

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text",
        marker=dict(size=node_sizes, color=node_colors,
                    line=dict(color="#fff", width=0.8)),
        text=node_labels,
        textposition="top center",
        hovertext=node_texts,
        hovertemplate="%{hovertext}<extra></extra>",
        name="Services",
    )

    fig = go.Figure(data=[*edge_traces, node_trace])
    fig.update_layout(
        title=dict(text="Service map (🔴 origin · 🟠 affected · ⬜ other)", font=dict(size=14)),
        showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False,
                   tickvals=list(range(-3, 1)),
                   ticktext=["Tier 3 (Edge)", "Tier 2 (Business)", "Tier 1 (Platform)", "Tier 0 (Infra)"]),
        height=340,
    )
    return _apply_template(fig)


# ── Noise bar chart ────────────────────────────────────────────────────────────

def noise_bar(candidates: list[dict]) -> go.Figure:
    top = sorted(candidates, key=lambda c: c.get("volume", 0), reverse=True)[:10]
    labels = [f"{c.get('template','?')[:30]}…" if len(c.get("template","")) > 30 else c.get("template","?") for c in top]
    volumes = [c.get("volume", 0) for c in top]
    colors = [GREY if c.get("incident_involvement", 0) > 0 else RED for c in top]

    fig = go.Figure(go.Bar(
        x=volumes, y=labels,
        orientation="h",
        marker_color=colors,
        text=[str(v) for v in volumes],
        textposition="outside",
        hovertemplate="%{y}: %{x} fires<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="Top 10 noise candidates by volume (red = zero incident involvement)", font=dict(size=14)),
        xaxis_title="Fires (training period)",
        yaxis=dict(autorange="reversed"),
        height=max(250, 30 * len(top) + 80),
    )
    return _apply_template(fig)


# ── Scorecard charts ───────────────────────────────────────────────────────────

def scorecard_comparison(metrics: dict) -> go.Figure:
    """Learned vs baseline bar comparison."""
    categories = ["Compression", "Recall", "Pairwise P", "B-cubed F1", "Origin Top-1"]
    learned_keys = ["compression_ratio", "recall", "pairwise_precision", "bcubed_f1", "origin_top1"]
    baseline_keys = [f"baseline_{k}" for k in learned_keys]

    learned = [metrics.get(k, 0) for k in learned_keys]
    baseline = [metrics.get(k, 0) for k in baseline_keys]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Baseline (rules)", x=categories, y=baseline, marker_color=GREY))
    fig.add_trace(go.Bar(name="Learned (LightGBM)", x=categories, y=learned, marker_color=ACCENT))
    fig.update_layout(
        barmode="group",
        title=dict(text="Learned vs baseline", font=dict(size=14)),
        yaxis_title="Score",
        height=280,
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    return _apply_template(fig)
