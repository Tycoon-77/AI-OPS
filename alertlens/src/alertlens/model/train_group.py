"""
Group-level LightGBM incident classifier (Step 2).

Label   : 1 if alert group belongs to a real incident (truth_incident_id IS NOT NULL)
Training: split == 'train' groups only.
Val     : 80/20 stratified random split WITHIN train to tune thresholds
          (never on test).
Test    : split == 'test' — evaluation only.

Saves booster to models/group_lgbm.txt.

Usage:
    cd alertlens && python -m alertlens.model.train_group
    # or with custom output:
    cd alertlens && python -m alertlens.model.train_group --out models/group_lgbm.txt
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

from alertlens.api.db import get_connection
from alertlens.features.group_features import GROUP_FEATURE_NAMES, build_group_features


def _report(label: str, y_true: np.ndarray, probs: np.ndarray, thresholds=(0.3, 0.4, 0.5)) -> dict:
    auc = float(roc_auc_score(y_true, probs))
    prauc = float(average_precision_score(y_true, probs))
    n_pos = int(y_true.sum())
    n_neg = int((y_true == 0).sum())
    print(f"\n[{label}]  n={len(y_true)}  pos={n_pos}  neg={n_neg}")
    print(f"  ROC-AUC={auc:.4f}  PR-AUC={prauc:.4f}")
    rows = {}
    for thr in thresholds:
        pred = (probs >= thr).astype(int)
        rep = classification_report(y_true, pred, digits=4, zero_division=0, output_dict=True)
        pos_m = rep.get("1", {})
        p = pos_m.get("precision", 0.0)
        r = pos_m.get("recall", 0.0)
        f = pos_m.get("f1-score", 0.0)
        print(f"  thr={thr:.2f}  P={p:.4f}  R={r:.4f}  F1={f:.4f}")
        rows[thr] = {"precision": p, "recall": r, "f1": f}
    return {"auc": auc, "prauc": prauc, "thresholds": rows}


def train_group_model(
    model_out: str = "models/group_lgbm.txt",
    val_fraction: float = 0.20,
    random_state: int = 42,
) -> dict:
    t0 = time.time()
    conn = get_connection()

    # ------------------------------------------------------------------ #
    # Build features — train split
    # ------------------------------------------------------------------ #
    print("[train_group] Loading train split features …")
    X_all, y_all, gids_all = build_group_features(conn, split="train")
    print(f"  train groups: {len(y_all)}  pos={y_all.sum()}  neg={(y_all==0).sum()}")

    # 80/20 stratified split within train for validation (threshold tuning)
    X_tr, X_val, y_tr, y_val = train_test_split(
        X_all, y_all,
        test_size=val_fraction,
        stratify=y_all,
        random_state=random_state,
    )
    print(f"  sub-train={len(y_tr)}  val={len(y_val)}")

    # ------------------------------------------------------------------ #
    # Train LightGBM
    # ------------------------------------------------------------------ #
    clf = lgb.LGBMClassifier(
        n_estimators=500,
        learning_rate=0.04,
        num_leaves=31,
        min_child_samples=10,
        subsample=0.8,
        colsample_bytree=0.8,
        class_weight="balanced",
        random_state=random_state,
        n_jobs=-1,
        verbose=-1,
    )
    clf.fit(
        X_tr, y_tr,
        eval_set=[(X_val, y_val)],
        callbacks=[
            lgb.early_stopping(stopping_rounds=40, verbose=False),
            lgb.log_evaluation(period=-1),
        ],
    )
    best_iter = clf.best_iteration_
    print(f"  best_iteration={best_iter}")

    # ------------------------------------------------------------------ #
    # Val metrics + pick best threshold
    # ------------------------------------------------------------------ #
    val_probs = clf.predict_proba(X_val)[:, 1]
    val_metrics = _report("VAL", y_val, val_probs, thresholds=(0.2, 0.3, 0.4, 0.5, 0.6))

    # Grid-search best F1 threshold on val (never test)
    best_thr, best_f1 = 0.3, 0.0
    for t_int in range(10, 70, 5):
        thr = t_int / 100
        pred = (val_probs >= thr).astype(int)
        rep = classification_report(y_val, pred, digits=4, zero_division=0, output_dict=True)
        f1 = rep.get("1", {}).get("f1-score", 0.0)
        if f1 > best_f1:
            best_f1 = f1
            best_thr = thr
    print(f"\n  Best threshold (val F1={best_f1:.4f}): {best_thr:.2f}")

    # ------------------------------------------------------------------ #
    # Test metrics — evaluation ONLY
    # ------------------------------------------------------------------ #
    print("\n[train_group] Loading test split features …")
    X_test, y_test, gids_test = build_group_features(conn, split="test")
    print(f"  test groups: {len(y_test)}  pos={y_test.sum()}  neg={(y_test==0).sum()}")

    test_probs = clf.predict_proba(X_test)[:, 1]
    test_metrics = _report(
        "TEST", y_test, test_probs,
        thresholds=(0.2, best_thr, 0.4, 0.5),
    )

    # Per-incident breakdown (4 test incidents — n is small, interpret with caution)
    print("\n  Per-incident recall on TEST (n_incidents=4, interpret with caution):")
    from alertlens.api.db import get_connection as _gc
    rows = conn.execute(
        """SELECT i.incident_id, i.type, ag.group_id, ag.truth_incident_id
           FROM incidents_truth i
           JOIN alert_groups ag ON ag.truth_incident_id = i.incident_id
           WHERE i.split='test'"""
    ).fetchall()
    from collections import defaultdict
    inc_gids: dict = defaultdict(set)
    for r in rows:
        inc_gids[r["incident_id"]].add(r["group_id"])
    gid_to_idx = {gid: idx for idx, gid in enumerate(gids_test)}
    for inc_id, gid_set in sorted(inc_gids.items()):
        idxs = [gid_to_idx[g] for g in gid_set if g in gid_to_idx]
        if not idxs:
            continue
        inc_probs = test_probs[idxs]
        inc_y = y_test[idxs]
        recalled = (inc_probs >= best_thr).sum()
        itype = conn.execute(
            "SELECT type FROM incidents_truth WHERE incident_id=?", (inc_id,)
        ).fetchone()["type"]
        print(
            f"    {inc_id} ({itype}): {recalled}/{len(idxs)} groups recalled "
            f"at thr={best_thr:.2f}"
        )

    # ------------------------------------------------------------------ #
    # Feature importance
    # ------------------------------------------------------------------ #
    importances = {n: int(v) for n, v in zip(GROUP_FEATURE_NAMES, clf.feature_importances_)}
    top_feats = sorted(importances.items(), key=lambda x: x[1], reverse=True)
    print("\n  Top features:", top_feats[:8])

    # ------------------------------------------------------------------ #
    # Save model
    # ------------------------------------------------------------------ #
    out_path = Path(model_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    clf.booster_.save_model(str(out_path))
    print(f"\n  Model saved → {out_path}")

    conn.close()
    return {
        "n_train": int(len(y_tr)),
        "n_val":   int(len(y_val)),
        "n_test":  int(len(y_test)),
        "val_auc":    round(val_metrics["auc"], 4),
        "val_prauc":  round(val_metrics["prauc"], 4),
        "test_auc":   round(test_metrics["auc"], 4),
        "test_prauc": round(test_metrics["prauc"], 4),
        "best_threshold_from_val": best_thr,
        "top_features": top_feats,
        "model_path": str(out_path),
        "time_s": round(time.time() - t0, 2),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="models/group_lgbm.txt")
    args = ap.parse_args()
    res = train_group_model(model_out=args.out)
    print("\n=== GROUP MODEL TRAINING COMPLETE ===")
    for k, v in res.items():
        if k != "top_features":
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
