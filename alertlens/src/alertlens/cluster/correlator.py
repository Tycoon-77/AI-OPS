"""
Rules-baseline correlator and (later) ML-scored incremental correlator.

Phase 2 (now): pure rules — connect two alert groups if:
    time_gap <= PAIR_WINDOW_MIN  AND  graph_dist <= 2

Phase 4 extension: swap in LightGBM pair scores above PAIR_THRESHOLD.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Generator

from alertlens.cluster.graph_utils import build_undirected_graph, graph_dist
from alertlens.cluster.origin import rank_origins
from alertlens.cluster.priority import get_band, priority_score, should_surface
from alertlens.cluster.history import history_match_score
from alertlens.explain.reasons import build_reasons
from alertlens.config import settings


# ---------------------------------------------------------------------------
# Union-Find
# ---------------------------------------------------------------------------

class UnionFind:
    def __init__(self) -> None:
        self._parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        self._parent.setdefault(x, x)
        if self._parent[x] != x:
            self._parent[x] = self.find(self._parent[x])
        return self._parent[x]

    def union(self, x: str, y: str) -> None:
        self._parent[self.find(x)] = self.find(y)

    def clusters(self, members: list[str]) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {}
        for m in members:
            root = self.find(m)
            result.setdefault(root, []).append(m)
        return result


# ---------------------------------------------------------------------------
# Rules baseline
# ---------------------------------------------------------------------------

def run_rules_baseline(
    conn: sqlite3.Connection,
    run_id: str,
    split: str = "all",
    pair_window_min: int | None = None,
    graph_dist_threshold: int = 2,
) -> None:
    """
    Build incident clusters using pure rules (no ML).
    Writes results into incidents_pred + incident_members.
    """
    pair_window = pair_window_min or settings.pair_window_min
    window_td   = timedelta(minutes=pair_window)

    # Load all groups (sorted by first_ts)
    if split and split != "all":
        rows = conn.execute(
            """SELECT group_id, fingerprint_id, service_id, source,
                      first_ts, last_ts, alert_count, max_severity_num, split, truth_incident_id
               FROM alert_groups
               WHERE split = ?
               ORDER BY first_ts""",
            (split,),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT group_id, fingerprint_id, service_id, source,
                      first_ts, last_ts, alert_count, max_severity_num, split, truth_incident_id
               FROM alert_groups
               ORDER BY first_ts"""
        ).fetchall()

    if not rows:
        print(f"[correlator] No groups for split={split}")
        return

    groups = [dict(r) for r in rows]
    UG = build_undirected_graph(conn)
    DG_directed = None  # lazy-loaded in origin step

    # -----------------------------------------------------------------------
    # Build edges via rules
    # -----------------------------------------------------------------------
    uf = UnionFind()
    # Ensure every group is in the UF
    for g in groups:
        uf.find(g["group_id"])

    for i, b in enumerate(groups):
        b_ts = _parse_ts(b["first_ts"])
        # Walk backwards; stop when gap exceeds window
        for a in reversed(groups[:i]):
            a_ts = _parse_ts(a["first_ts"])
            if b_ts - a_ts > window_td:
                break
            dist = graph_dist(UG, a["service_id"], b["service_id"])
            if dist <= graph_dist_threshold:
                uf.union(a["group_id"], b["group_id"])

    # -----------------------------------------------------------------------
    # Build cluster dicts
    # -----------------------------------------------------------------------
    cluster_map = uf.clusters([g["group_id"] for g in groups])
    group_by_id = {g["group_id"]: g for g in groups}

    # Load training incidents for history matching
    train_incidents = _load_train_incidents(conn)

    # -----------------------------------------------------------------------
    # For each cluster → compute stats, origin, priority, write to DB
    # -----------------------------------------------------------------------
    incident_rows: list[dict]  = []
    member_rows:   list[dict]  = []
    inc_counter = 0

    # Load directed graph for origin ranking
    from alertlens.cluster.graph_utils import build_directed_graph
    DG = build_directed_graph(conn)

    for root, member_ids in cluster_map.items():
        inc_counter += 1
        inc_id = f"inc_{run_id}_{inc_counter:04d}"

        members = [group_by_id[gid] for gid in member_ids]
        members_sorted = sorted(members, key=lambda g: g["first_ts"])

        # Aggregate stats
        first_ts      = members_sorted[0]["first_ts"]
        last_ts       = members_sorted[-1]["last_ts"]
        day           = first_ts[:10]
        n_groups      = len(members)
        n_alerts_raw  = sum(m["alert_count"] for m in members)
        services      = list({m["service_id"] for m in members})
        n_services    = len(services)
        max_sev_num   = max(m["max_severity_num"] for m in members)

        # Origin ranking
        ranked = rank_origins(members, DG, n_services)

        origin_group  = ranked[0] if ranked else members_sorted[0]
        origin_svc    = origin_group["service_id"]
        origin_score_val = origin_group.get("origin_score", 0.0)

        # Blast radius: services transitively depending on origin
        from alertlens.cluster.graph_utils import transitive_dependents
        dependents   = transitive_dependents(DG, origin_svc)
        blast_radius = len(dependents)

        # History match
        hist_match, hist_type = history_match_score(members, train_incidents)

        # Priority
        prio = priority_score(max_sev_num, n_services, blast_radius, hist_match, n_alerts_raw)
        band = get_band(prio, max_sev_num)
        surfaced, surface_reason = should_surface(
            prio, max_sev_num, hist_match, n_groups, n_services,
            settings.surface_threshold,
        )
        if not surfaced:
            band = "BACKGROUND"

        # Surfaced timestamp = first_ts of cluster (batch mode)
        surfaced_ts = first_ts if surfaced else None

        # Title: origin alert fingerprint type + service
        fp_row = conn.execute(
            "SELECT template FROM fingerprints WHERE fingerprint_id=?",
            (origin_group["fingerprint_id"],),
        ).fetchone()
        title = _make_title(fp_row["template"] if fp_row else "", origin_svc)

        # Explanations
        reasons = build_reasons(members, origin_svc, DG, conn)

        incident_rows.append({
            "incident_pred_id": inc_id,
            "run_id":           run_id,
            "title":            title,
            "day":              day,
            "first_ts":         first_ts,
            "last_ts":          last_ts,
            "origin_group_id":  origin_group["group_id"],
            "origin_service":   origin_svc,
            "origin_score":     round(origin_score_val, 4),
            "n_alerts_raw":     n_alerts_raw,
            "n_groups":         n_groups,
            "n_services":       n_services,
            "blast_radius":     blast_radius,
            "max_severity_num": max_sev_num,
            "history_match":    round(hist_match, 4),
            "history_match_type": hist_type,
            "priority_score":   round(prio, 4),
            "band":             band,
            "surfaced":         int(surfaced),
            "surfaced_ts":      surfaced_ts,
            "surface_reason":   surface_reason,
            "reasons_json":     json.dumps(reasons),
        })

        # Members
        for rank, mg in enumerate(ranked, start=1):
            origin_path = ""
            if mg["service_id"] != origin_svc:
                from alertlens.cluster.graph_utils import dep_path
                origin_path = dep_path(DG, origin_svc, mg["service_id"])
            member_rows.append({
                "run_id":            run_id,
                "incident_pred_id":  inc_id,
                "group_id":          mg["group_id"],
                "origin_rank":       rank,
                "origin_score":      round(mg.get("origin_score", 0.0), 4),
                "dep_path_from_origin": origin_path,
            })

    # -----------------------------------------------------------------------
    # Persist
    # -----------------------------------------------------------------------
    with conn:
        # Clear previous predictions for this run
        conn.execute("DELETE FROM incident_members WHERE run_id=?", (run_id,))
        conn.execute("DELETE FROM incidents_pred WHERE run_id=?", (run_id,))

        conn.executemany(
            """INSERT INTO incidents_pred
               (incident_pred_id,run_id,title,day,first_ts,last_ts,
                origin_group_id,origin_service,origin_score,
                n_alerts_raw,n_groups,n_services,blast_radius,max_severity_num,
                history_match,history_match_type,priority_score,band,surfaced,
                surfaced_ts,surface_reason,reasons_json)
               VALUES
               (:incident_pred_id,:run_id,:title,:day,:first_ts,:last_ts,
                :origin_group_id,:origin_service,:origin_score,
                :n_alerts_raw,:n_groups,:n_services,:blast_radius,:max_severity_num,
                :history_match,:history_match_type,:priority_score,:band,:surfaced,
                :surfaced_ts,:surface_reason,:reasons_json)""",
            incident_rows,
        )
        conn.executemany(
            """INSERT INTO incident_members
               (run_id,incident_pred_id,group_id,origin_rank,origin_score,dep_path_from_origin)
               VALUES (:run_id,:incident_pred_id,:group_id,:origin_rank,:origin_score,:dep_path_from_origin)""",
            member_rows,
        )

    surfaced_count = sum(1 for r in incident_rows if r["surfaced"])
    print(
        f"[correlator] clusters={len(incident_rows)}  surfaced={surfaced_count}  "
        f"members_written={len(member_rows)}"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _make_title(template: str, service: str) -> str:
    """Derive a human-readable incident title from fingerprint template + service."""
    keywords = {
        "replication_lag": "Replication lag",
        "latency":         "High latency",
        "error_rate":      "Error rate spike",
        "timeout":         "Timeout cascade",
        "endpoint_down":   "Endpoint down",
        "disk":            "Disk full",
        "cert":            "Certificate expiry",
        "queue_lag":       "Queue backlog",
        "dns":             "DNS failure",
        "cache_miss":      "Cache failure",
        "deploy_error":    "Bad deploy",
        "oom":             "OOM / Restart loop",
        "packet_loss":     "Network partition",
        "conn_refused":    "Connection refused",
        "restart_loop":    "Restart loop",
    }
    for kw, label in keywords.items():
        if kw in template:
            return f"{label} — {service}"
    # Fallback: first 6 words of template
    words = template.split()[:6]
    return " ".join(words) + f" — {service}"


def _load_train_incidents(conn: sqlite3.Connection) -> list[dict]:
    """Load training incidents for history matching."""
    rows = conn.execute(
        """SELECT i.incident_id, i.type,
                  GROUP_CONCAT(ag.fingerprint_id) AS fp_ids,
                  GROUP_CONCAT(ag.alert_count)    AS counts
           FROM incidents_truth i
           JOIN alerts a ON a.truth_incident_id = i.incident_id
           JOIN alert_groups ag ON ag.group_id = a.group_id
           WHERE i.split = 'train'
           GROUP BY i.incident_id"""
    ).fetchall()
    result = []
    for r in rows:
        fp_ids = (r["fp_ids"] or "").split(",")
        counts = [int(c) for c in (r["counts"] or "1").split(",")]
        result.append({
            "incident_id": r["incident_id"],
            "type":        r["type"],
            "fingerprints": dict(zip(fp_ids, counts)),
        })
    return result
