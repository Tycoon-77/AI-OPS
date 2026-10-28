"""
Noise candidate finder (BACKEND_STRUCTURE §5.9).

Algorithm (training period only):
  1. Group alert_groups by (fingerprint_id, service_id) where split='train'
  2. volume = sum(alert_count); incident_involvement = # distinct truth incidents
  3. volume >= 50 AND involvement == 0  → candidate
     involvement >= 1                   → keep  (e.g. N7)
  4. Recommendation rules:
     - CV of inter-alert gaps < 0.3       → raise_threshold
     - >40% repeats within 5 min         → require_consecutive
     - severity >= medium AND involvement=0 → downgrade_severity
     - same template, >= 5 services       → merge_rule
  5. Validate on test week: noise_false_positive_count must == 0
"""
from __future__ import annotations

import json
import sqlite3
import statistics
from datetime import datetime


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _gap_cv(timestamps: list[datetime]) -> float:
    """Coefficient of variation of gaps (in seconds) between consecutive timestamps."""
    if len(timestamps) < 3:
        return 1.0  # not enough data → don't call it periodic
    gaps = [(timestamps[i + 1] - timestamps[i]).total_seconds()
            for i in range(len(timestamps) - 1)]
    mean = statistics.mean(gaps)
    if mean == 0:
        return 0.0
    stdev = statistics.stdev(gaps) if len(gaps) > 1 else 0.0
    return stdev / mean


def find_noise_candidates(conn: sqlite3.Connection, run_id: str) -> None:
    """Compute and persist noise candidates for *run_id*."""

    # ------------------------------------------------------------------
    # 1. Aggregate by (fingerprint_id, service_id) on training data
    # ------------------------------------------------------------------
    agg_rows = conn.execute(
        """SELECT ag.fingerprint_id, ag.service_id,
                  SUM(ag.alert_count)                           AS volume,
                  COUNT(DISTINCT ag.truth_incident_id)          AS raw_involvement,
                  MAX(ag.max_severity_num)                      AS max_sev,
                  GROUP_CONCAT(ag.first_ts, '|')               AS all_ts
           FROM alert_groups ag
           WHERE ag.split = 'train'
           GROUP BY ag.fingerprint_id, ag.service_id"""
    ).fetchall()

    # ------------------------------------------------------------------
    # 2. For each fingerprint+service, determine involvement more carefully.
    #    Involvement = distinct incidents where the fingerprint appeared
    #    as a labelled member OR fired on an affected service within 30 min
    #    before incident start (we approximate: any truth_incident_id != NULL).
    # ------------------------------------------------------------------
    candidate_rows: list[dict] = []

    # Load how many distinct services each fingerprint spans
    fp_service_counts: dict[str, int] = {}
    for row in conn.execute(
        "SELECT fingerprint_id, COUNT(DISTINCT service_id) AS svc_count FROM alert_groups GROUP BY fingerprint_id"
    ).fetchall():
        fp_service_counts[row["fingerprint_id"]] = row["svc_count"]

    for row in agg_rows:
        fp_id    = row["fingerprint_id"]
        svc_id   = row["service_id"]
        volume   = row["volume"] or 0
        max_sev  = row["max_sev"] or 1
        all_ts_str = row["all_ts"] or ""

        # real incident_involvement: count non-null truth incidents
        involvement_row = conn.execute(
            """SELECT COUNT(DISTINCT truth_incident_id) AS cnt
               FROM alert_groups
               WHERE fingerprint_id=? AND service_id=? AND split='train'
                 AND truth_incident_id IS NOT NULL""",
            (fp_id, svc_id),
        ).fetchone()
        involvement = involvement_row["cnt"] if involvement_row else 0

        if volume < 50:
            continue  # not voluminous enough to be a noise candidate

        # Recommendation type
        if involvement >= 1:
            rec_type = "keep"
            rec_text = (
                f"This fingerprint preceded {involvement} incident(s). "
                "Do NOT suppress — investigate threshold tuning instead."
            )
        else:
            # Parse timestamps for gap analysis
            ts_list = sorted(
                [_parse_ts(t) for t in all_ts_str.split("|") if t],
                key=lambda x: x,
            )
            cv = _gap_cv(ts_list)
            short_gap_count = sum(
                1 for i in range(len(ts_list) - 1)
                if (ts_list[i + 1] - ts_list[i]).total_seconds() <= 300  # 5 min
            )
            short_gap_pct = short_gap_count / max(len(ts_list) - 1, 1)
            n_services = fp_service_counts.get(fp_id, 1)

            if cv < 0.3:
                rec_type = "raise_threshold"
                rec_text = (
                    f"Fires every ~{int(statistics.mean([(ts_list[i+1]-ts_list[i]).total_seconds() for i in range(len(ts_list)-1)]) / 60 if len(ts_list)>1 else 0)} min "
                    f"(CV={cv:.2f}, very periodic). Raise the alert threshold."
                )
            elif short_gap_pct > 0.4:
                rec_type = "require_consecutive"
                rec_text = (
                    f"{int(short_gap_pct*100)}% of firings repeat within 5 min. "
                    "Require N consecutive breaches before alerting."
                )
            elif max_sev <= 2:
                rec_type = "downgrade_severity"
                rec_text = (
                    f"Fires {volume}x with 0 incident involvement. "
                    "Downgrade severity to info/low or suppress."
                )
            elif n_services >= 5:
                rec_type = "merge_rule"
                rec_text = (
                    f"Same template fires across {n_services} services. "
                    "Merge into one aggregate rule."
                )
            else:
                rec_type = "downgrade_severity"
                rec_text = (
                    f"Fires {volume}x in training period with 0 incident involvement. "
                    "Consider suppressing or downgrading."
                )

        fp_row = conn.execute(
            "SELECT template, source FROM fingerprints WHERE fingerprint_id=?", (fp_id,)
        ).fetchone()
        template = fp_row["template"] if fp_row else fp_id
        source   = fp_row["source"]   if fp_row else "monitoring"
        pattern  = _detect_pattern(volume, involvement, cv if involvement == 0 else 1.0)

        evidence = {
            "volume":               volume,
            "incident_involvement": involvement,
            "max_severity_num":     max_sev,
            "n_services_with_this_fp": fp_service_counts.get(fp_id, 1),
            "source":               source,
        }

        candidate_rows.append({
            "run_id":               run_id,
            "fingerprint_id":       fp_id,
            "service_id":           svc_id,
            "volume":               volume,
            "incident_involvement": involvement,
            "precursor_rate":       round(involvement / volume, 6) if volume else 0.0,
            "pattern":              pattern,
            "recommendation_type":  rec_type,
            "recommendation_text":  rec_text,
            "evidence_json":        json.dumps(evidence),
        })

    # ------------------------------------------------------------------
    # 3. Validate on test week: no candidate should appear in test incident
    # ------------------------------------------------------------------
    test_fp_ids: set[str] = set()
    for row in conn.execute(
        """SELECT DISTINCT ag.fingerprint_id
           FROM alert_groups ag
           WHERE ag.split='test' AND ag.truth_incident_id IS NOT NULL"""
    ).fetchall():
        test_fp_ids.add(row["fingerprint_id"])

    noise_false_positive_count = sum(
        1 for r in candidate_rows
        if r["recommendation_type"] != "keep" and r["fingerprint_id"] in test_fp_ids
    )
    print(
        f"[noise] candidates={len(candidate_rows)}  "
        f"noise_false_positive_count={noise_false_positive_count}"
    )

    # ------------------------------------------------------------------
    # 4. Persist
    # ------------------------------------------------------------------
    with conn:
        conn.execute("DELETE FROM noise_candidates WHERE run_id=?", (run_id,))
        conn.executemany(
            """INSERT INTO noise_candidates
               (run_id,fingerprint_id,service_id,volume,incident_involvement,
                precursor_rate,pattern,recommendation_type,recommendation_text,evidence_json)
               VALUES
               (:run_id,:fingerprint_id,:service_id,:volume,:incident_involvement,
                :precursor_rate,:pattern,:recommendation_type,:recommendation_text,:evidence_json)""",
            candidate_rows,
        )


def _detect_pattern(volume: int, involvement: int, cv: float) -> str:
    if cv < 0.3:
        return "periodic"
    if involvement == 0 and volume > 200:
        return "single_template_wide"
    return "flapping"
