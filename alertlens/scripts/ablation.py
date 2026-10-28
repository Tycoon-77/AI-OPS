"""Compare clusters.json variants in one table (eval-ui, Step 3).

Run from alertlens/:  PYTHONPATH=src python scripts/ablation.py [--json out.json]

Rows (skipped if the file is missing):
  rules baseline (measured)   data/baseline/clusters_rules.json   <- the committed rules path, measured
  rules (new run)             data/new_run/clusters_rules.json
  classifier + rules          data/new_run/clusters_classifier_rules.json
  full                        data/new_run/clusters_full.json
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from alertlens.eval.scorecard import evaluate_files  # noqa: E402

VARIANTS = [
    ("rules baseline (measured)", "data/baseline/clusters_rules.json"),
    ("rules (new run)", "data/new_run/clusters_rules.json"),
    ("classifier + rules", "data/new_run/clusters_classifier_rules.json"),
    ("full", "data/new_run/clusters_full.json"),
]
COLS = [("cards", "cards"), ("RO", "red_orange_cards"), ("cardP", "card_precision"), ("purity", "mean_purity_of_incident_cards"),
        ("rec_any", "recall_lenient_any_alert"), ("rec50", "recall_at_least_50pct_in_one_card"),
        ("pairP", "pairwise_precision"), ("bcF1", "bcubed_f1"), ("top1", "origin_top1"), ("top3", "origin_top3")]


def fmt(v):
    return "-" if v is None else (f"{v:.3f}" if isinstance(v, float) else str(v))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    ap.add_argument("--alerts", default="data/alerts.csv")
    ap.add_argument("--incidents", default="data/incidents.csv")
    a = ap.parse_args()
    results = {}
    for name, path in VARIANTS:
        if os.path.exists(path):
            results[name] = evaluate_files(path, a.alerts, a.incidents)
        else:
            print(f"[skip] {name}: {path} not found")
    for scope, title in (("all", "ALL 11 incidents"), ("test", "TEST split only (4 incidents, anecdotal)")):
        print(f"\n== {title} ==")
        print("%-28s" % "variant" + "".join("%9s" % c[0] for c in COLS))
        for name, r in results.items():
            print("%-28s" % name + "".join("%9s" % fmt(r[scope].get(k)) for _, k in COLS))
    print("\ncards = surfaced cards, RO = RED+ORANGE cards, cardP = card precision, rec_any = lenient recall,")
    print("rec50 = recall needing >=50% of incident alerts in one card. top3 == top1 unless origin_candidates exists.")
    if a.json:
        json.dump(results, open(a.json, "w"), indent=2)


if __name__ == "__main__":
    main()
