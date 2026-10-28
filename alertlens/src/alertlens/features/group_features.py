"""
Group-level feature extraction for the incident classifier (Step 2).

LEAKAGE RULES enforced here:
  - precursor_rate / fingerprint_daily_freq / service_avg_alert_count are
    computed from the TRAIN split only (rows where ag.split = 'train').
  - Service baseline uses ONLY groups with first_ts < the current group's
    first_ts, recomputed per-group at build time so there is no look-ahead.
    In practice for the train split this is a rolling mean; for test groups
    it uses the full train baseline (no test data leaks in).
  - is_new_fingerprint is 1 if the fingerprint has never appeared in the
    TRAIN split at all (novel) OR appeared only within 1 h of the group's
    own first_ts in the train period.

GROUP_FEATURE_NAMES (13):
  alert_count, log_alert_count, max_severity_num, tier,
  burst_rate, is_new_fingerprint, fingerprint_daily_freq,
  precursor_rate, service_window_service_count,
  neighbor_alert_count, hour_of_day, day_of_week, source_encoded
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np

GROUP_FEATURE_NAMES = [
    "alert_count",
    "log_alert_count",
    "max_severity_num",
    "tier",
    "burst_rate",
    "is_new_fingerprint",
    "fingerprint_daily_freq",
    "precursor_rate",
    "service_window_service_count",
    "neighbor_alert_count",
    "hour_of_day",
    "day_of_week",
    "source_encoded",
]

SOURCE_MAP: Dict[str, int] = {
    "prometheus": 0,
    "datadog": 1,
    "cloudwatch": 2,
    "pagerduty": 3,
    "nagios": 4,
    "zabbix": 5,
    "grafana": 6,
    "newrelic": 7,
}
_UNKNOWN_SRC = len(SOURCE_MAP)

_WINDOW_5 = timedelta(minutes=5)
_WINDOW_10 = timedelta(minutes=10)


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_group_features(
    conn: sqlite3.Connection,
    split: str = "train",
    neighbors: Optional[Dict[str, List[str]]] = None,
) -> tuple:
    """
    Build feature matrix for all groups in *split*.

    Parameters
    ----------
    conn      : open SQLite connection (row_factory should be sqlite3.Row)
    split     : 'train', 'test', or 'all'
    neighbors : optional pre-built undirected neighbour dict; fetched from DB
                if None.

    Returns
    -------
    X         : np.ndarray shape (n, 13) float32
    y         : np.ndarray shape (n,)    int32   (1 = has truth_incident_id)
    group_ids : list[str]
    """
    if neighbors is None:
        neighbors = _load_neighbors(conn)

    # ------------------------------------------------------------------ #
    # Pre-compute TRAIN-only baselines (no leakage regardless of split)
    # ------------------------------------------------------------------ #
    # Service average alert_count across all train groups
    svc_avg: Dict[str, float] = {}
    for r in conn.execute(
        "SELECT service_id, AVG(alert_count) AS avg FROM alert_groups WHERE split='train' GROUP BY service_id"
    ).fetchall():
        svc_avg[r["service_id"]] = max(float(r["avg"]), 1.0)

    # Fingerprint: earliest first_ts in train (for is_new_fingerprint)
    fp_first_train: Dict[str, datetime] = {}
    for r in conn.execute(
        "SELECT fingerprint_id, MIN(first_ts) AS fts FROM alert_groups WHERE split='train' GROUP BY fingerprint_id"
    ).fetchall():
        fp_first_train[r["fingerprint_id"]] = _parse_ts(r["fts"])

    # Fingerprint daily frequency (groups per day) — train only
    fp_daily_freq: Dict[str, float] = {}
    for r in conn.execute(
        """SELECT fingerprint_id,
                  COUNT(*) AS n,
                  MAX(julianday(last_ts) - julianday(first_ts) + 1) AS span_days
           FROM alert_groups WHERE split='train'
           GROUP BY fingerprint_id"""
    ).fetchall():
        span = max(float(r["span_days"]), 1.0)
        fp_daily_freq[r["fingerprint_id"]] = float(r["n"]) / span

    # precursor_rate = distinct incidents where fp appeared in train / total
    # train groups for that fp (a noise-inspired signal; train split only)
    fp_precursor: Dict[str, float] = {}
    for r in conn.execute(
        """SELECT fingerprint_id,
                  SUM(alert_count)                          AS vol,
                  COUNT(DISTINCT truth_incident_id) - (MIN(truth_incident_id) IS NULL) AS involved
           FROM alert_groups WHERE split='train'
           GROUP BY fingerprint_id"""
    ).fetchall():
        vol = max(float(r["vol"]), 1.0)
        involved = float(max(r["involved"] or 0, 0))
        fp_precursor[r["fingerprint_id"]] = involved / vol

    # ------------------------------------------------------------------ #
    # Load target groups (sorted by first_ts for window features)
    # ------------------------------------------------------------------ #
    if split == "all":
        where, params = "", ()
    else:
        where, params = "WHERE ag.split = ?", (split,)

    rows = conn.execute(
        f"""SELECT ag.group_id, ag.fingerprint_id, ag.service_id, ag.source,
                   ag.first_ts, ag.last_ts, ag.alert_count, ag.max_severity_num,
                   ag.split, ag.truth_incident_id, s.tier
            FROM alert_groups ag
            JOIN services s ON ag.service_id = s.service_id
            {where}
            ORDER BY ag.first_ts""",
        params,
    ).fetchall()

    groups = [dict(r) for r in rows]
    for g in groups:
        g["_dt"] = _parse_ts(g["first_ts"])

    n = len(groups)
    timestamps = [g["_dt"] for g in groups]

    X_rows: List[List[float]] = []
    y_rows: List[int] = []
    group_ids: List[str] = []

    for i, g in enumerate(groups):
        gdt = g["_dt"]
        fp_id = g["fingerprint_id"]
        svc = g["service_id"]

        # -- alert_count --------------------------------------------------
        ac = float(g["alert_count"])
        log_ac = float(np.log1p(ac))

        # -- severity / tier ----------------------------------------------
        sev = float(g["max_severity_num"])
        tier = float(g["tier"])

        # -- burst_rate: ac vs service's train baseline -------------------
        burst_rate = ac / svc_avg.get(svc, 1.0)

        # -- is_new_fingerprint: never seen in train OR appeared < 1h ago -
        fft = fp_first_train.get(fp_id)
        if fft is None:
            is_new = 1.0
        else:
            is_new = 1.0 if gdt <= fft + timedelta(hours=1) else 0.0

        # -- fingerprint_daily_freq (train-computed) ----------------------
        fp_freq = fp_daily_freq.get(fp_id, 0.0)

        # -- precursor_rate (train-computed) ------------------------------
        pr = fp_precursor.get(fp_id, 0.0)

        # -- service_window_service_count: distinct svcs ±5 min ----------
        lo = i
        while lo > 0 and gdt - timestamps[lo - 1] <= _WINDOW_5:
            lo -= 1
        hi = i
        while hi < n - 1 and timestamps[hi + 1] - gdt <= _WINDOW_5:
            hi += 1
        win_svcs = {groups[j]["service_id"] for j in range(lo, hi + 1)}
        svc_count = float(len(win_svcs))

        # -- neighbor_alert_count: graph-1 neighbours within 10 min ------
        nbrs = set(neighbors.get(svc, []))
        lo2 = i
        while lo2 > 0 and gdt - timestamps[lo2 - 1] <= _WINDOW_10:
            lo2 -= 1
        hi2 = i
        while hi2 < n - 1 and timestamps[hi2 + 1] - gdt <= _WINDOW_10:
            hi2 += 1
        nbr_ac = float(sum(
            groups[j]["alert_count"]
            for j in range(lo2, hi2 + 1)
            if j != i and groups[j]["service_id"] in nbrs
        ))

        # -- temporal -----------------------------------------------------
        hour = float(gdt.hour)
        dow = float(gdt.weekday())

        # -- source encoding ----------------------------------------------
        src_enc = float(SOURCE_MAP.get(str(g["source"]), _UNKNOWN_SRC))

        X_rows.append([
            ac, log_ac, sev, tier, burst_rate,
            is_new, fp_freq, pr,
            svc_count, nbr_ac,
            hour, dow, src_enc,
        ])
        y_rows.append(1 if g["truth_incident_id"] is not None else 0)
        group_ids.append(g["group_id"])

    return (
        np.array(X_rows, dtype=np.float32),
        np.array(y_rows, dtype=np.int32),
        group_ids,
    )


def _load_neighbors(conn: sqlite3.Connection) -> Dict[str, List[str]]:
    nbrs: Dict[str, List[str]] = {}
    for r in conn.execute("SELECT src_service, dst_service FROM service_edges"):
        src, dst = r["src_service"], r["dst_service"]
        nbrs.setdefault(src, []).append(dst)
        nbrs.setdefault(dst, []).append(src)
    return nbrs
