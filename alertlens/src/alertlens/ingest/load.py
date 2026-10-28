"""
Ingest loader — reads sample/real CSV + JSON files, applies redaction,
fingerprinting, deduplication, then persists everything to SQLite.

Uses only stdlib (csv module) so it works before pip install completes.
When pandas is available it will also be importable, but is not required here.
"""
from __future__ import annotations

import csv
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from alertlens.api.db import init_db
from alertlens.config import settings
from alertlens.ingest.dedupe import dedupe_alerts
from alertlens.ingest.fingerprint import fingerprint_id, make_template
from alertlens.ingest.redact import redact

SEV_MAP = {"low": 1, "medium": 2, "high": 3, "critical": 4}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _week_split(ts_str: str, start_date: str = "2026-03-02") -> str:
    """Return 'train' for weeks 1-2, 'test' for week 3."""
    ts    = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    start = datetime.fromisoformat(start_date + "T00:00:00+00:00")
    delta = (ts - start).days
    return "test" if delta >= 14 else "train"


def _read_csv(path: str) -> list[dict]:
    """Read a CSV file into a list of dicts (stripped values, empty→'')."""
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [
            {k.strip(): (v if v is not None else "").strip()
             for k, v in row.items() if k is not None}
            for row in reader
        ]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def load_data(
    alerts_csv: str,
    deps_json: str,
    incidents_csv: str | None = None,
    run_id: str | None = None,
) -> str:
    """
    Full ingest pass:
      1. Init DB schema
      2. Upsert services + edges from dependencies.json
      3. Read alerts.csv → redact → fingerprint → insert alerts + fingerprints
      4. Deduplicate → insert alert_groups, back-fill alerts.group_id
      5. Read incidents.csv (ground truth) → insert incidents_truth
      6. Create a run record
    Returns run_id.
    """
    conn = init_db()
    salt = settings.redaction_salt

    if run_id is None:
        run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    # ------------------------------------------------------------------
    # 1. Services + edges
    # ------------------------------------------------------------------
    with open(deps_json) as f:
        deps = json.load(f)

    # Standard service tiers lookup (Tier 0: infra, Tier 1: platform, Tier 3: edge, Tier 2: business)
    service_tiers_map = {
        "db-primary": 0, "db-replica": 0, "cache-redis": 0, "msg-queue": 0,
        "dns": 0, "object-storage": 0, "log-cluster": 0, "secrets-vault": 0,
        "auth-service": 1, "identity": 1, "config-service": 1, "feature-flags": 1,
        "rate-limiter": 1, "scheduler": 1, "search-index": 1, "email-gateway": 1,
        "sms-gateway": 1, "payments-gateway": 1, "file-service": 1, "geo-service": 1,
        "audit-log": 1, "service-mesh": 1,
        "api-gateway": 3, "web-frontend": 3, "mobile-bff": 3, "admin-portal": 3,
        "partner-gateway": 3, "cdn-origin": 3, "graphql-gateway": 3, "merchant-api": 3,
        "webhook-dispatcher": 3, "public-api": 3, "iot-gateway": 3, "internal-proxy": 3,
        "ingress-controller": 3, "checkout-web": 3, "search-api": 3, "pos-gateway": 3,
        "stream-consumer": 3, "event-broker": 3,
    }

    if isinstance(deps, dict) and "services" in deps and "edges" in deps:
        # Schema style {"services": [...], "edges": [...]}
        services_to_insert = [
            (s["id"], s["tier"], s.get("team"), s.get("criticality", 3))
            for s in deps["services"]
        ]
        edges_to_insert = [(e["src"], e["dst"]) for e in deps["edges"]]
        known_services = {s["id"] for s in deps["services"]}
    else:
        # Adjacency map style {"upstream_dependency": ["downstream_caller", ...]}
        all_nodes = set(deps.keys())
        for u, callers in deps.items():
            for v in callers:
                all_nodes.add(v)
        services_to_insert = []
        for s in all_nodes:
            tier = service_tiers_map.get(s, 2)
            services_to_insert.append((s, tier, "engineering", 5 if tier == 0 else 3))
        edges_to_insert = []
        for u, callers in deps.items():
            for v in callers:
                # v depends on u: src=v, dst=u
                edges_to_insert.append((v, u))
        known_services = all_nodes

    with conn:
        conn.executemany(
            "INSERT OR REPLACE INTO services (service_id, tier, team, criticality) VALUES (?,?,?,?)",
            services_to_insert,
        )
        conn.executemany(
            "INSERT OR REPLACE INTO service_edges (src_service, dst_service) VALUES (?,?)",
            edges_to_insert,
        )

    # ------------------------------------------------------------------
    # 2. Alerts
    # ------------------------------------------------------------------
    raw_rows = _read_csv(alerts_csv)
    alert_rows: list[dict] = []
    fp_cache: dict[str, dict] = {}

    for row in raw_rows:
        svc = row.get("service", "").strip()
        ts  = row.get("timestamp", row.get("ts", "")).strip()

        if not svc or not ts:
            continue

        if svc not in known_services:
            tier = service_tiers_map.get(svc, 2)
            with conn:
                conn.execute(
                    "INSERT OR IGNORE INTO services (service_id,tier,team,criticality) VALUES (?,?,'unknown',3)",
                    (svc, tier),
                )
            known_services.add(svc)

        src      = row.get("source", "monitoring")
        sev      = row.get("severity", "low")
        msg_raw  = row.get("message", "")
        # Support both 'incident_id' and 'truth_incident_id'
        truth_id = (row.get("truth_incident_id", "") or row.get("incident_id", "")).strip() or None
        split    = _week_split(ts)

        msg_redacted = redact(msg_raw, salt)
        template     = make_template(msg_redacted)
        fp_id        = fingerprint_id(src, template)

        if fp_id not in fp_cache:
            fp_cache[fp_id] = {
                "fingerprint_id": fp_id,
                "template":       template,
                "alert_type":     None,
                "source":         src,
                "first_seen":     ts,
                "volume_total":   0,
            }
        fp_cache[fp_id]["volume_total"] += 1

        alert_rows.append({
            "alert_id":          row.get("alert_id", f"auto_{len(alert_rows)}"),
            "ts":                ts,
            "source":            src,
            "service_id":        svc,
            "severity":          sev,
            "severity_num":      SEV_MAP.get(sev, 1),
            "message_raw":       msg_raw,
            "message_redacted":  msg_redacted,
            "fingerprint_id":    fp_id,
            "group_id":          None,
            "split":             split,
            "truth_incident_id": truth_id,
            "truth_kind":        "incident" if truth_id else "noise",
        })

    # Persist fingerprints
    with conn:
        conn.executemany(
            """INSERT OR REPLACE INTO fingerprints
               (fingerprint_id,template,alert_type,source,first_seen,volume_total)
               VALUES (:fingerprint_id,:template,:alert_type,:source,:first_seen,:volume_total)""",
            list(fp_cache.values()),
        )

    # ------------------------------------------------------------------
    # 3. Deduplication (fills alert["group_id"] in memory)
    # ------------------------------------------------------------------
    groups = dedupe_alerts(alert_rows, dedup_window_min=settings.dedup_window_min)

    with conn:
        conn.executemany(
            """INSERT OR REPLACE INTO alert_groups
               (group_id,fingerprint_id,service_id,source,
                first_ts,last_ts,alert_count,max_severity_num,split,truth_incident_id)
               VALUES (:group_id,:fingerprint_id,:service_id,:source,
                       :first_ts,:last_ts,:alert_count,:max_severity_num,:split,:truth_incident_id)""",
            groups,
        )
        conn.executemany(
            """INSERT OR REPLACE INTO alerts
               (alert_id,ts,source,service_id,severity,severity_num,
                message_raw,message_redacted,fingerprint_id,group_id,split,
                truth_incident_id,truth_kind)
               VALUES (:alert_id,:ts,:source,:service_id,:severity,:severity_num,
                       :message_raw,:message_redacted,:fingerprint_id,:group_id,:split,
                       :truth_incident_id,:truth_kind)""",
            alert_rows,
        )

    # ------------------------------------------------------------------
    # 4. Ground truth incidents
    # ------------------------------------------------------------------
    if incidents_csv and Path(incidents_csv).exists():
        inc_rows_raw = _read_csv(incidents_csv)
        inc_rows = []
        for r in inc_rows_raw:
            svc = r.get("root_cause_service", "")
            if svc and svc not in known_services:
                tier = service_tiers_map.get(svc, 2)
                with conn:
                    conn.execute(
                        "INSERT OR IGNORE INTO services (service_id,tier,team,criticality) VALUES (?,?,'unknown',3)",
                        (svc, tier),
                    )
                known_services.add(svc)

            start_ts = r.get("start", "")
            buried_val = str(r.get("buried", "0")).strip().lower()
            buried = 1 if buried_val in ("1", "true") else 0
            split = r.get("split", "") or _week_split(start_ts)

            inc_rows.append({
                "incident_id":             r.get("incident_id", ""),
                "type":                    r.get("type", "unknown"),
                "start_ts":                start_ts,
                "end_ts":                  r.get("end", ""),
                "root_cause_service":      svc,
                "root_cause_description":  r.get("root_cause_description", f"{r.get('type','')} on {svc}"),
                "buried":                  buried,
                "split":                   split,
            })
        with conn:
            conn.executemany(
                """INSERT OR REPLACE INTO incidents_truth
                   (incident_id,type,start_ts,end_ts,root_cause_service,
                    root_cause_description,buried,split)
                   VALUES (:incident_id,:type,:start_ts,:end_ts,:root_cause_service,
                           :root_cause_description,:buried,:split)""",
                inc_rows,
            )

    # ------------------------------------------------------------------
    # 5. Run record
    # ------------------------------------------------------------------
    config_snap = {
        "surface_threshold": settings.surface_threshold,
        "pair_threshold":    settings.pair_threshold,
        "pair_window_min":   settings.pair_window_min,
        "dedup_window_min":  settings.dedup_window_min,
        "seed":              settings.seed,
    }
    with conn:
        conn.execute(
            """INSERT OR REPLACE INTO runs (run_id,created_at,seed,config_json)
               VALUES (?,?,?,?)""",
            (run_id, _utcnow(), settings.seed, json.dumps(config_snap)),
        )

    conn.close()
    print(f"[load] run_id={run_id}  alerts={len(alert_rows)}  groups={len(groups)}")
    return run_id
