"""dashboard/components/api.py
All HTTP calls go through this module.  During development, if the FastAPI
backend is not reachable, it falls back to reading mock JSON/CSV files.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import streamlit as st

# ── configuration ────────────────────────────────────────────────────────────
_API_BASE = os.getenv("ALERTLENS_API_URL", "http://localhost:8000").rstrip("/")
_DATA_DIR = Path(__file__).parent.parent.parent / "data"
_DEMO_MODE = os.getenv("ALERTLENS_DEMO_MODE", "0") == "1"

# ── low-level helpers ─────────────────────────────────────────────────────────

def _get(path: str, params: dict | None = None) -> Any:
    """GET from the FastAPI backend; falls back to mock files on connection error."""
    try:
        import httpx  # only imported here, never in page code
        url = f"{_API_BASE}{path}"
        r = httpx.get(url, params=params, timeout=5.0)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None  # caller handles None → mock fallback


def _post(path: str, body: dict) -> Any:
    """POST to the FastAPI backend; returns None on failure."""
    try:
        import httpx
        url = f"{_API_BASE}{path}"
        r = httpx.post(url, json=body, timeout=5.0)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


# ── mock loaders ─────────────────────────────────────────────────────────────

def _load_mock_summary() -> dict:
    p = _DATA_DIR / "mock_summary.json"
    if p.exists():
        return json.loads(p.read_text())
    return {
        "run_id": "mock",
        "day": "2026-03-18",
        "raw_alerts": 612,
        "alert_groups": 388,
        "surfaced_incidents": 3,
        "background_clusters": 71,
        "reduction_pct": 99.5,
        "hourly": [],
    }


def _load_mock_clusters() -> list[dict]:
    # Try clusters.json first (written by Person B's engine)
    for name in ("clusters.json", "mock_clusters.json"):
        p = _DATA_DIR / name
        if p.exists():
            return json.loads(p.read_text())
    return []


def _clusters_to_incidents(clusters: list[dict]) -> list[dict]:
    """Convert clusters.json format → incidents API format."""
    result = []
    for c in clusters:
        reasons = c.get("reasons", [])
        result.append({
            "incident_id": c.get("cluster_id", "unknown"),
            "title": f"{c.get('origin', 'Unknown')} — {c.get('band', '')}",
            "band": c.get("band", "YELLOW"),
            "first_ts": c.get("start", ""),
            "last_ts": c.get("end", ""),
            "origin_service": c.get("origin", ""),
            "n_services": len(c.get("services", [])),
            "n_alerts_raw": c.get("alert_count", 0),
            "priority_score": {"RED": 0.85, "ORANGE": 0.65, "YELLOW": 0.45}.get(c.get("band", "YELLOW"), 0.5),
            "surface_reason": "priority",
            "reason_summary": reasons[0] if reasons else "",
            "status": "new",
            "dep_path": c.get("dep_path", []),
            "reasons": reasons,
            "services": c.get("services", []),
        })
    # Sort: RED → ORANGE → YELLOW
    band_order = {"RED": 0, "ORANGE": 1, "YELLOW": 2, "BACKGROUND": 3}
    result.sort(key=lambda x: band_order.get(x["band"], 4))
    return result


# ── public API ────────────────────────────────────────────────────────────────

@st.cache_data(ttl=30, show_spinner=False)
def get_summary(day: str) -> dict:
    data = _get("/api/v1/summary", {"day": day})
    return data if data else _load_mock_summary()


@st.cache_data(ttl=30, show_spinner=False)
def get_incidents(
    day: str,
    band: str | None = None,
    service: str | None = None,
    include_background: bool = False,
) -> list[dict]:
    params: dict = {"day": day, "include_background": str(include_background).lower()}
    if band:
        params["band"] = band
    if service:
        params["service"] = service
    data = _get("/api/v1/incidents", params)
    if data and "items" in data:
        return data["items"]
    # Fallback: read clusters.json / mock_clusters.json
    clusters = _load_mock_clusters()
    incidents = _clusters_to_incidents(clusters)
    if band:
        incidents = [i for i in incidents if i["band"] == band.upper()]
    if not include_background:
        incidents = [i for i in incidents if i["band"] != "BACKGROUND"]
    return incidents


@st.cache_data(ttl=30, show_spinner=False)
def get_incident(incident_id: str) -> dict | None:
    data = _get(f"/api/v1/incidents/{incident_id}")
    if data:
        return data
    # Fallback: find in mock clusters
    clusters = _load_mock_clusters()
    for c in clusters:
        if c.get("cluster_id") == incident_id:
            return {
                "incident_id": incident_id,
                "title": f"{c.get('origin', 'Unknown')} incident",
                "band": c.get("band", "YELLOW"),
                "priority_score": 0.75,
                "origin": {
                    "service": c.get("origin", ""),
                    "group_id": "",
                    "score": 0.9,
                },
                "stats": {
                    "first_ts": c.get("start", ""),
                    "last_ts": c.get("end", ""),
                    "n_alerts_raw": c.get("alert_count", 0),
                    "n_services": len(c.get("services", [])),
                    "blast_radius": len(c.get("services", [])) + 3,
                    "max_severity": "critical" if c.get("band") == "RED" else "high",
                    "history_match": 0.72,
                    "history_match_type": "db_slowdown",
                },
                "timeline": [
                    {
                        "group_id": f"grp_{i}",
                        "ts": c.get("start", ""),
                        "service": svc,
                        "severity": "high",
                        "source": "monitoring",
                        "message": f"Alert on {svc}",
                        "count": 4,
                        "origin_rank": i + 1,
                    }
                    for i, svc in enumerate(c.get("services", []))
                ],
                "graph": {
                    "nodes": [
                        {
                            "id": svc,
                            "tier": 0 if svc == c.get("origin") else 2,
                            "role": "origin" if svc == c.get("origin") else "affected",
                        }
                        for svc in c.get("services", [])
                    ],
                    "edges": [
                        {"src": c.get("dep_path", [""])[i], "dst": c.get("dep_path", [""])[i + 1], "on_path": True}
                        for i in range(len(c.get("dep_path", [])) - 1)
                    ],
                },
                "reasons": c.get("reasons", []),
                "strong_edges": [],
                "actions": [],
            }
    return None


@st.cache_data(ttl=30, show_spinner=False)
def get_services_graph() -> dict:
    data = _get("/api/v1/services/graph")
    return data if data else {"nodes": [], "edges": []}


@st.cache_data(ttl=30, show_spinner=False)
def get_noise_candidates(sort: str = "volume") -> list[dict]:
    data = _get("/api/v1/noise-candidates", {"sort": sort})
    if data and "items" in data:
        return data["items"]
    # Fallback mock
    p = _DATA_DIR / "noise_candidates.json"
    if p.exists():
        return json.loads(p.read_text())
    return [
        {
            "fingerprint_id": "fp_mock_01",
            "template": "disk <NUM>% full on <HOST>",
            "service": "log-cluster",
            "volume": 96,
            "incident_involvement": 0,
            "precursor_rate": 0.0,
            "recommendation_type": "raise_threshold",
            "recommendation_text": "Raise disk alert threshold to 90%; fires every 15 min but never precedes an incident.",
            "evidence": {"fires_per_day": 96, "incident_preceded": 0},
            "status": "new",
        },
        {
            "fingerprint_id": "fp_mock_02",
            "template": "health check failed once on <HOST>",
            "service": "api-gateway",
            "volume": 240,
            "incident_involvement": 0,
            "precursor_rate": 0.0,
            "recommendation_type": "require_consecutive",
            "recommendation_text": "Require 3 consecutive failures before alerting; single blips self-resolve in 1 min.",
            "evidence": {"fires_per_day": 80, "incident_preceded": 0},
            "status": "new",
        },
    ]


def post_action(
    target_type: str,
    target_id: str,
    action_type: str,
    note: str | None = None,
) -> dict:
    body: dict = {
        "target_type": target_type,
        "target_id": target_id,
        "action_type": action_type,
    }
    if note:
        body["note"] = note[:500]
    result = _post("/api/v1/actions", body)
    if result:
        return result
    # Local fallback: write to actions.json
    import datetime
    actions_path = _DATA_DIR / "actions.json"
    actions = json.loads(actions_path.read_text()) if actions_path.exists() else []
    entry = {
        "ts": datetime.datetime.utcnow().isoformat() + "Z",
        "actor": "demo-user",
        **body,
    }
    actions.append(entry)
    actions_path.write_text(json.dumps(actions, indent=2))
    return {"recorded": True, "message": "Recorded only. No live system was changed."}


@st.cache_data(ttl=60, show_spinner=False)
def get_metrics() -> dict:
    data = _get("/api/v1/metrics")
    if data:
        return data
    p = _DATA_DIR / "metrics.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return {}


@st.cache_data(show_spinner=False)
def get_replay(day: str) -> dict:
    data = _get(f"/api/v1/replay/{day}")
    if data:
        return data
    # Minimal mock replay built from mock clusters
    clusters = _load_mock_clusters()
    events: list[dict] = []
    raw = 0
    for c in clusters:
        raw += c.get("alert_count", 0)
        events.append({"t": c.get("start", ""), "type": "alert", "raw_total": raw})
        events.append({
            "t": c.get("start", ""),
            "type": "incident_surfaced",
            "incident_id": c.get("cluster_id", ""),
            "title": f"{c.get('origin', '')} — {c.get('band', '')}",
            "band": c.get("band", "YELLOW"),
        })
    return {"day": day, "events": events}


@st.cache_data(ttl=60, show_spinner=False)
def get_days() -> list[dict]:
    data = _get("/api/v1/days")
    if data and "items" in data:
        return data["items"]
    return [{"day": "2026-03-18", "raw_alerts": 612, "surfaced_incidents": 3, "split": "test"}]


def is_demo_mode() -> bool:
    return _DEMO_MODE
