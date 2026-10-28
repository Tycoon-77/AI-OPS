"""
History matching — compare a cluster's fingerprint set to training incidents.

Returns (max_jaccard_score, incident_type_or_None).
Uses volume-weighted Jaccard similarity.
"""
from __future__ import annotations


def history_match_score(
    members: list[dict],
    train_incidents: list[dict],
) -> tuple[float, str | None]:
    """
    *members*         — alert_group dicts for the current cluster
    *train_incidents* — list of {incident_id, type, fingerprints: {fp_id: count}}

    Returns (best_score, incident_type) or (0.0, None).
    """
    if not train_incidents or not members:
        return 0.0, None

    # Build cluster fingerprint → total alert count
    cluster_fps: dict[str, int] = {}
    for m in members:
        fp = m["fingerprint_id"]
        cluster_fps[fp] = cluster_fps.get(fp, 0) + m["alert_count"]

    best_score = 0.0
    best_type: str | None = None

    for inc in train_incidents:
        inc_fps: dict[str, int] = inc.get("fingerprints", {})
        if not inc_fps:
            continue

        # Volume-weighted Jaccard
        all_fps = set(cluster_fps) | set(inc_fps)
        intersection = 0.0
        union = 0.0
        for fp in all_fps:
            c = cluster_fps.get(fp, 0)
            i = inc_fps.get(fp, 0)
            intersection += min(c, i)
            union += max(c, i)

        score = intersection / union if union > 0 else 0.0
        if score > best_score:
            best_score = score
            best_type  = inc.get("type")

    return round(best_score, 4), best_type
