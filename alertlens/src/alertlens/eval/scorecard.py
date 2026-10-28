"""
scorecard.py - stricter, per-incident evaluation (eval-ui, Step 2).

Works on any clusters.json that keeps the agreed format
(cluster_id, band, origin, alert_ids, services, start, end, alert_count, reasons)
and optionally `origin_candidates` (services, best first).

Everything is reported twice:
  scope "all"  -> all incidents in incidents.csv
  scope "test" -> only incidents on/after TEST_START (week 3), cards and alerts in that window

Definitions
  surfaced card        cluster whose band is not BACKGROUND
  card precision       surfaced cards holding >=1 real incident alert / surfaced cards
  cluster purity       real-incident alerts of the card's majority incident / known alerts in the card
  recall (lenient)     incidents with >=1 alert inside any surfaced card
  recall (>=50%)       incidents with >=50% of their alerts inside ONE surfaced card
  origin top-1/top-3   per incident, using the surfaced card that holds most of its alerts;
                       top-3 uses `origin_candidates`, falls back to [origin] when absent
Alert ids that are not in alerts.csv (e.g. stale sample alerts) are ignored and counted.

Python 3.9 compatible.
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set

from alertlens.eval.metrics import (
    compute_bcubed_metrics,
    compute_pairwise_metrics,
    load_alerts,
    load_clusters,
    load_incidents,
)

START_DATE = "2026-03-02"
TEST_START = datetime(2026, 3, 16, tzinfo=timezone.utc)  # week 3, same rule as ingest/load.py


def _ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _truth(alerts: Dict[str, dict], aid: str) -> str:
    return (alerts.get(aid, {}).get("truth_incident_id") or "").strip()


def is_surfaced(cluster: dict) -> bool:
    return str(cluster.get("band", "RED")).upper() != "BACKGROUND"


def _scope(clusters, alerts, incidents, scope):
    """Restrict everything to the requested scope. Returns (clusters, alerts, incidents)."""
    if scope == "all":
        return clusters, alerts, incidents
    inc = {k: v for k, v in incidents.items() if _ts(v["start"]) >= TEST_START}
    al = {k: v for k, v in alerts.items() if _ts(v["timestamp"]) >= TEST_START}
    cl = []
    for c in clusters:
        ids = [a for a in c.get("alert_ids", []) if a in al]
        if ids:
            c2 = dict(c)
            c2["alert_ids"] = ids
            c2["alert_count"] = len(ids)
            cl.append(c2)
    return cl, al, inc


def evaluate(clusters: List[dict], alerts: Dict[str, dict], incidents: Dict[str, dict], scope: str = "all") -> dict:
    clusters, alerts, incidents = _scope(clusters, alerts, incidents, scope)

    foreign = 0
    known: Dict[str, List[str]] = {}
    for c in clusters:
        ids = [a for a in c.get("alert_ids", []) if a in alerts]
        foreign += len(c.get("alert_ids", [])) - len(ids)
        known[c["cluster_id"]] = ids

    surfaced = [c for c in clusters if is_surfaced(c)]
    red_orange = [c for c in surfaced if str(c.get("band")).upper() in ("RED", "ORANGE")]

    # incident -> alert ids
    inc_alerts: Dict[str, Set[str]] = defaultdict(set)
    for aid in alerts:
        t = _truth(alerts, aid)
        if t in incidents:
            inc_alerts[t].add(aid)

    # card precision & purity
    cards_with_incident = 0
    purities = []
    card_rows = []
    for c in surfaced:
        ids = known[c["cluster_id"]]
        counts = Counter(_truth(alerts, a) for a in ids if _truth(alerts, a) in incidents)
        if counts:
            cards_with_incident += 1
            top_inc, top_n = counts.most_common(1)[0]
            purity = top_n / max(len(ids), 1)
            purities.append(purity)
            card_rows.append({"cluster_id": c["cluster_id"], "incident": top_inc,
                              "size": len(ids), "true_alerts": top_n, "purity": round(purity, 4)})

    # per-incident best surfaced card
    per_incident = {}
    recall_any = recall_50 = top1 = top3 = 0
    for inc_id, inc in incidents.items():
        members = inc_alerts.get(inc_id, set())
        best, best_n = None, 0
        any_hit = False
        for c in surfaced:
            n = len(members.intersection(known[c["cluster_id"]]))
            if n:
                any_hit = True
            if n > best_n:
                best, best_n = c, n
        coverage = best_n / len(members) if members else 0.0
        hit50 = coverage >= 0.5
        row = {"type": inc.get("type"), "alerts": len(members), "surfaced_any": any_hit,
               "best_card": best["cluster_id"] if best else None,
               "coverage_in_best_card": round(coverage, 4),
               "purity_of_best_card": round(best_n / max(len(known[best["cluster_id"]]), 1), 4) if best else 0.0,
               "best_card_size": len(known[best["cluster_id"]]) if best else 0}
        recall_any += any_hit
        recall_50 += hit50
        truth_origin = inc.get("root_cause_service")
        if best:
            cands = best.get("origin_candidates") or [best.get("origin")]
            row["origin"] = best.get("origin")
            row["origin_correct_top1"] = best.get("origin") == truth_origin
            row["origin_correct_top3"] = truth_origin in list(cands)[:3]
            top1 += row["origin_correct_top1"]
            top3 += row["origin_correct_top3"]
        else:
            row["origin_correct_top1"] = row["origin_correct_top3"] = False
        row["true_origin"] = truth_origin
        per_incident[inc_id] = row

    n_inc = len(incidents)
    pw = compute_pairwise_metrics(clusters, alerts)
    bc = compute_bcubed_metrics(clusters, alerts)

    def frac(x, d):
        return round(x / d, 4) if d else None

    return {
        "scope": scope,
        "n_incidents": n_inc,
        "n_raw_alerts": len(alerts),
        "foreign_alert_ids_ignored": foreign,
        "cards": len(surfaced),
        "red_orange_cards": len(red_orange),
        "compression_ratio": round(len(alerts) / len(surfaced), 2) if surfaced else None,
        "card_precision": frac(cards_with_incident, len(surfaced)),
        "cards_with_real_incident": cards_with_incident,
        "mean_purity_of_incident_cards": round(statistics.mean(purities), 4) if purities else None,
        "median_purity_of_incident_cards": round(statistics.median(purities), 4) if purities else None,
        "recall_lenient_any_alert": frac(recall_any, n_inc),
        "recall_at_least_50pct_in_one_card": frac(recall_50, n_inc),
        "origin_top1": frac(top1, n_inc),
        "origin_top3": frac(top3, n_inc),
        "origin_top3_uses_candidates": any("origin_candidates" in c for c in surfaced),
        "pairwise_precision": pw.get("pairwise_precision", pw.get("precision")),
        "pairwise_recall": pw.get("pairwise_recall", pw.get("recall")),
        "bcubed_f1": bc.get("bcubed_f1", bc.get("f1")),
        "per_incident": per_incident,
    }


def evaluate_files(clusters_path: str, alerts_path: str, incidents_path: str) -> dict:
    alerts = load_alerts(alerts_path)
    incidents = load_incidents(incidents_path)
    clusters = load_clusters(clusters_path)
    return {
        "all": evaluate(clusters, alerts, incidents, "all"),
        "test": evaluate(clusters, alerts, incidents, "test"),
    }


def print_report(res: dict) -> None:
    keys = ["n_incidents", "n_raw_alerts", "cards", "red_orange_cards", "compression_ratio", "card_precision",
            "mean_purity_of_incident_cards", "recall_lenient_any_alert", "recall_at_least_50pct_in_one_card",
            "pairwise_precision", "pairwise_recall", "bcubed_f1", "origin_top1", "origin_top3"]
    print("%-38s %12s %12s" % ("metric", "all", "test-split"))
    for k in keys:
        print("%-38s %12s %12s" % (k, res["all"].get(k), res["test"].get(k)))
    print("\ntop-3 uses origin_candidates:", res["all"]["origin_top3_uses_candidates"],
          "(if False, top-3 == top-1 by construction)")
    print("foreign alert ids ignored:", res["all"]["foreign_alert_ids_ignored"])
    print("\nPer incident (best surfaced card):")
    for k, r in res["all"]["per_incident"].items():
        print("  %-11s %-15s alerts=%-4s cov=%-6s purity=%-6s size=%-5s origin=%s (true %s) %s" % (
            k, r["type"], r["alerts"], r["coverage_in_best_card"], r["purity_of_best_card"],
            r["best_card_size"], r.get("origin"), r["true_origin"], "TOP1" if r["origin_correct_top1"] else ""))
    print("\nNOTE: the test split has only %d incidents; treat its numbers as anecdotes, not statistics."
          % res["test"]["n_incidents"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--clusters", default="data/clusters.json")
    ap.add_argument("--alerts", default="data/alerts.csv")
    ap.add_argument("--incidents", default="data/incidents.csv")
    ap.add_argument("--json", help="write full result to this path")
    a = ap.parse_args()
    out = evaluate_files(a.clusters, a.alerts, a.incidents)
    print_report(out)
    if a.json:
        with open(a.json, "w") as f:
            json.dump(out, f, indent=2)
