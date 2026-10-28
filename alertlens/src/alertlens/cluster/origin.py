"""
Origin ranking — score each alert group within a cluster to find the
most likely root cause.

Formula (BACKEND_STRUCTURE §5.7):
    E = 1 - rank_by_first_ts / (n-1)         earliness score
    U = dependents_in_cluster / (n_services-1) upstream score
    T = 1 - tier / 3                           infrastructure score

    origin_score = 0.45·E + 0.40·U + 0.15·T
"""
from __future__ import annotations

import networkx as nx


def rank_origins(
    members: list[dict],
    DG: nx.DiGraph,
    n_services: int,
) -> list[dict]:
    """
    Rank *members* by origin score (descending).
    Returns a new list of member dicts with 'origin_score' added.
    """
    if not members:
        return []

    n = len(members)
    sorted_by_ts = sorted(members, key=lambda g: g["first_ts"])

    # Build a set of services in this cluster
    cluster_services = {m["service_id"] for m in members}

    scored = []
    for rank_ts, grp in enumerate(sorted_by_ts):
        svc = grp["service_id"]

        # E: earliness (0 for first, approaching 1 as rank worsens)
        E = 1.0 - (rank_ts / max(n - 1, 1))

        # U: fraction of cluster services that transitively depend on svc
        try:
            dependents_in_cluster = nx.ancestors(DG, svc) & cluster_services
        except nx.NodeNotFound:
            dependents_in_cluster = set()
        U = len(dependents_in_cluster) / max(n_services - 1, 1)

        # T: infrastructure tier bonus
        tier = DG.nodes.get(svc, {}).get("tier", 2)
        T = 1.0 - tier / 3.0

        score = 0.45 * E + 0.40 * U + 0.15 * T
        scored.append({**grp, "origin_score": round(score, 4)})

    return sorted(scored, key=lambda g: g["origin_score"], reverse=True)
