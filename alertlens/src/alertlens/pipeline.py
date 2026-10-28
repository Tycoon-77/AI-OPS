"""
AlertLens pipeline CLI.

Usage:
    # Full run (all three modes), outputs to data/new_run/
    python -m alertlens.pipeline run --all --out-dir data/new_run

    # Single mode
    python -m alertlens.pipeline run --all --mode rules      --out-dir data/new_run
    python -m alertlens.pipeline run --all --mode classifier_rules --out-dir data/new_run
    python -m alertlens.pipeline run --all --mode full       --out-dir data/new_run

    # Single stage
    python -m alertlens.pipeline run --stage ingest  --out-dir data/new_run
    python -m alertlens.pipeline run --stage cluster --mode full --out-dir data/new_run
    python -m alertlens.pipeline run --stage noise   --out-dir data/new_run

IMPORTANT: This pipeline NEVER writes to data/*.json, data/*.db, or
models/pair_lgbm.txt when --out-dir is set.  All outputs go to --out-dir.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from alertlens.api.db import init_db, get_connection
from alertlens.config import settings

_MODES = ("rules", "classifier_rules", "full")


# ---------------------------------------------------------------------------
# Stage functions
# ---------------------------------------------------------------------------

def stage_ingest(
    alerts_csv: str = "data/alerts.csv",
    deps_json: str = "data/dependencies.json",
    incidents_csv: str = "data/incidents.csv",
    out_dir: str = "data/new_run",
    run_id: str | None = None,
) -> str:
    from alertlens.ingest.load import load_data
    if not Path(alerts_csv).exists():
        print(f"[pipeline] {alerts_csv} not found — using sample data")
        alerts_csv    = "data/sample/alerts.csv"
        deps_json     = "data/sample/dependencies.json"
        incidents_csv = "data/sample/incidents.csv"
    return load_data(alerts_csv, deps_json, incidents_csv, run_id=run_id)


def stage_cluster(
    run_id: str,
    mode: str = "rules",
    out_dir: str = "data/new_run",
) -> None:
    conn = get_connection()
    out_json = str(Path(out_dir) / f"clusters_{mode}.json")

    if mode == "rules":
        from alertlens.cluster.correlator import run_rules_baseline
        run_rules_baseline(conn, run_id, split="all", out_json=out_json)
    elif mode == "classifier_rules":
        from alertlens.cluster.correlator import run_classifier_rules
        run_classifier_rules(conn, run_id, split="all", out_json=out_json)
    elif mode == "full":
        from alertlens.cluster.correlator import run_ml_clustering
        run_ml_clustering(conn, run_id, split="all", out_json=out_json)
    else:
        raise ValueError(f"Unknown mode: {mode!r}. Choose from: {_MODES}")

    conn.close()


def stage_noise(run_id: str, out_dir: str = "data/new_run") -> None:
    from alertlens.noise.candidates import find_noise_candidates
    conn = get_connection()
    find_noise_candidates(conn, run_id)

    rows = conn.execute(
        """SELECT nc.*, f.template FROM noise_candidates nc
           JOIN fingerprints f ON f.fingerprint_id = nc.fingerprint_id
           WHERE nc.run_id=?""",
        (run_id,),
    ).fetchall()
    items = []
    for r in rows:
        items.append({
            "fingerprint_id": r["fingerprint_id"],
            "template": r["template"],
            "service": r["service_id"],
            "volume": r["volume"],
            "incident_involvement": r["incident_involvement"],
            "precursor_rate": r["precursor_rate"],
            "recommendation_type": r["recommendation_type"],
            "recommendation_text": r["recommendation_text"],
            "evidence": json.loads(r["evidence_json"] or "{}"),
            "status": "pending",
        })
    out_path = Path(out_dir) / "noise_candidates.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(items, f, indent=2)
    conn.close()


def stage_eval(
    run_id: str,
    mode: str = "rules",
    out_dir: str = "data/new_run",
) -> dict:
    from alertlens.eval.metrics import evaluate_all, print_scorecard
    clusters_json = str(Path(out_dir) / f"clusters_{mode}.json")

    if not Path(clusters_json).exists():
        print(f"[eval] {clusters_json} not found — skipping eval for mode={mode}")
        return {}

    alerts_path    = "data/alerts.csv"    if Path("data/alerts.csv").exists()    else "data/sample/alerts.csv"
    incidents_path = "data/incidents.csv" if Path("data/incidents.csv").exists() else "data/sample/incidents.csv"

    results = evaluate_all(clusters_json, alerts_path, incidents_path)
    print(f"\n=== SCORECARD: mode={mode} ===")
    print_scorecard(results)

    # Write metrics JSON to out_dir
    comp = results.get("compression", {})
    rec  = results.get("recall", {})
    pw   = results.get("pairwise", {})
    bc   = results.get("bcubed", {})
    orig = results.get("origin", {})
    exp  = results.get("explainability", {})

    flat = {
        "run_id":              run_id,
        "mode":                mode,
        "compression_ratio":   comp.get("compression_ratio", 0.0),
        "reduction_pct":       comp.get("reduction_pct", 0.0),
        "surfaced_clusters":   comp.get("surfaced_clusters", 0),
        "recall":              rec.get("recall", 0.0),
        "buried_recall":       rec.get("buried_recall", 0.0),
        "heldout_recall":      rec.get("heldout_recall", 0.0),
        "pairwise_precision":  pw.get("pairwise_precision", 0.0),
        "pairwise_recall":     pw.get("pairwise_recall", 0.0),
        "bcubed_f1":           bc.get("bcubed_f1", 0.0),
        "origin_top1":         orig.get("origin_top1_accuracy", 0.0),
        "origin_top3":         orig.get("origin_top3_accuracy", 0.0),
        "explainability_pct":  exp.get("explainability_pct", 0.0),
    }
    metrics_path = Path(out_dir) / f"metrics_{mode}.json"
    with open(metrics_path, "w") as f:
        json.dump(flat, f, indent=2)
    print(f"[eval] Metrics → {metrics_path}")
    return results


def run_all(
    mode: str = "rules",
    out_dir: str = "data/new_run",
) -> str:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    print("=" * 60)
    print(f"AlertLens Pipeline — mode={mode}  out_dir={out_dir}")
    print("=" * 60)

    print("\n[1/4] Ingest …")
    run_id = stage_ingest(out_dir=out_dir)

    print(f"\n[2/4] Cluster  run_id={run_id}  mode={mode} …")
    stage_cluster(run_id, mode=mode, out_dir=out_dir)

    print("\n[3/4] Noise candidates …")
    stage_noise(run_id, out_dir=out_dir)

    print("\n[4/4] Evaluate & Scorecard …")
    stage_eval(run_id, mode=mode, out_dir=out_dir)

    elapsed = round(time.time() - t0, 1)
    print(f"\n✅  Pipeline complete.  run_id={run_id}  elapsed={elapsed}s")
    return run_id


def run_all_modes(out_dir: str = "data/new_run") -> str:
    """Run all three modes and print a side-by-side comparison."""
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    print("=" * 60)
    print(f"AlertLens Pipeline — ALL MODES  out_dir={out_dir}")
    print("=" * 60)

    print("\n[1/4] Ingest …")
    run_id = stage_ingest(out_dir=out_dir)

    print("\n[2/4] Noise candidates …")
    stage_noise(run_id, out_dir=out_dir)

    results = {}
    for mode in _MODES:
        print(f"\n{'='*40}")
        print(f"[Cluster + Eval] mode={mode}")
        print(f"{'='*40}")
        stage_cluster(run_id, mode=mode, out_dir=out_dir)
        results[mode] = stage_eval(run_id, mode=mode, out_dir=out_dir)

    # Side-by-side comparison
    print("\n" + "=" * 70)
    print("SIDE-BY-SIDE SCORECARD COMPARISON")
    print("=" * 70)
    metrics_keys = [
        ("surfaced_clusters", "Surfaced cards"),
        ("compression_ratio", "Compression ratio"),
        ("recall",            "Recall"),
        ("pairwise_precision","Pairwise precision"),
        ("bcubed_f1",         "B³ F1"),
        ("origin_top1",       "Origin top-1"),
    ]
    header = f"{'Metric':30s}" + "".join(f"{m:>20s}" for m in _MODES)
    print(header)
    print("-" * (30 + 20 * len(_MODES)))
    for key, label in metrics_keys:
        row = f"{label:30s}"
        for mode in _MODES:
            r = results.get(mode, {})
            comp = r.get("compression", {})
            rec  = r.get("recall", {})
            pw   = r.get("pairwise", {})
            bc   = r.get("bcubed", {})
            orig = r.get("origin", {})
            mapping = {
                "surfaced_clusters": comp.get("surfaced_clusters", 0),
                "compression_ratio": comp.get("compression_ratio", 0),
                "recall":            rec.get("recall", 0),
                "pairwise_precision": pw.get("pairwise_precision", 0),
                "bcubed_f1":         bc.get("bcubed_f1", 0),
                "origin_top1":       orig.get("origin_top1_accuracy", 0),
            }
            val = mapping.get(key, 0)
            row += f"{val:>20.4f}" if isinstance(val, float) else f"{val:>20}"
        print(row)

    print(f"\n✅  All modes complete.  run_id={run_id}")
    return run_id


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="alertlens.pipeline")
    sub = parser.add_subparsers(dest="cmd")

    run_p = sub.add_parser("run")
    run_p.add_argument("--all",     action="store_true")
    run_p.add_argument("--stage",   choices=["ingest", "cluster", "noise"])
    run_p.add_argument("--run-id",  default=None)
    run_p.add_argument(
        "--mode", choices=list(_MODES) + ["all_modes"],
        default="rules",
        help="Clustering mode. Use 'all_modes' to run rules + classifier_rules + full.",
    )
    run_p.add_argument(
        "--out-dir", default="data/new_run",
        help="Output directory for JSON files (never overwrites data/*.json or data/*.db).",
    )

    args = parser.parse_args(argv)

    if args.cmd == "run":
        out_dir = args.out_dir
        Path(out_dir).mkdir(parents=True, exist_ok=True)

        if args.all:
            if args.mode == "all_modes":
                run_all_modes(out_dir=out_dir)
            else:
                run_all(mode=args.mode, out_dir=out_dir)

        elif args.stage == "ingest":
            print(stage_ingest(out_dir=out_dir, run_id=args.run_id))

        elif args.stage == "cluster":
            run_id = args.run_id
            if not run_id:
                conn = get_connection()
                row = conn.execute("SELECT run_id FROM runs ORDER BY created_at DESC LIMIT 1").fetchone()
                if not row:
                    print("No runs found — run ingest first.")
                    sys.exit(1)
                run_id = row["run_id"]
                conn.close()
            stage_cluster(run_id, mode=args.mode, out_dir=out_dir)

        elif args.stage == "noise":
            conn = get_connection()
            row = conn.execute("SELECT run_id FROM runs ORDER BY created_at DESC LIMIT 1").fetchone()
            if not row:
                print("No runs found.")
                sys.exit(1)
            run_id = row["run_id"]
            conn.close()
            stage_noise(run_id, out_dir=out_dir)

        else:
            parser.print_help()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
