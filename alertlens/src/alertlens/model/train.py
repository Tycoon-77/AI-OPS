"""
LightGBM pairwise alert correlator training.
Follows BACKEND_STRUCTURE.md Section 5.3-5.5.
Trains on train split, saves to models/pair_lgbm.txt (default) or a custom path.

Now delegates feature extraction to alertlens.features.pair_features so that
training and inference share one implementation.
"""
from __future__ import annotations

import os
import random
import time
from datetime import datetime, timedelta
from pathlib import Path

import lightgbm as lgb
import networkx as nx
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import roc_auc_score

from alertlens.api.db import get_connection
from alertlens.cluster.graph_utils import build_directed_graph, build_undirected_graph
from alertlens.features.pair_features import FEATURE_NAMES, extract_pair_features


def train_pair_model(
    model_out: str = "models/pair_lgbm.txt",
    max_neg_ratio: int = 3,
) -> dict:
    t0 = time.time()
    conn = get_connection()
    UG = build_undirected_graph(conn)
    DG = build_directed_graph(conn)

    all_services = list(UG.nodes())
    reachability = {s: set(nx.descendants(DG, s)) if s in DG else set() for s in all_services}
    shortest_paths = dict(nx.all_pairs_shortest_path_length(UG))

    # Load train groups
    rows = conn.execute("""
        SELECT ag.group_id, ag.first_ts, ag.service_id, ag.source, ag.max_severity_num,
               ag.truth_incident_id, f.template, s.tier
        FROM alert_groups ag
        JOIN fingerprints f ON ag.fingerprint_id = f.fingerprint_id
        JOIN services s ON ag.service_id = s.service_id
        WHERE ag.split = "train"
        ORDER BY ag.first_ts
    """).fetchall()

    groups = [dict(r) for r in rows]
    for g in groups:
        g["dt"] = datetime.fromisoformat(g["first_ts"].replace("Z", "+00:00"))

    # Fit TF-IDF on templates (train split only)
    templates = [g["template"] for g in groups]
    tfidf = TfidfVectorizer(ngram_range=(3, 5), analyzer="char", min_df=2, max_features=1000)
    tfidf_matrix = tfidf.fit_transform(templates)

    # Candidate pairs within 10-minute sliding window
    pos_pairs = []
    neg_candidates = []
    window = timedelta(minutes=10)

    for i, b in enumerate(groups):
        b_dt = b["dt"]
        b_truth = b["truth_incident_id"]
        for a_idx in reversed(range(max(0, i - 150), i)):
            a = groups[a_idx]
            if b_dt - a["dt"] > window:
                break
            a_truth = a["truth_incident_id"]
            is_pos = (b_truth is not None and a_truth is not None and b_truth == a_truth)
            if is_pos:
                pos_pairs.append((a_idx, i, 1))
            else:
                neg_candidates.append((a_idx, i, 0))

    random.seed(42)
    sampled_negs = random.sample(neg_candidates, min(len(neg_candidates), len(pos_pairs) * max_neg_ratio))
    pairs = pos_pairs + sampled_negs
    random.shuffle(pairs)

    X = []
    y = []
    for a_idx, b_idx, label in pairs:
        feats = extract_pair_features(
            groups[a_idx], groups[b_idx],
            a_idx, b_idx,
            shortest_paths, reachability,
            tfidf_matrix,
        )
        X.append(feats)
        y.append(label)

    X = np.array(X, dtype=np.float32)
    y = np.array(y, dtype=np.int32)

    clf = lgb.LGBMClassifier(
        n_estimators=300,
        learning_rate=0.05,
        num_leaves=31,
        min_child_samples=20,
        subsample=0.8,
        colsample_bytree=0.8,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    clf.fit(X, y)

    # Save booster model
    out_path = Path(model_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    clf.booster_.save_model(str(out_path))

    preds = clf.predict_proba(X)[:, 1]
    auc = float(roc_auc_score(y, preds))
    importances = {name: int(imp) for name, imp in zip(FEATURE_NAMES, clf.feature_importances_)}

    conn.close()
    return {
        "n_pairs": len(pairs),
        "n_pos": len(pos_pairs),
        "n_neg": len(sampled_negs),
        "train_auc": round(auc, 4),
        "top_features": sorted(importances.items(), key=lambda x: x[1], reverse=True),
        "model_path": str(out_path),
        "time_s": round(time.time() - t0, 2),
    }


if __name__ == "__main__":
    res = train_pair_model()
    print("LightGBM Model Training Results:")
    for k, v in res.items():
        print(f"  {k}: {v}")
