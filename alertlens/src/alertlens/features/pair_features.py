"""
Shared pair-feature extraction for training (model/train.py) and inference
(cluster/correlator.py).

Features (13):
    dt_sec, log_dt, g_dist, a_dep_b, b_dep_a,
    t_a, t_b, t_diff, same_src, same_sev, sev_a, sev_b, text_sim
"""
from __future__ import annotations

import numpy as np

FEATURE_NAMES = [
    "dt_sec", "log_dt", "g_dist", "a_dep_b", "b_dep_a",
    "t_a", "t_b", "t_diff", "same_src", "same_sev",
    "sev_a", "sev_b", "text_sim",
]


def extract_pair_features(
    a: dict,
    b: dict,
    a_idx: int,
    b_idx: int,
    shortest_paths: dict,
    reachability: dict,
    tfidf_matrix,
) -> list:
    """
    Extract the 13-feature vector for a candidate pair (a, b).

    Parameters
    ----------
    a, b            : alert-group dicts with keys:
                      dt (datetime), service_id (str), source (str),
                      max_severity_num (int), tier (int)
    a_idx, b_idx    : row indices into *tfidf_matrix*
    shortest_paths  : dict[service_id -> dict[service_id -> int]]
                      (from nx.all_pairs_shortest_path_length on UG)
    reachability    : dict[service_id -> set[service_id]]
                      (descendants in DG for each node)
    tfidf_matrix    : sparse matrix returned by TfidfVectorizer.fit_transform /
                      transform; shape (n_groups, n_vocab)

    Returns
    -------
    list of float, length 13, in the order of FEATURE_NAMES.
    """
    dt_sec = (b["dt"] - a["dt"]).total_seconds()
    log_dt = np.log1p(dt_sec)

    s_a = a["service_id"]
    s_b = b["service_id"]
    g_dist = shortest_paths.get(s_a, {}).get(s_b, 6)

    a_dep_b = 1.0 if s_b in reachability.get(s_a, set()) else 0.0
    b_dep_a = 1.0 if s_a in reachability.get(s_b, set()) else 0.0

    t_a = a["tier"]
    t_b = b["tier"]
    t_diff = abs(t_a - t_b)

    same_src = 1.0 if a["source"] == b["source"] else 0.0
    same_sev = 1.0 if a["max_severity_num"] == b["max_severity_num"] else 0.0
    sev_a = a["max_severity_num"]
    sev_b = b["max_severity_num"]

    vec_a = tfidf_matrix[a_idx]
    vec_b = tfidf_matrix[b_idx]
    text_sim = float(vec_a.dot(vec_b.T).toarray()[0][0])

    return [
        dt_sec, log_dt, g_dist, a_dep_b, b_dep_a,
        t_a, t_b, t_diff, same_src, same_sev,
        sev_a, sev_b, text_sim,
    ]
