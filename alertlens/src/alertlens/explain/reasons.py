"""
Explanation generation — produce ≥ 3 plain-language reasons per cluster.

Reason kinds (BACKEND_STRUCTURE §5.10):
  time        — "{n} alerts within {minutes} min of each other."
  dependency  — "{k} of {m} services depend on {origin} ({path_example})."
  template    — "Messages describe the same symptom: {top_words}."
  shap_edge   — "Strongest link: {a} ↔ {b} (distance {d}, Δt {s}s, text sim {x:.2f})."
"""
from __future__ import annotations

import sqlite3
from datetime import datetime

import networkx as nx


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _top_words(template: str, n: int = 4) -> str:
    """Extract most meaningful words from a fingerprint template."""
    stop = {
        "<num>", "<host>", "<ip>", "<cust>", "<uuid>", "<email>",
        "on", "in", "at", "the", "a", "an", "is", "of", "to",
        "ms", "pct", "s", "min",
    }
    words = [w for w in template.lower().split() if w not in stop]
    return ", ".join(words[:n]) if words else template[:40]


def build_reasons(
    members: list[dict],
    origin_service: str,
    DG: nx.DiGraph,
    conn: sqlite3.Connection,
) -> list[dict]:
    """
    Build at least 3 reason dicts for the given cluster members.
    Each dict: {"kind": str, "text": str}
    """
    reasons: list[dict] = []

    if not members:
        return [{"kind": "time", "text": "No alerts in cluster."}]

    timestamps = [_parse_ts(m["first_ts"]) for m in members]
    first_ts   = min(timestamps)
    last_ts    = max(timestamps)
    span_min   = int((last_ts - first_ts).total_seconds() / 60) or 1
    n_alerts   = sum(m["alert_count"] for m in members)

    # ------------------------------------------------------------------
    # 1. Time reason
    # ------------------------------------------------------------------
    reasons.append({
        "kind": "time",
        "text": f"{n_alerts} alerts within {span_min} min of each other.",
    })

    # ------------------------------------------------------------------
    # 2. Dependency reason
    # ------------------------------------------------------------------
    cluster_services = {m["service_id"] for m in members}
    n_services = len(cluster_services)

    try:
        dependents_in_cluster = nx.ancestors(DG, origin_service) & cluster_services
        k = len(dependents_in_cluster)
    except nx.NodeNotFound:
        k = 0

    # Find an example dependency path to any dependent in cluster
    path_example = ""
    for dep_svc in list(dependents_in_cluster)[:1]:
        try:
            path = nx.shortest_path(DG, origin_service, dep_svc)
            path_example = " > ".join(path)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            pass

    path_str = f" ({path_example})" if path_example else ""
    reasons.append({
        "kind": "dependency",
        "text": (
            f"{k} of {n_services} services depend on {origin_service}{path_str}."
        ),
    })

    # ------------------------------------------------------------------
    # 3. Template similarity reason
    # ------------------------------------------------------------------
    fp_ids = list({m["fingerprint_id"] for m in members})
    templates: list[str] = []
    for fp_id in fp_ids[:5]:
        row = conn.execute(
            "SELECT template FROM fingerprints WHERE fingerprint_id=?", (fp_id,)
        ).fetchone()
        if row:
            templates.append(row["template"])

    if templates:
        # Find most common meaningful words across templates
        from collections import Counter
        word_counter: Counter = Counter()
        for t in templates:
            word_counter.update(_top_words(t, n=6).split(", "))
        top_words = ", ".join(w for w, _ in word_counter.most_common(4))
        reasons.append({
            "kind": "template",
            "text": f"Messages describe the same symptom: {top_words}.",
        })
    else:
        reasons.append({
            "kind": "template",
            "text": "Multiple alert types share this service cluster.",
        })

    # ------------------------------------------------------------------
    # 4. Optional: severity escalation reason
    # ------------------------------------------------------------------
    max_sev = max(m["max_severity_num"] for m in members)
    sev_names = {1: "low", 2: "medium", 3: "high", 4: "critical"}
    services_list = ", ".join(list(cluster_services)[:3])
    if max_sev >= 3:
        reasons.append({
            "kind": "severity",
            "text": (
                f"Max severity is {sev_names[max_sev]} across "
                f"{n_services} service(s): {services_list}."
            ),
        })

    return reasons
