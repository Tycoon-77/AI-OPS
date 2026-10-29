import json
import random
import time
from datetime import datetime, timedelta
from pathlib import Path
import lightgbm as lgb
import networkx as nx
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import roc_auc_score, average_precision_score, precision_score, recall_score, f1_score
from alertlens.api.db import get_connection
from alertlens.cluster.graph_utils import build_directed_graph, build_undirected_graph

def run():
    conn = get_connection()
    UG = build_undirected_graph(conn)
    DG = build_directed_graph(conn)

    all_services = list(UG.nodes())
    reachability = {s: set(nx.descendants(DG, s)) if s in DG else set() for s in all_services}
    shortest_paths = dict(nx.all_pairs_shortest_path_length(UG))

    # 1. Load train groups
    train_rows = conn.execute("""
        SELECT ag.group_id, ag.first_ts, ag.service_id, ag.source, ag.max_severity_num,
               ag.truth_incident_id, f.template, s.tier
        FROM alert_groups ag
        JOIN fingerprints f ON ag.fingerprint_id = f.fingerprint_id
        JOIN services s ON ag.service_id = s.service_id
        WHERE ag.split = 'train'
        ORDER BY ag.first_ts
    """).fetchall()

    train_groups = [dict(r) for r in train_rows]
    for g in train_groups:
        g["dt"] = datetime.fromisoformat(g["first_ts"].replace("Z", "+00:00"))

    train_templates = [g["template"] for g in train_groups]
    tfidf = TfidfVectorizer(ngram_range=(3, 5), analyzer="char", min_df=2, max_features=1000)
    train_tfidf_matrix = tfidf.fit_transform(train_templates)

    # 2. Load test groups
    test_rows = conn.execute("""
        SELECT ag.group_id, ag.first_ts, ag.service_id, ag.source, ag.max_severity_num,
               ag.truth_incident_id, f.template, s.tier
        FROM alert_groups ag
        JOIN fingerprints f ON ag.fingerprint_id = f.fingerprint_id
        JOIN services s ON ag.service_id = s.service_id
        WHERE ag.split = 'test'
        ORDER BY ag.first_ts
    """).fetchall()

    test_groups = [dict(r) for r in test_rows]
    for g in test_groups:
        g["dt"] = datetime.fromisoformat(g["first_ts"].replace("Z", "+00:00"))

    test_templates = [g["template"] for g in test_groups]
    test_tfidf_matrix = tfidf.transform(test_templates)

    window = timedelta(minutes=10)

    def extract_pairs(groups, tfidf_matrix, sample_neg_ratio=None, seed=42):
        pos_pairs = []
        neg_candidates = []
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

        if sample_neg_ratio is not None and len(pos_pairs) > 0:
            random.seed(seed)
            sampled_negs = random.sample(neg_candidates, min(len(neg_candidates), len(pos_pairs) * sample_neg_ratio))
            pairs = pos_pairs + sampled_negs
            random.shuffle(pairs)
        else:
            pairs = pos_pairs + neg_candidates
            sampled_negs = neg_candidates

        X = []
        y = []
        for a_idx, b_idx, label in pairs:
            a = groups[a_idx]
            b = groups[b_idx]
            dt_sec = (b["dt"] - a["dt"]).total_seconds()
            log_dt = np.log1p(dt_sec)
            s_a, s_b = a["service_id"], b["service_id"]
            g_dist = shortest_paths.get(s_a, {}).get(s_b, 6)
            a_dep_b = 1.0 if s_b in reachability.get(s_a, set()) else 0.0
            b_dep_a = 1.0 if s_a in reachability.get(s_b, set()) else 0.0
            t_a, t_b = a["tier"], b["tier"]
            t_diff = abs(t_a - t_b)
            same_src = 1.0 if a["source"] == b["source"] else 0.0
            same_sev = 1.0 if a["max_severity_num"] == b["max_severity_num"] else 0.0
            sev_a, sev_b = a["max_severity_num"], b["max_severity_num"]
            vec_a = tfidf_matrix[a_idx]
            vec_b = tfidf_matrix[b_idx]
            text_sim = float(vec_a.dot(vec_b.T).toarray()[0][0])
            X.append([dt_sec, log_dt, g_dist, a_dep_b, b_dep_a, t_a, t_b, t_diff, same_src, same_sev, sev_a, sev_b, text_sim])
            y.append(label)

        return np.array(X, dtype=np.float32), np.array(y, dtype=np.int32), len(pos_pairs), len(sampled_negs)

    X_train, y_train, _, _ = extract_pairs(train_groups, train_tfidf_matrix, sample_neg_ratio=3, seed=42)
    X_test_sampled, y_test_sampled, _, _ = extract_pairs(test_groups, test_tfidf_matrix, sample_neg_ratio=3, seed=42)

    booster = lgb.Booster(model_file="models/pair_lgbm.txt")
    train_preds = booster.predict(X_train)
    test_preds = booster.predict(X_test_sampled)

    train_roc_auc = float(roc_auc_score(y_train, train_preds))
    test_roc_auc = float(roc_auc_score(y_test_sampled, test_preds))

    print(f"Train ROC-AUC: {train_roc_auc:.4f}")
    print(f"Test ROC-AUC:  {test_roc_auc:.4f}")

    out_dir = Path("data/eval")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "test_auc.json"
    data = {
        "train_auc": round(train_roc_auc, 4),
        "test_auc": round(test_roc_auc, 4),
        "timestamp": datetime.now().isoformat()
    }
    out_file.write_text(json.dumps(data, indent=2))
    print(f"Wrote {out_file}")
    conn.close()

if __name__ == "__main__":
    run()
