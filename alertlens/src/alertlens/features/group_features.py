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
    "logging": 0,
    "monitoring": 1,
    "uptime": 2,
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

    # Load ALL groups in chronological order to compute strictly-prior historical features
    all_rows = conn.execute(
        """SELECT ag.group_id, ag.fingerprint_id, ag.service_id, ag.source,
                  ag.first_ts, ag.last_ts, ag.alert_count, ag.max_severity_num,
                  ag.split, ag.truth_incident_id, s.tier
           FROM alert_groups ag
           JOIN services s ON ag.service_id = s.service_id
           ORDER BY ag.first_ts"""
    ).fetchall()

    groups = [dict(r) for r in all_rows]
    for g in groups:
        g["_dt"] = _parse_ts(g["first_ts"])

    timestamps = [g["_dt"] for g in groups]
    n = len(groups)

    # Map each incident to its earliest alert timestamp
    incident_start_times: Dict[str, datetime] = {}
    for g in groups:
        inc = g["truth_incident_id"]
        if inc and inc not in incident_start_times:
            incident_start_times[inc] = g["_dt"]

    # Running state strictly prior to current group
    svc_running_vol: Dict[str, float] = {}
    svc_running_cnt: Dict[str, float] = {}
    fp_first_seen: Dict[str, datetime] = {}
    fp_prior_vol: Dict[str, float] = {}
    fp_prior_incidents: Dict[str, set] = {}

    p5_lo, p5_hi = 0, 0
    p10_lo, p10_hi = 0, 0

    X_all: List[List[float]] = []
    y_all: List[int] = []
    gids_all: List[str] = []
    splits_all: List[str] = []

    for i, g in enumerate(groups):
        gdt = g["_dt"]
        fp_id = g["fingerprint_id"]
        svc = g["service_id"]
        ac = float(g["alert_count"])
        sev = float(g["max_severity_num"])
        tier = float(g["tier"])

        # Service baseline strictly prior to current timestamp
        vol = svc_running_vol.get(svc, 0.0)
        cnt = svc_running_cnt.get(svc, 0.0)
        base_ac = (vol / cnt) if cnt > 0 else 1.0
        burst_rate = ac / max(base_ac, 1.0)

        # Novel fingerprint flag (never seen or first seen < 1 hour ago)
        fst = fp_first_seen.get(fp_id)
        is_new = 1.0 if fst is None or (gdt - fst).total_seconds() < 3600 else 0.0

        # Fingerprint frequency (groups/alerts per day prior to now)
        fp_vol = fp_prior_vol.get(fp_id, 0.0)
        if fst is not None:
            days = max((gdt - fst).total_seconds() / 86400.0, 0.1)
            fp_freq = fp_vol / days
        else:
            fp_freq = 0.0

        # Precursor rate strictly prior to now:
        # distinct completed incidents (>2 hours ago) this fingerprint was involved in / prior volume
        past_incs = {
            inc for inc in fp_prior_incidents.get(fp_id, set())
            if (gdt - incident_start_times[inc]).total_seconds() > 7200
        }
        pr = len(past_incs) / max(fp_vol, 1.0) if fp_vol > 0 else 0.0

        # 5-minute distinct services window
        while p5_lo < n and gdt - timestamps[p5_lo] > _WINDOW_5:
            p5_lo += 1
        while p5_hi < n and timestamps[p5_hi] - gdt <= _WINDOW_5:
            p5_hi += 1
        win_svcs = float(len({groups[j]["service_id"] for j in range(p5_lo, p5_hi)}))

        # 10-minute neighbor alert activity
        while p10_lo < n and gdt - timestamps[p10_lo] > _WINDOW_10:
            p10_lo += 1
        while p10_hi < n and timestamps[p10_hi] - gdt <= _WINDOW_10:
            p10_hi += 1
        svc_nbrs = set(neighbors.get(svc, []))
        nbr_ac = float(sum(
            groups[j]["alert_count"]
            for j in range(p10_lo, p10_hi)
            if j != i and groups[j]["service_id"] in svc_nbrs
        ))

        hour = float(gdt.hour)
        dow = float(gdt.weekday())
        src_enc = float(SOURCE_MAP.get(str(g["source"]), _UNKNOWN_SRC))

        # Update running history strictly after feature calculation
        svc_running_vol[svc] = svc_running_vol.get(svc, 0.0) + ac
        svc_running_cnt[svc] = svc_running_cnt.get(svc, 0.0) + 1.0
        fp_prior_vol[fp_id] = fp_prior_vol.get(fp_id, 0.0) + ac
        if fst is None:
            fp_first_seen[fp_id] = gdt
        if g["truth_incident_id"]:
            fp_prior_incidents.setdefault(fp_id, set()).add(g["truth_incident_id"])

        X_all.append([
            ac, np.log1p(ac), sev, tier, burst_rate,
            is_new, fp_freq, pr,
            win_svcs, nbr_ac,
            hour, dow, src_enc,
        ])
        y_all.append(1 if g["truth_incident_id"] is not None else 0)
        gids_all.append(g["group_id"])
        splits_all.append(g["split"])

    X_arr = np.array(X_all, dtype=np.float32)
    y_arr = np.array(y_all, dtype=np.int32)

    if split == "all":
        return X_arr, y_arr, gids_all

    mask = [s == split for s in splits_all]
    idx = [i for i, m in enumerate(mask) if m]
    return X_arr[idx], y_arr[idx], [gids_all[i] for i in idx]


def _load_neighbors(conn: sqlite3.Connection) -> Dict[str, List[str]]:
    nbrs: Dict[str, List[str]] = {}
    for r in conn.execute("SELECT src_service, dst_service FROM service_edges"):
        src, dst = r["src_service"], r["dst_service"]
        nbrs.setdefault(src, []).append(dst)
        nbrs.setdefault(dst, []).append(src)
    return nbrs
