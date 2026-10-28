"""
ML-augmented correlator — three modes behind --mode flag.

modes:
  rules              : original union-find (unchanged, kept as reference)
  classifier_rules   : filter groups via group classifier, then apply rules
  full               : group filter + online pair-score incident assignment

New settings used from config.py:
  group_threshold_cr   : group score threshold for classifier_rules mode
  group_threshold_full : group score threshold for full mode
  pair_threshold       : pair score to join an open incident (full mode)
  inactivity_timeout_min : close open incident after N min of no new groups

All three modes write to the tables with the same schema as run_rules_baseline
and additionally support writing output JSON to a file path (out_json=).
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import lightgbm as lgb
import networkx as nx
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from alertlens.cluster.graph_utils import (
    build_directed_graph,
    build_undirected_graph,
    dep_path,
    graph_dist,
    transitive_dependents,
)
from alertlens.cluster.history import history_match_score
from alertlens.cluster.origin import rank_origins
from alertlens.cluster.priority import get_band, priority_score, should_surface
from alertlens.config import settings
from alertlens.explain.reasons import build_reasons
from alertlens.features.group_features import build_group_features
from alertlens.features.pair_features import FEATURE_NAMES, extract_pair_features


# ---------------------------------------------------------------------------
# Union-Find (unchanged)
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
# Original rules baseline (kept intact)
# ---------------------------------------------------------------------------

def run_rules_baseline(
    conn: sqlite3.Connection,
    run_id: str,
    split: str = "all",
    pair_window_min: int | None = None,
    graph_dist_threshold: int = 2,
    out_json: str | None = None,
) -> None:
    """
    Build incident clusters using pure topological rules (no ML).
    Writes results into incidents_pred + incident_members.
    """
    pair_window = pair_window_min or settings.pair_window_min
    window_td = timedelta(minutes=pair_window)

    groups = _load_groups(conn, split)
    if not groups:
        print(f"[correlator] No groups for split={split}")
        return

    UG = build_undirected_graph(conn)
    DG = build_directed_graph(conn)

    uf = UnionFind()
    for g in groups:
        uf.find(g["group_id"])

    for i, b in enumerate(groups):
        b_ts = _parse_ts(b["first_ts"])
        for a in reversed(groups[:i]):
            a_ts = _parse_ts(a["first_ts"])
            if b_ts - a_ts > window_td:
                break
            dist = graph_dist(UG, a["service_id"], b["service_id"])
            if dist <= graph_dist_threshold:
                uf.union(a["group_id"], b["group_id"])

    cluster_map = uf.clusters([g["group_id"] for g in groups])
    _persist_clusters(conn, run_id, cluster_map, groups, DG, out_json=out_json)


# ---------------------------------------------------------------------------
# Classifier + Rules mode
# ---------------------------------------------------------------------------

def run_classifier_rules(
    conn: sqlite3.Connection,
    run_id: str,
    split: str = "all",
    pair_window_min: int | None = None,
    graph_dist_threshold: int = 2,
    group_threshold: float | None = None,
    group_model_path: str = "models/group_lgbm.txt",
    out_json: str | None = None,
) -> None:
    """
    Filter groups above group_threshold, then apply union-find rules.
    Groups below threshold are each placed in their own singleton cluster.
    """
    pair_window = pair_window_min or settings.pair_window_min
    window_td = timedelta(minutes=pair_window)
    g_thr = group_threshold if group_threshold is not None else float(os.environ.get("ALERTLENS_GROUP_THRESHOLD_CR", "0.001"))

    groups = _load_groups(conn, split)
    if not groups:
        print(f"[correlator] No groups for split={split}")
        return

    # Score groups with group classifier
    kept_ids = _score_groups(conn, groups, group_model_path, g_thr)
    kept_set = set(kept_ids)
    print(
        f"[correlator:classifier_rules] groups={len(groups)}  "
        f"kept={len(kept_set)}  thr={g_thr:.3f}"
    )

    UG = build_undirected_graph(conn)
    DG = build_directed_graph(conn)

    uf = UnionFind()
    for g in groups:
        uf.find(g["group_id"])

    # Run rules only on kept groups
    kept_groups = [g for g in groups if g["group_id"] in kept_set]
    for i, b in enumerate(kept_groups):
        b_ts = _parse_ts(b["first_ts"])
        for a in reversed(kept_groups[:i]):
            a_ts = _parse_ts(a["first_ts"])
            if b_ts - a_ts > window_td:
                break
            dist = graph_dist(UG, a["service_id"], b["service_id"])
            if dist <= graph_dist_threshold:
                uf.union(a["group_id"], b["group_id"])

    cluster_map = uf.clusters([g["group_id"] for g in groups])
    _persist_clusters(conn, run_id, cluster_map, groups, DG, out_json=out_json)


# ---------------------------------------------------------------------------
# Full ML mode (online incident assignment)
# ---------------------------------------------------------------------------

def run_ml_clustering(
    conn: sqlite3.Connection,
    run_id: str,
    split: str = "all",
    pair_window_min: int | None = None,
    group_threshold: float | None = None,
    pair_threshold: float | None = None,
    inactivity_timeout_min: int | None = None,
    group_model_path: str = "models/group_lgbm.txt",
    pair_model_path: str = "models/pair_lgbm.txt",
    out_json: str | None = None,
) -> None:
    """
    Full ML clustering:
      1. Score all groups with group classifier; drop below group_threshold.
      2. Process kept groups in time order.
      3. For each group, score against recent members of open incidents
         using the pair model; join if score >= pair_threshold.
      4. Singleton cluster for groups not kept by group classifier.
    """
    pair_window = pair_window_min or settings.pair_window_min
    g_thr = group_threshold if group_threshold is not None else float(os.environ.get("ALERTLENS_GROUP_THRESHOLD_FULL", "0.001"))
    p_thr = pair_threshold if pair_threshold is not None else getattr(settings, "pair_threshold", 0.60)
    timeout_min = inactivity_timeout_min if inactivity_timeout_min is not None else int(os.environ.get("ALERTLENS_INACTIVITY_TIMEOUT_MIN", "15"))
    window_td = timedelta(minutes=pair_window)
    timeout_td = timedelta(minutes=timeout_min)

    groups = _load_groups(conn, split)
    if not groups:
        print(f"[correlator] No groups for split={split}")
        return

    # Score groups
    kept_ids = _score_groups(conn, groups, group_model_path, g_thr)
    kept_set = set(kept_ids)
    print(
        f"[correlator:full] groups={len(groups)}  "
        f"kept={len(kept_set)}  g_thr={g_thr:.3f}  p_thr={p_thr:.3f}  timeout={timeout_min}min"
    )

    # Build graphs
    UG = build_undirected_graph(conn)
    DG = build_directed_graph(conn)
    all_services = list(UG.nodes())
    reachability = {s: set(nx.descendants(DG, s)) if s in DG else set() for s in all_services}
    shortest_paths = dict(nx.all_pairs_shortest_path_length(UG))

    # Fit TF-IDF on TRAIN groups only (no leakage)
    train_rows = conn.execute(
        """SELECT ag.group_id, f.template
           FROM alert_groups ag
           JOIN fingerprints f ON ag.fingerprint_id = f.fingerprint_id
           WHERE ag.split = 'train'
           ORDER BY ag.first_ts"""
    ).fetchall()
    train_templates = [r["template"] for r in train_rows]
    train_gids = [r["group_id"] for r in train_rows]

    tfidf = TfidfVectorizer(
        ngram_range=(3, 5), analyzer="char", min_df=2, max_features=1000
    )
    tfidf.fit(train_templates)

    # Fit transform for ALL groups (train tfidf, applied to all)
    all_templates_rows = conn.execute(
        """SELECT ag.group_id, f.template
           FROM alert_groups ag
           JOIN fingerprints f ON ag.fingerprint_id = f.fingerprint_id
           ORDER BY ag.first_ts"""
    ).fetchall()
    all_gid_order = [r["group_id"] for r in all_templates_rows]
    all_templates = [r["template"] for r in all_templates_rows]
    tfidf_matrix = tfidf.transform(all_templates)
    gid_to_tfidf_idx = {gid: i for i, gid in enumerate(all_gid_order)}

    # Load pair booster
    pair_booster = lgb.Booster(model_file=pair_model_path)

    # ------------------------------------------------------------------ #
    # Online assignment
    # ------------------------------------------------------------------ #
    # cluster_map: group_id -> incident_id (str)
    cluster_assignment: dict[str, str] = {}
    inc_counter = [0]

    # open_incidents: list of dicts
    #   {id, members: [group_dict], last_ts: datetime}
    open_incidents: list[dict] = []

    group_by_id = {g["group_id"]: g for g in groups}

    def _new_incident(g: dict) -> str:
        inc_counter[0] += 1
        iid = f"inc_{run_id}_{inc_counter[0]:04d}"
        open_incidents.append({
            "id": iid,
            "members": [g],
            "last_ts": _parse_ts(g["first_ts"]),
        })
        return iid

    def _score_pair(a: dict, b: dict) -> float:
        a_idx = gid_to_tfidf_idx.get(a["group_id"])
        b_idx = gid_to_tfidf_idx.get(b["group_id"])
        if a_idx is None or b_idx is None:
            return 0.0
        feats = extract_pair_features(
            a, b, a_idx, b_idx, shortest_paths, reachability, tfidf_matrix
        )
        arr = np.array([feats], dtype=np.float32)
        return float(pair_booster.predict(arr)[0])

    # Process groups in time order
    for g in groups:
        gid = g["group_id"]
        gdt = _parse_ts(g["first_ts"])

        if gid not in kept_set:
            # Not kept by group classifier → singleton
            inc_counter[0] += 1
            iid = f"inc_{run_id}_{inc_counter[0]:04d}"
            cluster_assignment[gid] = iid
            continue

        # Expire inactive open incidents
        still_open = []
        for oi in open_incidents:
            if gdt - oi["last_ts"] <= timeout_td:
                still_open.append(oi)
            # expired → they stay closed, already assigned
        open_incidents[:] = still_open

        # Score against recent members of each open incident
        best_score = -1.0
        best_inc = None
        for oi in open_incidents:
            # Score against last N members within window
            recent = [
                m for m in oi["members"]
                if gdt - _parse_ts(m["first_ts"]) <= window_td
            ][-5:]
            if not recent:
                recent = oi["members"][-3:]
            scores = [_score_pair(m, g) for m in recent]
            score = max(scores) if scores else 0.0
            if score > best_score:
                best_score = score
                best_inc = oi

        if best_score >= p_thr and best_inc is not None:
            best_inc["members"].append(g)
            best_inc["last_ts"] = gdt
            cluster_assignment[gid] = best_inc["id"]
        else:
            iid = _new_incident(g)
            cluster_assignment[gid] = iid

    # Remaining open incidents are fine — already assigned
    # Assign singletons for any unassigned (shouldn't happen)
    for g in groups:
        if g["group_id"] not in cluster_assignment:
            inc_counter[0] += 1
            cluster_assignment[g["group_id"]] = f"inc_{run_id}_{inc_counter[0]:04d}"

    # Build cluster_map
    cluster_map: dict[str, list[str]] = {}
    for gid, iid in cluster_assignment.items():
        cluster_map.setdefault(iid, []).append(gid)

    _persist_clusters(conn, run_id, cluster_map, groups, DG, out_json=out_json)


# ---------------------------------------------------------------------------
# Shared cluster persistence
# ---------------------------------------------------------------------------

def _persist_clusters(
    conn: sqlite3.Connection,
    run_id: str,
    cluster_map: dict[str, list[str]],
    groups: list[dict],
    DG: nx.DiGraph,
    out_json: str | None = None,
) -> None:
    """Write cluster results to DB and optionally to a JSON file."""
    group_by_id = {g["group_id"]: g for g in groups}
    train_incidents = _load_train_incidents(conn)

    incident_rows: list[dict] = []
    member_rows: list[dict] = []
    clusters_out: list[dict] = []

    inc_counter = 0
    for cl_key, member_ids in cluster_map.items():
        inc_counter += 1
        inc_id = cl_key if cl_key.startswith(f"inc_{run_id}_") else f"inc_{run_id}_{inc_counter:04d}"
        members = [group_by_id[gid] for gid in member_ids if gid in group_by_id]
        if not members:
            continue
        members_sorted = sorted(members, key=lambda g: g["first_ts"])

        first_ts = members_sorted[0]["first_ts"]
        last_ts = members_sorted[-1]["last_ts"]
        day = first_ts[:10]
        n_groups = len(members)
        n_alerts_raw = sum(m["alert_count"] for m in members)
        services = list({m["service_id"] for m in members})
        n_services = len(services)
        max_sev_num = max(m["max_severity_num"] for m in members)

        ranked = rank_origins(members, DG, n_services)
        origin_group = ranked[0] if ranked else members_sorted[0]
        origin_svc = origin_group["service_id"]
        origin_score_val = origin_group.get("origin_score", 0.0)

        dependents = transitive_dependents(DG, origin_svc)
        blast_radius = len(dependents)

        hist_match, hist_type = history_match_score(members, train_incidents)

        prio = priority_score(max_sev_num, n_services, blast_radius, hist_match, n_alerts_raw)
        band = get_band(prio, max_sev_num)
        surfaced, surface_reason = should_surface(
            prio, max_sev_num, hist_match, n_groups, n_services,
            settings.surface_threshold,
        )
        if not surfaced:
            band = "BACKGROUND"

        surfaced_ts = first_ts if surfaced else None

        fp_row = conn.execute(
            "SELECT template FROM fingerprints WHERE fingerprint_id=?",
            (origin_group["fingerprint_id"],),
        ).fetchone()
        template_str = fp_row["template"] if fp_row else ""
        title = _make_title(template_str, origin_svc)

        reasons = build_reasons(members, origin_svc, DG, conn)

        # Fetch alert_ids for JSON output
        if out_json:
            placeholders = ",".join("?" for _ in member_ids)
            alert_rows = conn.execute(
                f"SELECT alert_id, service_id FROM alerts WHERE group_id IN ({placeholders})",
                member_ids,
            ).fetchall()
            alert_ids = [r["alert_id"] for r in alert_rows]
            svc_list = list({r["service_id"] for r in alert_rows})

            seen_svcs: set[str] = set()
            origin_candidates = [
                r["service_id"]
                for r in ranked
                if not (r["service_id"] in seen_svcs or seen_svcs.add(r["service_id"]))
            ]

            clusters_out.append({
                "cluster_id": inc_id,
                "band": band,
                "origin": origin_svc,
                "origin_candidates": origin_candidates,
                "alert_ids": alert_ids,
                "services": svc_list,
                "start": first_ts,
                "end": last_ts,
                "alert_count": n_alerts_raw,
                "reasons": [r["text"] for r in reasons],
            })

        incident_rows.append({
            "incident_pred_id": inc_id,
            "run_id": run_id,
            "title": title,
            "day": day,
            "first_ts": first_ts,
            "last_ts": last_ts,
            "origin_group_id": origin_group["group_id"],
            "origin_service": origin_svc,
            "origin_score": round(origin_score_val, 4),
            "n_alerts_raw": n_alerts_raw,
            "n_groups": n_groups,
            "n_services": n_services,
            "blast_radius": blast_radius,
            "max_severity_num": max_sev_num,
            "history_match": round(hist_match, 4),
            "history_match_type": hist_type or "",
            "priority_score": round(prio, 4),
            "band": band,
            "surfaced": int(surfaced),
            "surfaced_ts": surfaced_ts,
            "surface_reason": surface_reason,
            "reasons_json": json.dumps(reasons),
        })

        for rank, mg in enumerate(ranked, start=1):
            op = ""
            if mg["service_id"] != origin_svc:
                op = dep_path(DG, origin_svc, mg["service_id"])
            member_rows.append({
                "run_id": run_id,
                "incident_pred_id": inc_id,
                "group_id": mg["group_id"],
                "origin_rank": rank,
                "origin_score": round(mg.get("origin_score", 0.0), 4),
                "dep_path_from_origin": op,
            })

    with conn:
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

    if out_json:
        Path(out_json).parent.mkdir(parents=True, exist_ok=True)
        with open(out_json, "w") as f:
            json.dump(clusters_out, f, indent=2)
        print(f"[correlator] clusters JSON → {out_json}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_groups(conn: sqlite3.Connection, split: str) -> list[dict]:
    if split and split != "all":
        rows = conn.execute(
            """SELECT ag.group_id, ag.fingerprint_id, ag.service_id, ag.source,
                      ag.first_ts, ag.last_ts, ag.alert_count, ag.max_severity_num,
                      ag.split, ag.truth_incident_id, s.tier
               FROM alert_groups ag
               JOIN services s ON ag.service_id = s.service_id
               WHERE ag.split = ?
               ORDER BY ag.first_ts""",
            (split,),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT ag.group_id, ag.fingerprint_id, ag.service_id, ag.source,
                      ag.first_ts, ag.last_ts, ag.alert_count, ag.max_severity_num,
                      ag.split, ag.truth_incident_id, s.tier
               FROM alert_groups ag
               JOIN services s ON ag.service_id = s.service_id
               ORDER BY ag.first_ts"""
        ).fetchall()

    groups = [dict(r) for r in rows]
    for g in groups:
        g["dt"] = _parse_ts(g["first_ts"])
    return groups


def _score_groups(
    conn: sqlite3.Connection,
    groups: list[dict],
    model_path: str,
    threshold: float,
) -> list[str]:
    """Return group_ids scoring >= threshold from the group classifier."""
    booster = lgb.Booster(model_file=model_path)
    # Build features on the same split as provided groups
    # We need to pass the same conn; use build_group_features then filter
    split_vals = {g["split"] for g in groups}
    if len(split_vals) == 1:
        (split,) = split_vals
    else:
        split = "all"
    X, _, gids = build_group_features(conn, split=split)
    probs = booster.predict(X)
    return [gid for gid, p in zip(gids, probs) if p >= threshold]


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _make_title(template: str, service: str) -> str:
    keywords = {
        "replication_lag": "Replication lag",
        "latency": "High latency",
        "error_rate": "Error rate spike",
        "timeout": "Timeout cascade",
        "endpoint_down": "Endpoint down",
        "disk": "Disk full",
        "cert": "Certificate expiry",
        "queue_lag": "Queue backlog",
        "dns": "DNS failure",
        "cache_miss": "Cache failure",
        "deploy_error": "Bad deploy",
        "oom": "OOM / Restart loop",
        "packet_loss": "Network partition",
        "conn_refused": "Connection refused",
        "restart_loop": "Restart loop",
    }
    for kw, label in keywords.items():
        if kw in template:
            return f"{label} — {service}"
    words = template.split()[:6]
    return " ".join(words) + f" — {service}"


def _load_train_incidents(conn: sqlite3.Connection) -> list[dict]:
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
            "type": r["type"],
            "fingerprints": dict(zip(fp_ids, counts)),
        })
    return result
