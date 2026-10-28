# AlertLens — Data Contracts (FROZEN)

> **⚠️ Do not change column names or JSON fields without telling the whole team.**
> Last frozen: 2026-10-28

---

## `alerts.csv`

Produced by: **A** (simulator) | Consumed by: **B** (ingest)

| Column | Type | Notes |
|---|---|---|
| `alert_id` | string | Unique, e.g. `a_20260304_001` |
| `timestamp` | string | UTC ISO-8601 `2026-03-04T14:00:05Z` |
| `source` | enum | `monitoring` \| `logging` \| `uptime` |
| `service` | string | Must match a `service.id` in `dependencies.json` |
| `severity` | enum | `low` \| `medium` \| `high` \| `critical` |
| `message` | string | Raw alert message (may contain IPs, hostnames) |
| `incident_id` | string | Ground truth incident ID; **empty string** for noise |

---

## `incidents.csv`

Produced by: **A** (simulator) | Consumed by: **B** (ingest / eval)

| Column | Type | Notes |
|---|---|---|
| `incident_id` | string | Unique, e.g. `INC001` |
| `type` | string | e.g. `db_slowdown`, `bad_deploy`, `cert_expiry` |
| `start` | string | UTC ISO-8601 |
| `end` | string | UTC ISO-8601 |
| `root_cause_service` | string | Must match a service id |
| `root_cause_description` | string | Human-readable |
| `buried` | int | `0` or `1` |
| `split` | enum | `train` \| `test` |

---

## `dependencies.json`

Produced by: **A** (simulator) | Consumed by: **B** (graph utils)

```json
{
  "services": [
    {"id": "db-primary", "tier": 0, "team": "data", "criticality": 5}
  ],
  "edges": [
    {"src": "cart", "dst": "db-primary"}
  ]
}
```

Edge `src → dst` means **src depends on dst** (dst failing hurts src).

---

## `clusters.json` / API `GET /api/v1/incidents` response

Produced by: **B** (correlator → API) | Consumed by: **C** (dashboard)

```json
{
  "run_id": "run_20261028_2000",
  "items": [
    {
      "incident_id":    "inc_run_20261028_2000_0001",
      "title":          "Replication lag — db-primary",
      "band":           "RED",
      "first_ts":       "2026-03-04T14:00:05Z",
      "last_ts":        "2026-03-04T14:30:00Z",
      "origin_service": "db-primary",
      "n_services":     4,
      "n_alerts_raw":   11,
      "priority_score": 0.83,
      "surface_reason": "critical_severity",
      "reason_summary": "11 alerts within 5 min of each other.",
      "status":         "new"
    }
  ]
}
```

---

## `GET /api/v1/incidents/{id}` — full detail

```json
{
  "incident_id":    "...",
  "title":          "...",
  "band":           "RED",
  "priority_score": 0.83,
  "origin": { "service": "db-primary", "group_id": "grp_000001", "score": 0.91 },
  "stats": {
    "first_ts": "...", "last_ts": "...",
    "n_alerts_raw": 11, "n_services": 4, "blast_radius": 12,
    "max_severity": "critical", "history_match": 0.0, "history_match_type": null
  },
  "timeline": [
    { "group_id": "grp_000001", "ts": "...", "service": "db-primary",
      "severity": "critical", "source": "monitoring", "message": "...",
      "count": 2, "origin_rank": 1 }
  ],
  "graph": {
    "nodes": [{ "id": "db-primary", "tier": 0, "role": "origin" }],
    "edges": [{ "src": "cart", "dst": "db-primary", "on_path": true }]
  },
  "reasons": [
    { "kind": "time",       "text": "11 alerts within 5 min of each other." },
    { "kind": "dependency", "text": "3 of 4 services depend on db-primary (db-primary > cart)." },
    { "kind": "template",   "text": "Messages describe the same symptom: replication, latency." }
  ],
  "actions": []
}
```

---

## Band → severity mapping

| Band | Meaning | Display |
|---|---|---|
| `RED` | Critical severity or score ≥ 0.75 | 🔴 |
| `ORANGE` | Score 0.55–0.75 | 🟠 |
| `YELLOW` | Safety-net surfaced | 🟡 |
| `BACKGROUND` | Not surfaced (visible in collapsed list) | ⬜ |

---

## `POST /api/v1/actions`

```json
{ "target_type": "incident", "target_id": "inc_...", "action_type": "acknowledge", "note": "optional" }
```

- `target_type=incident` → `action_type` must be `acknowledge` or `escalate`
- `target_type=noise_candidate` → `action_type` must be `approve` or `ignore`
