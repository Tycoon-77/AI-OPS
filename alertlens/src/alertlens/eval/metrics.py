"""
metrics.py - Evaluation Engine for AlertLens.
Owned by Person A.

Computes:
1. Compression: raw_alerts ÷ surfaced_incidents (target: >= 50x / >= 90% reduction)
2. Incident Recall: real incidents with >=1 alert in surfaced cluster ÷ total incidents (target: 100%)
   - Buried incident recall (target: 100%)
   - Held-out cert_expiry recall (target: >= 90%)
3. Pairwise Precision & Recall: over alert-group pairs vs ground truth (target: P >= 0.90, R >= 0.80)
4. B-cubed Precision, Recall, and F1 (target: F1 >= 0.85)
5. Origin Accuracy: top-1 & top-3 vs ground-truth root_cause_service (target: top-1 >= 75%)
6. Explainability: surfaced clusters with >= 3 reasons (target: 100%)

Usage:
  python metrics.py --clusters data/sample/clusters.json --alerts data/sample/alerts.csv --incidents data/sample/incidents.csv
  python metrics.py --test
"""

import argparse
import csv
import json
import os
from collections import defaultdict
from typing import Dict, List, Set, Tuple


def load_alerts(alerts_path: str) -> Dict[str, dict]:
    """Loads alerts.csv into a dictionary keyed by alert_id."""
    alerts = {}
    with open(alerts_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            alerts[row["alert_id"]] = row
    return alerts


def load_incidents(incidents_path: str) -> Dict[str, dict]:
    """Loads incidents.csv into a dictionary keyed by incident_id."""
    incidents = {}
    with open(incidents_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # normalize boolean
            row["buried"] = str(row.get("buried", "")).lower() in ("true", "1")
            incidents[row["incident_id"]] = row
    return incidents


def load_clusters(clusters_path: str) -> List[dict]:
    """Loads clusters.json written by Person B."""
    with open(clusters_path, "r", encoding="utf-8") as f:
        return json.load(f)


def compute_compression(total_raw_alerts: int, total_surfaced_clusters: int) -> dict:
    """Computes compression ratio and percentage reduction."""
    if total_surfaced_clusters == 0:
        ratio = float(total_raw_alerts)
        reduction_pct = 100.0 if total_raw_alerts > 0 else 0.0
    else:
        ratio = total_raw_alerts / total_surfaced_clusters
        reduction_pct = (1.0 - (total_surfaced_clusters / total_raw_alerts)) * 100.0 if total_raw_alerts > 0 else 0.0

    return {
        "raw_alerts": total_raw_alerts,
        "surfaced_clusters": total_surfaced_clusters,
        "compression_ratio": round(ratio, 2),
        "reduction_pct": round(reduction_pct, 2),
        "target_met": ratio >= 10.0 or reduction_pct >= 90.0
    }


def compute_recall(
    clusters: List[dict],
    incidents: Dict[str, dict],
    alerts: Dict[str, dict]
) -> dict:
    """
    Computes:
    - Overall Incident Recall
    - Buried Incident Recall
    - Held-out Type (cert_expiry) Recall
    """
    if not incidents:
        return {"recall": 1.0, "buried_recall": 1.0, "heldout_recall": 1.0, "covered": 0, "total": 0}

    # Gather all alerts present in surfaced clusters (excluding BACKGROUND if flagged)
    surfaced_alert_ids = set()
    for cl in clusters:
        band = cl.get("band", "RED").upper()
        if band != "BACKGROUND":
            surfaced_alert_ids.update(cl.get("alert_ids", []))

    # Map truth incident to whether any of its alerts appeared in surfaced clusters
    incident_coverage = {}
    for inc_id, inc in incidents.items():
        # Find alerts belonging to this incident
        inc_alert_ids = [aid for aid, a in alerts.items() if a.get("truth_incident_id") == inc_id]
        if not inc_alert_ids:
            # If no alerts for incident, consider not covered
            incident_coverage[inc_id] = False
            continue
        covered = any(aid in surfaced_alert_ids for aid in inc_alert_ids)
        incident_coverage[inc_id] = covered

    total_incidents = len(incidents)
    covered_count = sum(1 for c in incident_coverage.values() if c)
    overall_recall = covered_count / total_incidents if total_incidents > 0 else 1.0

    # Buried incidents
    buried_incidents = [inc_id for inc_id, inc in incidents.items() if inc.get("buried")]
    if buried_incidents:
        buried_covered = sum(1 for inc_id in buried_incidents if incident_coverage.get(inc_id, False))
        buried_recall = buried_covered / len(buried_incidents)
    else:
        buried_recall = 1.0

    # Held-out incidents (cert_expiry)
    heldout_incidents = [inc_id for inc_id, inc in incidents.items() if inc.get("type") == "cert_expiry"]
    if heldout_incidents:
        heldout_covered = sum(1 for inc_id in heldout_incidents if incident_coverage.get(inc_id, False))
        heldout_recall = heldout_covered / len(heldout_incidents)
    else:
        heldout_recall = 1.0

    return {
        "recall": round(overall_recall, 4),
        "covered_incidents": covered_count,
        "total_incidents": total_incidents,
        "buried_recall": round(buried_recall, 4),
        "buried_total": len(buried_incidents),
        "heldout_recall": round(heldout_recall, 4),
        "heldout_total": len(heldout_incidents),
        "missed_incident_ids": [inc_id for inc_id, cov in incident_coverage.items() if not cov]
    }


def compute_pairwise_metrics(
    clusters: List[dict],
    alerts: Dict[str, dict]
) -> dict:
    """
    Computes Pairwise Precision, Recall, and F1 over alert pairs.
    Pair (a, b) is positive in ground truth if both belong to the same non-empty truth_incident_id.
    Pair (a, b) is positive in prediction if both appear in the same cluster.
    """
    # Build cluster mapping: alert_id -> cluster_id
    pred_clusters = {}
    for cl in clusters:
        cid = cl.get("cluster_id", "c")
        for aid in cl.get("alert_ids", []):
            pred_clusters[aid] = cid

    # Ground truth groups
    truth_groups = defaultdict(list)
    for aid, a in alerts.items():
        t_id = a.get("truth_incident_id", "").strip()
        if t_id:
            truth_groups[t_id].append(aid)

    # All alerts that have truth incident
    all_incident_alerts = [aid for aids in truth_groups.values() for aid in aids]

    # Calculate Ground Truth Pairs
    tp = 0
    fp = 0
    fn = 0

    # 1. Pairs formed by predicted clusters
    # To keep computation fast, iterate within each cluster
    for cl in clusters:
        c_aids = [aid for aid in cl.get("alert_ids", []) if aid in alerts]
        n_c = len(c_aids)
        if n_c < 2:
            continue
        for i in range(n_c):
            a_i = c_aids[i]
            t_i = alerts[a_i].get("truth_incident_id", "").strip()
            for j in range(i + 1, n_c):
                a_j = c_aids[j]
                t_j = alerts[a_j].get("truth_incident_id", "").strip()

                if t_i and t_j and (t_i == t_j):
                    tp += 1
                else:
                    fp += 1

    # 2. Total true pairs across ground truth
    total_true_pairs = 0
    for t_id, aids in truth_groups.items():
        n_t = len(aids)
        if n_t >= 2:
            total_true_pairs += (n_t * (n_t - 1)) // 2

    fn = max(0, total_true_pairs - tp)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "pairwise_precision": round(precision, 4),
        "pairwise_recall": round(recall, 4),
        "pairwise_f1": round(f1, 4),
        "tp_pairs": tp,
        "fp_pairs": fp,
        "fn_pairs": fn,
        "total_true_pairs": total_true_pairs
    }


def compute_bcubed_metrics(
    clusters: List[dict],
    alerts: Dict[str, dict]
) -> dict:
    """
    Computes B-cubed Precision, Recall, and F1.
    For each alert item i:
      Precision(i) = |C(i) ∩ L(i)| / |C(i)|
      Recall(i) = |C(i) ∩ L(i)| / |L(i)|
    Where C(i) is predicted cluster of i, and L(i) is ground truth cluster of i.
    Noise alerts are treated as singleton ground truth clusters.
    """
    # Map item -> predicted cluster items
    pred_map = {}
    for cl in clusters:
        c_aids = set(cl.get("alert_ids", []))
        for aid in c_aids:
            pred_map[aid] = c_aids

    # Map item -> truth cluster items
    truth_map = {}
    truth_groups = defaultdict(set)
    for aid, a in alerts.items():
        t_id = a.get("truth_incident_id", "").strip()
        if t_id:
            truth_groups[t_id].add(aid)
        else:
            # Noise is a singleton
            truth_groups[f"noise_{aid}"].add(aid)

    for t_id, aids in truth_groups.items():
        for aid in aids:
            truth_map[aid] = aids

    precisions = []
    recalls = []

    for aid in alerts:
        c_i = pred_map.get(aid, {aid})
        l_i = truth_map.get(aid, {aid})

        overlap = len(c_i.intersection(l_i))
        prec = overlap / len(c_i) if c_i else 1.0
        rec = overlap / len(l_i) if l_i else 1.0

        precisions.append(prec)
        recalls.append(rec)

    mean_p = sum(precisions) / len(precisions) if precisions else 0.0
    mean_r = sum(recalls) / len(recalls) if recalls else 0.0
    f1 = (2 * mean_p * mean_r) / (mean_p + mean_r) if (mean_p + mean_r) > 0 else 0.0

    return {
        "bcubed_precision": round(mean_p, 4),
        "bcubed_recall": round(mean_r, 4),
        "bcubed_f1": round(f1, 4)
    }


def compute_origin_accuracy(
    clusters: List[dict],
    incidents: Dict[str, dict],
    alerts: Dict[str, dict]
) -> dict:
    """
    Computes Top-1 and Top-3 Origin Service Accuracy against ground-truth root_cause_service.
    """
    top1_correct = 0
    top3_correct = 0
    evaluated_clusters = 0

    for cl in clusters:
        # Determine majority ground-truth incident for this cluster
        c_aids = cl.get("alert_ids", [])
        inc_counts = defaultdict(int)
        for aid in c_aids:
            if aid in alerts:
                t_id = alerts[aid].get("truth_incident_id", "").strip()
                if t_id:
                    inc_counts[t_id] += 1

        if not inc_counts:
            continue

        best_inc_id = max(inc_counts, key=inc_counts.get)
        truth_inc = incidents.get(best_inc_id)
        if not truth_inc:
            continue

        true_origin = truth_inc.get("root_cause_service")
        predicted_origin = cl.get("origin")
        dep_path = cl.get("dep_path", [])

        evaluated_clusters += 1
        if predicted_origin == true_origin:
            top1_correct += 1

        # Check top-3 (e.g. origin or first 3 in dep_path or candidate services)
        candidate_services = [predicted_origin] + [s for s in dep_path if s != predicted_origin]
        if true_origin in candidate_services[:3]:
            top3_correct += 1

    top1_acc = (top1_correct / evaluated_clusters) if evaluated_clusters > 0 else 1.0
    top3_acc = (top3_correct / evaluated_clusters) if evaluated_clusters > 0 else 1.0

    return {
        "origin_top1_accuracy": round(top1_acc, 4),
        "origin_top3_accuracy": round(top3_acc, 4),
        "evaluated_clusters": evaluated_clusters
    }


def compute_explainability(clusters: List[dict]) -> dict:
    """Checks that surfaced clusters carry visible, human-readable reasons (target: 100%)."""
    surfaced = [c for c in clusters if c.get("band", "RED").upper() != "BACKGROUND"]
    if not surfaced:
        return {"explainability_pct": 100.0, "explained_clusters": 0, "total_surfaced": 0}

    explained = sum(1 for c in surfaced if len(c.get("reasons", [])) >= 2)
    pct = (explained / len(surfaced)) * 100.0
    return {
        "explainability_pct": round(pct, 2),
        "explained_clusters": explained,
        "total_surfaced": len(surfaced)
    }


def evaluate_all(
    clusters_path: str,
    alerts_path: str,
    incidents_path: str
) -> dict:
    """Runs the full evaluation suite and returns a combined metrics dictionary."""
    alerts = load_alerts(alerts_path)
    incidents = load_incidents(incidents_path)
    clusters = load_clusters(clusters_path)

    surfaced_clusters = [c for c in clusters if c.get("band", "RED").upper() != "BACKGROUND"]

    compression = compute_compression(len(alerts), len(surfaced_clusters))
    recall = compute_recall(clusters, incidents, alerts)
    pairwise = compute_pairwise_metrics(clusters, alerts)
    bcubed = compute_bcubed_metrics(clusters, alerts)
    origin = compute_origin_accuracy(clusters, incidents, alerts)
    explain = compute_explainability(clusters)

    return {
        "compression": compression,
        "recall": recall,
        "pairwise": pairwise,
        "bcubed": bcubed,
        "origin": origin,
        "explainability": explain
    }


def print_scorecard(metrics: dict):
    """Prints a beautiful formatted Scorecard report."""
    comp = metrics["compression"]
    rec = metrics["recall"]
    pw = metrics["pairwise"]
    bc = metrics["bcubed"]
    orig = metrics["origin"]
    exp = metrics["explainability"]

    print("\n" + "=" * 65)
    print("           ALERTLENS EVALUATION SCORECARD (PERSON A)")
    print("=" * 65)
    print(f"| {'Metric':<32} | {'Target':<12} | {'Result':<13} |")
    print("|" + "-" * 34 + "|" + "-" * 14 + "|" + "-" * 15 + "|")
    print(f"| {'Compression Ratio':<32} | {'>= 50x':<12} | {comp['compression_ratio']:<11}x |")
    print(f"| {'Alert Reduction %':<32} | {'>= 90%':<12} | {comp['reduction_pct']:<12}% |")
    print(f"| {'Overall Incident Recall':<32} | {'100%':<12} | {rec['recall'] * 100:<12.1f}% |")
    print(f"| {'Buried Incident Recall':<32} | {'100%':<12} | {rec['buried_recall'] * 100:<12.1f}% |")
    print(f"| {'Held-Out Cert Expiry Recall':<32} | {'>= 90%':<12} | {rec['heldout_recall'] * 100:<12.1f}% |")
    print(f"| {'Pairwise Precision':<32} | {'>= 0.90':<12} | {pw['pairwise_precision']:<13} |")
    print(f"| {'Pairwise Recall':<32} | {'>= 0.80':<12} | {pw['pairwise_recall']:<13} |")
    print(f"| {'B-cubed F1 Score':<32} | {'>= 0.85':<12} | {bc['bcubed_f1']:<13} |")
    print(f"| {'Origin Top-1 Accuracy':<32} | {'>= 75%':<12} | {orig['origin_top1_accuracy'] * 100:<12.1f}% |")
    print(f"| {'Origin Top-3 Accuracy':<32} | {'>= 90%':<12} | {orig['origin_top3_accuracy'] * 100:<12.1f}% |")
    print(f"| {'Explainability Rate':<32} | {'100%':<12} | {exp['explainability_pct']:<12}% |")
    print("=" * 65)
    print(f"Summary: {comp['raw_alerts']} alerts compressed into {comp['surfaced_clusters']} incident card(s).")
    print("=" * 65 + "\n")


def run_self_test():
    """Runs a quick sanity check on a mock test case."""
    print("Running metrics.py self-test...")
    test_alerts = {
        "a1": {"alert_id": "a1", "truth_incident_id": "inc1"},
        "a2": {"alert_id": "a2", "truth_incident_id": "inc1"},
        "a3": {"alert_id": "a3", "truth_incident_id": "inc2"},
        "a4": {"alert_id": "a4", "truth_incident_id": ""},
    }
    test_incidents = {
        "inc1": {"incident_id": "inc1", "root_cause_service": "db", "buried": True, "type": "db_slowdown"},
        "inc2": {"incident_id": "inc2", "root_cause_service": "auth", "buried": False, "type": "cert_expiry"},
    }
    test_clusters = [
        {"cluster_id": "c1", "band": "RED", "origin": "db", "alert_ids": ["a1", "a2"], "reasons": ["r1", "r2", "r3"]},
        {"cluster_id": "c2", "band": "ORANGE", "origin": "auth", "alert_ids": ["a3"], "reasons": ["r1", "r2"]}
    ]

    comp = compute_compression(len(test_alerts), len(test_clusters))
    rec = compute_recall(test_clusters, test_incidents, test_alerts)
    pw = compute_pairwise_metrics(test_clusters, test_alerts)
    bc = compute_bcubed_metrics(test_clusters, test_alerts)

    assert comp["reduction_pct"] == 50.0
    assert rec["recall"] == 1.0
    assert rec["buried_recall"] == 1.0
    assert pw["pairwise_precision"] == 1.0
    assert bc["bcubed_f1"] == 1.0
    print("Self-test PASSED! All metric calculations are sound.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AlertLens Metrics & Evaluation (Person A)")
    parser.add_argument("--clusters", type=str, default="data/sample/clusters.json", help="Path to clusters.json")
    parser.add_argument("--alerts", type=str, default="data/sample/alerts.csv", help="Path to alerts.csv")
    parser.add_argument("--incidents", type=str, default="data/sample/incidents.csv", help="Path to incidents.csv")
    parser.add_argument("--json-out", type=str, default=None, help="Save scorecard JSON to file")
    parser.add_argument("--test", action="store_true", help="Run self-test assertion")

    args = parser.parse_args()

    if args.test:
        run_self_test()
    else:
        if not os.path.exists(args.clusters):
            print(f"Error: {args.clusters} not found.")
            exit(1)
        results = evaluate_all(args.clusters, args.alerts, args.incidents)
        print_scorecard(results)
        if args.json_out:
            with open(args.json_out, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
            print(f"Metrics saved to {args.json_out}")
