"""Minimal FastAPI stub — gives C something to code against immediately.
Real routes will be added as B's pipeline produces DB rows.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from alertlens.config import settings
from alertlens.api.db import get_connection
from alertlens.api.routes_react import router as react_router

_REPO = Path(__file__).resolve().parents[4]  # repo root (AI-OPS)

app = FastAPI(
    title="AlertLens / SignalIQ API",
    version="1.0.0",
    description="Alert correlation engine — AlertLens hackathon MVP",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include React Frontend API routes (/api/incidents, /api/alerts, /api/health, etc.)
app.include_router(react_router)


def _latest_run(conn: sqlite3.Connection) -> Optional[str]:
    row = conn.execute(
        "SELECT run_id FROM runs ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    return row["run_id"] if row else None


# ---------------------------------------------------------------------------
# Root & Health
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    index_file = _REPO / "alertlens" / "dist" / "index.html"
    if not index_file.exists():
        index_file = _REPO / "frontend" / "dist" / "index.html"
    if index_file.exists():
        return FileResponse(index_file)

    conn = get_connection()
    run_id = _latest_run(conn)
    conn.close()
    return {
        "app": "AlertLens API",
        "status": "online",
        "run_id": run_id,
        "docs_url": "/docs",
        "api_endpoints": [
            "/api/v1/health",
            "/api/v1/summary",
            "/api/v1/incidents",
            "/api/v1/days",
            "/api/v1/metrics",
            "/api/v1/noise-candidates",
            "/api/incidents",
            "/api/alerts",
            "/api/services/graph",
            "/api/analytics/summary",
        ],
    }


@app.get("/api/v1/health")
def health():
    conn = get_connection()
    run_id = _latest_run(conn)
    conn.close()
    return {"status": "ok", "run_id": run_id, "simulated": True}


# ---------------------------------------------------------------------------
# Days
# ---------------------------------------------------------------------------

@app.get("/api/v1/days")
def list_days():
    conn = get_connection()
    run_id = _latest_run(conn)
    if not run_id:
        raise HTTPException(status_code=503, detail="Pipeline not yet run")

    # Distinct days from alerts with counts
    day_rows = conn.execute(
        """SELECT date(ts) AS day, split, COUNT(*) AS raw_alerts
           FROM alerts
           GROUP BY date(ts), split
           ORDER BY day ASC"""
    ).fetchall()

    # Surfaced incident counts per day
    surfaced_per_day = dict(
        conn.execute(
            """SELECT day, COUNT(*) AS cnt
               FROM incidents_pred
               WHERE run_id=? AND surfaced=1
               GROUP BY day""",
            (run_id,),
        ).fetchall()
    )

    # Truth incidents per day
    truth_per_day = {}
    for r in conn.execute(
        "SELECT date(start_ts) AS day, type, buried FROM incidents_truth"
    ).fetchall():
        truth_per_day[r["day"]] = {"type": r["type"], "buried": bool(r["buried"])}

    days = []
    for r in day_rows:
        d = r["day"]
        surfaced = surfaced_per_day.get(d, 0)
        truth = truth_per_day.get(d)
        reduction = (
            round((1.0 - surfaced / max(r["raw_alerts"], 1)) * 100.0, 1)
            if r["raw_alerts"] > 0
            else 0.0
        )
        days.append({
            "day": d,
            "split": r["split"],
            "raw_alerts": r["raw_alerts"],
            "surfaced_incidents": surfaced,
            "reduction_pct": reduction,
            "has_incident": truth is not None,
            "incident_type": truth["type"] if truth else None,
            "is_buried": truth["buried"] if truth else False,
        })

    conn.close()
    return {"run_id": run_id, "items": days, "days": days}


# ---------------------------------------------------------------------------
# Replay Stream
# ---------------------------------------------------------------------------

@app.get("/api/v1/replay/{day}")
def replay_day(day: str):
    conn = get_connection()
    run_id = _latest_run(conn)
    if not run_id:
        raise HTTPException(status_code=503, detail="Pipeline not yet run")

    # Get all alerts for this day ordered by timestamp
    alert_rows = conn.execute(
        """SELECT alert_id, ts, service_id, severity, source
           FROM alerts
           WHERE date(ts)=?
           ORDER BY ts ASC""",
        (day,),
    ).fetchall()

    if not alert_rows:
        conn.close()
        raise HTTPException(status_code=404, detail=f"No alerts found for day {day}")

    # Get surfaced incidents on this day
    inc_rows = conn.execute(
        """SELECT * FROM incidents_pred
           WHERE run_id=? AND day=? AND surfaced=1
           ORDER BY first_ts ASC""",
        (run_id, day),
    ).fetchall()

    events = []
    start_ts = alert_rows[0]["ts"]
    end_ts = alert_rows[-1]["ts"]

    # Batch alerts every 30 simulated seconds
    from datetime import datetime
    raw_counter = 0

    # Index incidents by first_ts and last_ts
    surfaced_fired = set()

    for r in alert_rows:
        raw_counter += 1
        t = r["ts"]

        # Emit alert milestone every 20 alerts
        if raw_counter % 20 == 1 or raw_counter == len(alert_rows):
            events.append({
                "t": t,
                "type": "alert",
                "raw_total": raw_counter,
                "service": r["service_id"],
                "severity": r["severity"],
            })

        # Check if an incident should surface at or before t
        for inc in inc_rows:
            inc_id = inc["incident_pred_id"]
            if inc_id not in surfaced_fired and inc["first_ts"] <= t:
                surfaced_fired.add(inc_id)
                events.append({
                    "t": inc["surfaced_ts"] or t,
                    "type": "incident_surfaced",
                    "incident_id": inc_id,
                    "title": inc["title"],
                    "band": inc["band"],
                    "priority_score": inc["priority_score"],
                })
                if inc["origin_service"]:
                    events.append({
                        "t": inc["surfaced_ts"] or t,
                        "type": "origin_set",
                        "incident_id": inc_id,
                        "origin_service": inc["origin_service"],
                    })

    # Sort events chronologically
    events.sort(key=lambda x: x["t"])

    conn.close()
    return {
        "run_id": run_id,
        "day": day,
        "start": start_ts,
        "end": end_ts,
        "total_alerts": len(alert_rows),
        "total_incidents": len(inc_rows),
        "events": events[:2000],
    }


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

@app.get("/api/v1/summary")
def summary(day: Optional[str] = None, split: Optional[str] = None):
    conn = get_connection()
    run_id = _latest_run(conn)
    if not run_id:
        raise HTTPException(status_code=503, detail="Pipeline not yet run")

    where = "WHERE run_id=? AND surfaced=1"
    params: list = [run_id]
    if day:
        where += " AND day=?"
        params.append(day)

    surfaced = conn.execute(
        f"SELECT COUNT(*) FROM incidents_pred {where}", params
    ).fetchone()[0]

    raw_clauses = []
    raw_params = []
    if split and split.lower() != "all":
        raw_clauses.append("split=?")
        raw_params.append(split)
    if day:
        raw_clauses.append("date(first_ts)=?")
        raw_params.append(day)
    raw_where = ("WHERE " + " AND ".join(raw_clauses)) if raw_clauses else ""

    raw_alerts = conn.execute(
        f"SELECT COALESCE(SUM(alert_count),0) FROM alert_groups {raw_where}", raw_params
    ).fetchone()[0]

    reduction = round((1 - surfaced / max(raw_alerts, 1)) * 100, 1) if raw_alerts else 0

    conn.close()
    return {
        "run_id":             run_id,
        "day":                day,
        "raw_alerts":         raw_alerts,
        "surfaced_incidents": surfaced,
        "reduction_pct":      reduction,
    }


# ---------------------------------------------------------------------------
# Incidents list
# ---------------------------------------------------------------------------

@app.get("/api/v1/incidents")
def list_incidents(
    day: Optional[str] = None,
    band: Optional[str] = None,
    include_background: bool = False,
):
    conn = get_connection()
    run_id = _latest_run(conn)
    if not run_id:
        raise HTTPException(status_code=503, detail="Pipeline not yet run")

    clauses = ["run_id=?"]
    params: list = [run_id]

    if day:
        clauses.append("day=?")
        params.append(day)
    if band:
        clauses.append("band=?")
        params.append(band.upper())
    if not include_background:
        clauses.append("surfaced=1")

    where = " AND ".join(clauses)
    rows = conn.execute(
        f"""SELECT incident_pred_id, title, band, first_ts, last_ts,
                   origin_service, n_services, n_alerts_raw, priority_score,
                   surface_reason, reasons_json, surfaced
            FROM incidents_pred WHERE {where}
            ORDER BY priority_score DESC""",
        params,
    ).fetchall()

    items = []
    for r in rows:
        reasons = json.loads(r["reasons_json"] or "[]")
        reason_summary = reasons[0]["text"] if reasons else ""
        items.append({
            "incident_id":    r["incident_pred_id"],
            "title":          r["title"],
            "band":           r["band"],
            "first_ts":       r["first_ts"],
            "last_ts":        r["last_ts"],
            "origin_service": r["origin_service"],
            "n_services":     r["n_services"],
            "n_alerts_raw":   r["n_alerts_raw"],
            "priority_score": r["priority_score"],
            "surface_reason": r["surface_reason"],
            "reason_summary": reason_summary,
            "status":         "new",
        })

    conn.close()
    return {"run_id": run_id, "items": items}


# ---------------------------------------------------------------------------
# Incident detail
# ---------------------------------------------------------------------------

@app.get("/api/v1/incidents/{incident_id}")
def incident_detail(incident_id: str):
    conn = get_connection()
    run_id = _latest_run(conn)

    row = conn.execute(
        "SELECT * FROM incidents_pred WHERE incident_pred_id=? AND run_id=?",
        (incident_id, run_id),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Incident not found"})

    inc = dict(row)
    reasons = json.loads(inc.get("reasons_json") or "[]")

    # Timeline: member groups
    members = conn.execute(
        """SELECT im.group_id, im.origin_rank, im.origin_score, im.dep_path_from_origin,
                  ag.first_ts, ag.service_id, ag.source, ag.max_severity_num, ag.alert_count,
                  f.template
           FROM incident_members im
           JOIN alert_groups ag ON ag.group_id = im.group_id
           JOIN fingerprints f  ON f.fingerprint_id = ag.fingerprint_id
           WHERE im.run_id=? AND im.incident_pred_id=?
           ORDER BY im.origin_rank""",
        (run_id, incident_id),
    ).fetchall()

    sev_name = {1: "low", 2: "medium", 3: "high", 4: "critical"}
    timeline = [
        {
            "group_id":    m["group_id"],
            "ts":          m["first_ts"],
            "service":     m["service_id"],
            "severity":    sev_name.get(m["max_severity_num"], "low"),
            "source":      m["source"],
            "message":     m["template"],
            "count":       m["alert_count"],
            "origin_rank": m["origin_rank"],
        }
        for m in members
    ]

    # Services involved
    services = conn.execute("SELECT * FROM services").fetchall()
    svc_ids_in_cluster = {m["service_id"] for m in members}
    if inc["origin_service"]:
        svc_ids_in_cluster.add(inc["origin_service"])

    edges = conn.execute("SELECT * FROM service_edges").fetchall()

    graph_nodes = [
        {
            "id":   s["service_id"],
            "tier": s["tier"],
            "role": ("origin" if s["service_id"] == inc["origin_service"]
                     else "affected" if s["service_id"] in svc_ids_in_cluster
                     else "other"),
        }
        for s in services
        if s["service_id"] in svc_ids_in_cluster or s["service_id"] == inc["origin_service"]
    ]
    graph_edges = [
        {"src": e["src_service"], "dst": e["dst_service"], "on_path": True}
        for e in edges
        if e["src_service"] in svc_ids_in_cluster and e["dst_service"] in svc_ids_in_cluster
    ]

    conn.close()
    return {
        "incident_id":   inc["incident_pred_id"],
        "title":         inc["title"],
        "band":          inc["band"],
        "priority_score": inc["priority_score"],
        "origin": {
            "service":  inc["origin_service"],
            "group_id": inc["origin_group_id"],
            "score":    inc["origin_score"],
        },
        "stats": {
            "first_ts":       inc["first_ts"],
            "last_ts":        inc["last_ts"],
            "n_alerts_raw":   inc["n_alerts_raw"],
            "n_services":     len(svc_ids_in_cluster),
            "blast_radius":   inc["blast_radius"],
            "max_severity":   sev_name.get(inc["max_severity_num"], "low"),
            "history_match":  inc["history_match"],
            "history_match_type": inc["history_match_type"],
        },
        "timeline": timeline,
        "graph":    {"nodes": graph_nodes, "edges": graph_edges},
        "reasons":  reasons,
        "actions":  [],
    }


# ---------------------------------------------------------------------------
# Noise candidates
# ---------------------------------------------------------------------------

@app.get("/api/v1/noise-candidates")
def noise_candidates(sort: str = "volume"):
    conn = get_connection()
    run_id = _latest_run(conn)
    if not run_id:
        raise HTTPException(status_code=503, detail="Pipeline not yet run")

    order = "volume DESC" if sort == "volume" else "precursor_rate DESC"
    rows = conn.execute(
        f"""SELECT nc.*, f.template
            FROM noise_candidates nc
            JOIN fingerprints f ON f.fingerprint_id = nc.fingerprint_id
            WHERE nc.run_id=?
            ORDER BY {order}""",
        (run_id,),
    ).fetchall()

    items = [
        {
            "fingerprint_id":       r["fingerprint_id"],
            "template":             r["template"],
            "service":              r["service_id"],
            "volume":               r["volume"],
            "incident_involvement": r["incident_involvement"],
            "precursor_rate":       r["precursor_rate"],
            "recommendation_type":  r["recommendation_type"],
            "recommendation_text":  r["recommendation_text"],
            "evidence":             json.loads(r["evidence_json"] or "{}"),
            "status":               "pending",
        }
        for r in rows
    ]
    conn.close()
    return {"run_id": run_id, "items": items}


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

@app.post("/api/v1/actions", status_code=201)
def record_action(body: dict):
    required = {"target_type", "target_id", "action_type"}
    if not required.issubset(body):
        raise HTTPException(status_code=422, detail={"code": "VALIDATION_ERROR", "message": "Missing required fields"})

    target_type = body["target_type"]
    action_type = body["action_type"]
    note        = (body.get("note") or "")[:500]

    # Validate combos
    if target_type == "incident" and action_type not in ("acknowledge", "escalate"):
        raise HTTPException(status_code=422, detail={"code": "VALIDATION_ERROR", "message": "incident only accepts acknowledge/escalate"})
    if target_type == "noise_candidate" and action_type not in ("approve", "ignore"):
        raise HTTPException(status_code=422, detail={"code": "VALIDATION_ERROR", "message": "noise_candidate only accepts approve/ignore"})

    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO actions (ts, actor, target_type, target_id, action_type, note)
           VALUES (?,?,?,?,?,?)""",
        (ts, "demo-user", target_type, body["target_id"], action_type, note or None),
    )
    conn.commit()
    action_id = cur.lastrowid
    conn.close()

    return {
        "action_id": action_id,
        "recorded":  True,
        "message":   "Recorded only. No live system was changed.",
    }


@app.get("/api/v1/actions")
def get_actions(target_id: Optional[str] = None):
    conn = get_connection()
    if target_id:
        rows = conn.execute(
            "SELECT * FROM actions WHERE target_id=? ORDER BY ts DESC", (target_id,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM actions ORDER BY ts DESC").fetchall()
    conn.close()
    return {"items": [dict(r) for r in rows]}


# ---------------------------------------------------------------------------
# Services graph
# ---------------------------------------------------------------------------

@app.get("/api/v1/services/graph")
def services_graph():
    conn = get_connection()
    services = [dict(r) for r in conn.execute("SELECT * FROM services").fetchall()]
    edges    = [dict(r) for r in conn.execute("SELECT * FROM service_edges").fetchall()]
    conn.close()
    return {"services": services, "edges": edges}


# ---------------------------------------------------------------------------
# Metrics / scorecard
# ---------------------------------------------------------------------------

@app.get("/api/v1/metrics")
def get_metrics():
    conn = get_connection()
    run_id = _latest_run(conn)
    if not run_id:
        raise HTTPException(status_code=503, detail="Pipeline not yet run")
    rows = conn.execute(
        "SELECT name, split, value, detail_json FROM metrics WHERE run_id=?", (run_id,)
    ).fetchall()
    conn.close()

    result: dict = {
        "run_id": run_id,
        "metrics": [dict(r) for r in rows],
    }
    for r in rows:
        result[r["name"]] = r["value"]

    # Baseline = measured rules-only clusters (data/baseline/clusters_rules.json), never hardcoded.
    from alertlens.api.routes_react import _scorecard
    base = _scorecard("baseline/clusters_rules.json").get("all", {})
    if base:
        result["baseline_label"] = "rules baseline (measured)"
        result["baseline_compression_ratio"] = base.get("compression_ratio")
        result["baseline_recall"] = base.get("recall_lenient_any_alert")
        result["baseline_pairwise_precision"] = base.get("pairwise_precision")
        result["baseline_bcubed_f1"] = base.get("bcubed_f1")
        result["baseline_origin_top1"] = base.get("origin_top1")
    else:
        result["baseline_label"] = "baseline not available (data/baseline/clusters_rules.json missing)"
    result.setdefault("median_time_to_surface_s", None)

    return result


# ---------------------------------------------------------------------------
# React SPA Static Mounting (serves frontend/dist directly)
# ---------------------------------------------------------------------------

_dist_dir = _REPO / "alertlens" / "dist"
if not _dist_dir.exists():
    _dist_dir = _REPO / "frontend" / "dist"

if _dist_dir.exists():
    _assets_dir = _dist_dir / "assets"
    if _assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    async def serve_react_spa(full_path: str):
        # Exclude API and Docs paths
        if (
            full_path.startswith("api")
            or full_path.startswith("docs")
            or full_path.startswith("openapi")
        ):
            raise HTTPException(status_code=404, detail="API route not found")
        target_file = _dist_dir / full_path
        if target_file.is_file():
            return FileResponse(target_file)
        return FileResponse(_dist_dir / "index.html")
