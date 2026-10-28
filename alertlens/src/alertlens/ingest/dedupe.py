"""De-duplication — collapse alerts with same (fingerprint, service) within DEDUP_WINDOW."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

SEV_MAP = {"low": 1, "medium": 2, "high": 3, "critical": 4}


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def dedupe_alerts(
    alerts: list[dict],
    dedup_window_min: int = 5,
) -> list[dict]:
    """
    Group alerts by (fingerprint_id, service_id) whose gap to the previous alert
    in the group is ≤ *dedup_window_min* minutes.

    Each contiguous run becomes one ``alert_group`` dict with fields:
        group_id, fingerprint_id, service_id, source, first_ts, last_ts,
        alert_count, max_severity_num, split, truth_incident_id
    """
    # Sort by timestamp then by (fingerprint, service) for stable ordering
    sorted_alerts = sorted(alerts, key=lambda a: (a["ts"], a["fingerprint_id"], a["service_id"]))

    window = timedelta(minutes=dedup_window_min)
    # key → (last_ts, current_group_dict)
    open_groups: dict[tuple, dict] = {}
    groups: list[dict] = []
    counter = 0

    for alert in sorted_alerts:
        key = (alert["fingerprint_id"], alert["service_id"])
        ts  = _parse_ts(alert["ts"])

        if key in open_groups:
            last_ts, grp = open_groups[key]
            if ts - last_ts <= window:
                # Extend the existing group
                grp["last_ts"] = alert["ts"]
                grp["alert_count"] += 1
                sev_num = SEV_MAP.get(alert["severity"], 1)
                if sev_num > grp["max_severity_num"]:
                    grp["max_severity_num"] = sev_num
                # Keep majority non-null truth incident
                if alert.get("truth_incident_id"):
                    grp["_truth_ids"].append(alert["truth_incident_id"])
                alert["group_id"] = grp["group_id"]
                open_groups[key] = (ts, grp)
                continue
            else:
                # Gap too large — close old group
                _finalise_group(grp)
                groups.append(grp)

        # Start a new group
        counter += 1
        sev_num = SEV_MAP.get(alert["severity"], 1)
        truth_ids = [alert["truth_incident_id"]] if alert.get("truth_incident_id") else []
        gid = f"grp_{counter:06d}"
        alert["group_id"] = gid
        grp = {
            "group_id":        gid,
            "fingerprint_id":  alert["fingerprint_id"],
            "service_id":      alert["service_id"],
            "source":          alert["source"],
            "first_ts":        alert["ts"],
            "last_ts":         alert["ts"],
            "alert_count":     1,
            "max_severity_num": sev_num,
            "split":           alert.get("split", "train"),
            "truth_incident_id": None,
            "_truth_ids":      truth_ids,
        }
        open_groups[key] = (ts, grp)

    # Close all remaining open groups
    for _, (_, grp) in open_groups.items():
        _finalise_group(grp)
        groups.append(grp)

    return groups


def _finalise_group(grp: dict) -> None:
    """Set truth_incident_id from majority label and remove internal list."""
    truth_ids = grp.pop("_truth_ids", [])
    if truth_ids:
        # majority vote
        from collections import Counter
        grp["truth_incident_id"] = Counter(truth_ids).most_common(1)[0][0]
    else:
        grp["truth_incident_id"] = None
