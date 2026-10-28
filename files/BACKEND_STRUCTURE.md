# Backend Architecture, Database Schema & Simulator – AlertLens

**Version**: 1.0 | **Last Updated**: 28 Oct 2026
This is the core document. The simulator (section 3) produces the data; the pipeline (section 5) turns it into incidents; the schema (section 4) stores it; the API (section 6) serves it.

## 1. Architecture Overview
```
[Simulator] → data/dependencies.json, data/alerts.csv, data/alerts_truth.csv, data/incidents.csv
      ↓
[Pipeline]  ingest(redact, fingerprint) → dedupe → pair features → LightGBM → cluster
            → origin → priority/surface → noise candidates → explain → evaluate
      ↓
[SQLite]    data/alertlens.db
      ↓
[FastAPI]   :8000  (read endpoints + POST /actions only)
      ↓
[Streamlit] :8501
```
**Hard rules**
- The pipeline never reads `alerts_truth`/`truth_incident_id` at inference. Ground truth is used only for training labels (train split) and for `eval/`.
- No code path writes anywhere except the local DB. `POST /actions` stores the human's decision; nothing else.
- All timestamps are UTC ISO-8601 (`2026-03-02T14:00:05Z`).

## 2. Repository Layout
```
alertlens/
  .env.example  Makefile  requirements.txt  README.md
  data/                       # generated; git-ignored except sample/
  src/alertlens/
    config.py
    simulator/ graph.py templates.py incidents.py noise.py generate.py
    ingest/    redact.py fingerprint.py dedupe.py load.py
    features/  pairs.py cooccurrence.py
    model/     train.py predict.py
    cluster/   correlator.py origin.py priority.py history.py
    noise/     candidates.py
    explain/   reasons.py
    eval/      metrics.py report.py
    api/       main.py db.py schemas.py routes_*.py
    pipeline.py                # CLI: run --all | --stage X | replay-cache
  dashboard/   app.py pages/ components/ theme.py assets/style.css
  tests/
```

## 3. Simulator Specification (data generator)
Command: `python -m alertlens.simulator.generate --seed 42 --days 21 --start 2026-03-02` (Monday).
Same seed ⇒ identical files. Use `random.Random(seed)` and `numpy.random.default_rng(seed)` only; no global RNG, no wall-clock.

### 3.1 Service graph → `dependencies.json`
70 services, 4 tiers. Edge `A → B` means "A depends on B" (B failing hurts A).
| Tier | Role | Count | Examples |
|---|---|---|---|
| 0 | Infrastructure | 8 | `db-primary`, `db-replica`, `cache-redis`, `msg-queue`, `dns`, `object-storage`, `log-cluster`, `secrets-vault` |
| 1 | Platform | 14 | `auth-service`, `identity`, `config-service`, `feature-flags`, `rate-limiter`, `scheduler`, `search-index`, `email-gateway`, `sms-gateway`, `payments-gateway`, `file-service`, `geo-service`, `audit-log`, `service-mesh` |
| 2 | Business | 30 | `cart`, `orders`, `payments`, `inventory`, `catalog`, `pricing`, `search`, `recommendations`, `notifications`, `billing`, `shipping`, `loyalty`, `coupons`, `tax`, `fraud`, `user-profile`, … (seed ~10 names from Online Boutique/Sock Shop; generate the rest `svc-<domain>`) |
| 3 | Edge | 18 | `api-gateway`, `web-frontend`, `mobile-bff`, `admin-portal`, `partner-gateway`, `cdn-origin`, … |

Generation rules: tier-3 → 2–4 tier-2; tier-2 → 2–4 from tiers 0–1 (always ≥ 1 of tier 0 for `payments`, `orders`, `cart`); tier-1 → 1–3 tier-0. Edges only go to a lower tier ⇒ DAG. Every tier-0 node has ≥ 6 transitive dependents.
JSON shape:
```json
{"services":[{"id":"db-primary","tier":0,"team":"data","criticality":5}],
 "edges":[{"src":"cart","dst":"db-primary"}]}
```

### 3.2 Alert type catalogue (`templates.py`)
~45 alert types. Each has: `type_id`, `source` (monitoring|logging|uptime), `severity`, 3–4 message variants with placeholders `{host} {ip} {n} {pct} {ms} {cust}`, e.g.
- `latency_high` (monitoring, high): "p95 latency {ms}ms exceeds threshold on {host}" / "Response time degraded: {ms} ms (host {host})" / "Slow responses detected, p99={ms}ms" / "latency SLO burn rate {n}x"
- `error_rate_5xx` (monitoring, high), `timeout_upstream` (logging, medium), `conn_refused` (logging, high), `endpoint_down` (uptime, critical), `oom_killed` (logging, high), `restart_loop` (monitoring, high), `disk_full` (monitoring, critical), `cert_expired` (uptime, critical), `tls_handshake_fail` (logging, high), `queue_lag` (monitoring, high), `replication_lag` (monitoring, high), `packet_loss` (monitoring, high), `dns_resolution_fail` (logging, high), `cache_miss_storm` (monitoring, medium), `deploy_error_spike` (monitoring, high), …
Hostnames: `{service}-{region}-{nn}` (e.g. `payments-ap1-07`); IPs `10.x.y.z`; customer IDs `cust-48213` appear in ~10% of logging messages.

### 3.3 Incident types (cause + cascade)
Propagation walks reverse edges (callers of the failed service). Per hop: probability `p_hop = 0.85 × 0.9^(depth-1)`, delay `lognormal(mean≈25 s, σ=0.6)` per hop, each affected service emits 1–3 alert types, each from 1–3 sources with different wording. ~15% of affected services stay silent (missing hops). Duration 10–45 min; alerts repeat/flap every 2–6 min while active.
| # | Type | Root service (tier) | Root alerts | Cascade alerts |
|---|---|---|---|---|
| 1 | `db_slowdown` | db-primary (0) | replication_lag, latency_high | latency_high, timeout_upstream, error_rate_5xx |
| 2 | `memory_leak` | any tier-2 | oom_killed, restart_loop | endpoint_down (uptime), timeout_upstream on callers |
| 3 | `network_partition` | two zones: services split by region tag | packet_loss, conn_refused | timeout_upstream, endpoint_down |
| 4 | `bad_deploy` | any tier-2 | deploy_error_spike, error_rate_5xx | error_rate_5xx, latency_high on callers |
| 5 | `disk_full` | log-cluster (0) | disk_full (critical) | log_ingest_fail, logging delays |
| 6 | `cert_expiry` | any tier-1/edge | cert_expired, tls_handshake_fail | endpoint_down, conn_refused. **HELD OUT of training** |
| 7 | `cache_failure` | cache-redis (0) | conn_refused, cache_miss_storm | latency_high, db load alerts on callers |
| 8 | `queue_backlog` | msg-queue (0) | queue_lag | notification/order delays |
| 9 | `dns_failure` | dns (0) | dns_resolution_fail | timeout_upstream everywhere (wide blast) |

### 3.4 Schedule (fixed, deterministic given seed)
- **Week 1 (train)**: Tue db_slowdown · Thu bad_deploy · Sat memory_leak
- **Week 2 (train)**: Mon disk_full · Wed cache_failure · Fri queue_backlog · **BURIED #1**: Thu `network_partition` during a noise storm
- **Week 3 (test)**: Mon dns_failure · Wed `cert_expiry` (held-out type) · Fri `bad_deploy` on a different service than week 1 · **BURIED #2**: Thu `db_slowdown` during a noise storm
Each incident gets random start time (09:00–22:00), a 5–10 min jitter on each hop.
**Noise storm** (buried days): extra 600–900 alerts from the chatty rules over a 3-hour window that contains the incident start.

### 3.5 Background noise (never an incident)
| Noise rule id | Behaviour |
|---|---|
| `N1_disk80_log` | `disk_80pct` on log-cluster every ~15 min, all day (~96/day) |
| `N2_healthcheck_blip` | `health_check_failed_once` on 4 random edge services, Poisson ~10/h, recovers in 1 min |
| `N3_nightly_batch_cpu` | cpu spike on reporting/analytics services 02:00–02:45 daily, 20–40 alerts |
| `N4_slow_query_info` | `slow_query` (info/low) on reporting, ~40/day |
| `N5_deprecated_api` | `deprecated_api_call` (logging, low), ~60/day across 10 services |
| `N6_retry_info` | `retry_rate_elevated` (monitoring, low), bursty |
| `N7_latency_warn_search` | **ambiguous**: `latency_p95_warn` on `search`, ~20/day, precedes 2 incidents in 3 weeks ⇒ must NOT be listed as pure noise |
Plus random singletons (any service, any type, low/medium) to reach **400–900 baseline alerts/day**. Noise also overlaps incident windows (same minutes, different services/templates).
Flapping: any alert repeats with 2–6 min gap while its condition holds. Multi-tool duplicates: one fault yields a metric + log + uptime alert with different wording.

### 3.6 Output files
`alerts.csv`: `alert_id,timestamp,source,service,severity,message,incident_id` (incident_id empty for noise)
`alerts_truth.csv`: `alert_id,kind(incident|noise|singleton),noise_rule_id,incident_type,is_buried`
`incidents.csv`: `incident_id,type,start,end,root_cause_service,root_cause_description,buried,split(train|test)`
`dependencies.json`: as 3.1.
Validation tests (`tests/test_simulator.py`): determinism, DAG check, volume range per day, every incident alert has an incident_id, ≥ 8 incident types, held-out type only in test split, 2 buried incidents present, N7 precedes ≥ 2 incidents.
**Disclosure**: all docs and the Scorecard say results are on simulated data.

## 4. Database Schema (SQLite 3, WAL mode, foreign keys ON)
```sql
CREATE TABLE runs (
  run_id TEXT PRIMARY KEY,           -- e.g. run_20261028_1530
  created_at TEXT NOT NULL,
  seed INTEGER NOT NULL,
  config_json TEXT NOT NULL,
  model_path TEXT,
  notes TEXT
);

CREATE TABLE services (
  service_id TEXT PRIMARY KEY,
  tier INTEGER NOT NULL CHECK (tier BETWEEN 0 AND 3),
  team TEXT,
  criticality INTEGER NOT NULL DEFAULT 3 CHECK (criticality BETWEEN 1 AND 5)
);

CREATE TABLE service_edges (            -- src DEPENDS ON dst
  src_service TEXT NOT NULL REFERENCES services(service_id),
  dst_service TEXT NOT NULL REFERENCES services(service_id),
  PRIMARY KEY (src_service, dst_service)
);

CREATE TABLE fingerprints (
  fingerprint_id TEXT PRIMARY KEY,       -- sha1(template)[:12]
  template TEXT NOT NULL,                -- "p95 latency <NUM>ms exceeds threshold on <HOST>"
  alert_type TEXT,                       -- parsed or NULL
  source TEXT NOT NULL CHECK (source IN ('monitoring','logging','uptime')),
  first_seen TEXT, volume_total INTEGER DEFAULT 0
);

CREATE TABLE alerts (
  alert_id TEXT PRIMARY KEY,
  ts TEXT NOT NULL,                      -- UTC ISO
  source TEXT NOT NULL CHECK (source IN ('monitoring','logging','uptime')),
  service_id TEXT NOT NULL REFERENCES services(service_id),
  severity TEXT NOT NULL CHECK (severity IN ('low','medium','high','critical')),
  severity_num INTEGER NOT NULL,         -- 1..4
  message_raw TEXT NOT NULL,             -- shown only if DEMO_MODE=0
  message_redacted TEXT NOT NULL,
  fingerprint_id TEXT NOT NULL REFERENCES fingerprints(fingerprint_id),
  group_id TEXT,                         -- FK alert_groups (set by dedupe)
  split TEXT NOT NULL CHECK (split IN ('train','test')),
  truth_incident_id TEXT,                -- ground truth; eval/train only
  truth_kind TEXT                        -- incident|noise|singleton; eval only
);
CREATE INDEX idx_alerts_ts ON alerts(ts);
CREATE INDEX idx_alerts_group ON alerts(group_id);
CREATE INDEX idx_alerts_service_ts ON alerts(service_id, ts);

CREATE TABLE alert_groups (              -- de-duplicated unit used by the model
  group_id TEXT PRIMARY KEY,             -- grp_000123
  fingerprint_id TEXT NOT NULL REFERENCES fingerprints(fingerprint_id),
  service_id TEXT NOT NULL REFERENCES services(service_id),
  source TEXT NOT NULL,
  first_ts TEXT NOT NULL, last_ts TEXT NOT NULL,
  alert_count INTEGER NOT NULL,
  max_severity_num INTEGER NOT NULL,
  split TEXT NOT NULL,
  truth_incident_id TEXT                 -- majority label; eval/train only
);
CREATE INDEX idx_groups_first ON alert_groups(first_ts);

CREATE TABLE incidents_truth (           -- historical incident records
  incident_id TEXT PRIMARY KEY,
  type TEXT NOT NULL,
  start_ts TEXT NOT NULL, end_ts TEXT NOT NULL,
  root_cause_service TEXT NOT NULL REFERENCES services(service_id),
  root_cause_description TEXT,
  buried INTEGER NOT NULL DEFAULT 0,
  split TEXT NOT NULL
);

CREATE TABLE pair_scores (               -- strong edges only (score >= 0.30)
  run_id TEXT NOT NULL REFERENCES runs(run_id),
  group_a TEXT NOT NULL, group_b TEXT NOT NULL,   -- a earlier than b
  score REAL NOT NULL,
  features_json TEXT NOT NULL,
  top_reasons_json TEXT,                 -- SHAP top-3 [{"feature":"graph_dist","value":1,"shap":0.42}]
  PRIMARY KEY (run_id, group_a, group_b)
);

CREATE TABLE incidents_pred (
  incident_pred_id TEXT NOT NULL,        -- inc_<run>_<n>
  run_id TEXT NOT NULL REFERENCES runs(run_id),
  title TEXT NOT NULL,                   -- "Database slow" (from origin alert_type + service)
  day TEXT NOT NULL,                     -- YYYY-MM-DD of first_ts
  first_ts TEXT NOT NULL, last_ts TEXT NOT NULL,
  origin_group_id TEXT, origin_service TEXT, origin_score REAL,
  n_alerts_raw INTEGER NOT NULL, n_groups INTEGER NOT NULL, n_services INTEGER NOT NULL,
  blast_radius INTEGER NOT NULL,         -- services transitively depending on origin
  max_severity_num INTEGER NOT NULL,
  history_match REAL NOT NULL DEFAULT 0, history_match_type TEXT,
  priority_score REAL NOT NULL,
  band TEXT NOT NULL CHECK (band IN ('RED','ORANGE','YELLOW','BACKGROUND')),
  surfaced INTEGER NOT NULL,             -- 0/1
  surfaced_ts TEXT,                      -- when rule first satisfied (replay time)
  surface_reason TEXT,                   -- 'priority'|'critical_severity'|'history_match'|'multi_service'
  reasons_json TEXT NOT NULL,            -- [{"kind":"time","text":"..."},{"kind":"dependency","text":"..."},{"kind":"template","text":"..."}]
  PRIMARY KEY (run_id, incident_pred_id)
);
CREATE INDEX idx_pred_day ON incidents_pred(run_id, day, surfaced);

CREATE TABLE incident_members (
  run_id TEXT NOT NULL, incident_pred_id TEXT NOT NULL,
  group_id TEXT NOT NULL REFERENCES alert_groups(group_id),
  origin_rank INTEGER NOT NULL,          -- 1 = probable origin
  origin_score REAL NOT NULL,
  dep_path_from_origin TEXT,             -- "db-primary>payments>api-gateway"
  PRIMARY KEY (run_id, incident_pred_id, group_id),
  FOREIGN KEY (run_id, incident_pred_id) REFERENCES incidents_pred(run_id, incident_pred_id)
);

CREATE TABLE noise_candidates (
  run_id TEXT NOT NULL,
  fingerprint_id TEXT NOT NULL REFERENCES fingerprints(fingerprint_id),
  service_id TEXT,                       -- NULL = across services
  volume INTEGER NOT NULL,
  incident_involvement INTEGER NOT NULL, -- # distinct incidents accompanied/preceded (train period)
  precursor_rate REAL NOT NULL,          -- involvement / volume
  pattern TEXT,                          -- periodic|flapping|single_template_wide|low_severity
  recommendation_type TEXT NOT NULL CHECK (recommendation_type IN
    ('raise_threshold','merge_rule','downgrade_severity','require_consecutive','keep')),
  recommendation_text TEXT NOT NULL,
  evidence_json TEXT NOT NULL,
  PRIMARY KEY (run_id, fingerprint_id, service_id)
);

CREATE TABLE actions (                   -- append-only human decisions; no side effects
  action_id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  actor TEXT NOT NULL DEFAULT 'demo-user',
  target_type TEXT NOT NULL CHECK (target_type IN ('incident','noise_candidate')),
  target_id TEXT NOT NULL,
  action_type TEXT NOT NULL CHECK (action_type IN ('acknowledge','escalate','approve','ignore')),
  note TEXT
);
CREATE INDEX idx_actions_target ON actions(target_type, target_id);

CREATE TABLE metrics (
  run_id TEXT NOT NULL, name TEXT NOT NULL, split TEXT NOT NULL,   -- split: train|test|all
  value REAL, detail_json TEXT,
  PRIMARY KEY (run_id, name, split)
);
```
Relationships: `alerts.group_id → alert_groups`; `incident_members → alert_groups, incidents_pred`; `incidents_pred.run_id → runs`; `service_edges → services`.
Metric names stored: `raw_alerts`, `surfaced_incidents`, `compression_ratio`, `recall`, `median_time_to_surface_s`, `pairwise_precision`, `pairwise_recall`, `bcubed_f1`, `origin_top1`, `origin_top3`, `heldout_recall`, `buried_recall`, `baseline_*` (same set for the rules-only baseline), `explainability_pct`.

## 5. Pipeline Algorithms (exact definitions)
### 5.1 Ingest & redaction
- Regexes: IPv4, IPv6, `[a-z0-9-]+-[a-z]{2}\d-\d{2}` hostnames, `cust-\d+`, UUIDs, emails.
- Token = `prefix-` + first 4 hex of `HMAC_SHA256(salt, value)`; same value → same token.
- Fingerprint template: redact, then replace numbers → `<NUM>`, tokens → `<HOST>/<IP>/<CUST>`, lowercase, collapse whitespace; `fingerprint_id = sha1(source + "|" + template)[:12]`.

### 5.2 De-duplication
Group alerts with same `(fingerprint_id, service_id)` whose gap to the previous alert ≤ `DEDUP_WINDOW_MIN` (5). `first_ts/last_ts/alert_count/max_severity`. Label = majority non-null truth_incident_id (train/eval only). The model operates on **groups**.

### 5.3 Candidate pairs
For group *b*, candidates = groups *a* with `first_ts(a) ≤ first_ts(b)` and `first_ts(b) − first_ts(a) ≤ PAIR_WINDOW_MIN` (10), `a ≠ b`, cap 200 nearest by time. Training: all positives + negatives sampled 5:1 (hard negatives = same window, different incident or noise). Label 1 iff both have the same non-null truth incident.

### 5.4 Pair features
`dt_seconds, log_dt, graph_dist (undirected shortest path, cap 6), a_depends_on_b (transitive), b_depends_on_a, share_dependency (common transitive dependency count), tier_a, tier_b, tier_diff, text_sim (TF-IDF char 3–5 cosine on templates), same_source, same_severity, sev_a, sev_b, cooc_prior (train-incident co-occurrence of the two fingerprints, Laplace-smoothed; computed leave-one-incident-out for training rows), burst_density (groups in window)`.

### 5.5 Model
LightGBM binary: `n_estimators=300, learning_rate=0.05, num_leaves=31, min_child_samples=20, subsample=0.8, colsample_bytree=0.8, class_weight="balanced", random_state=42`. Train on weeks 1–2 excluding `cert_expiry`; test on week 3. Save `models/pair_lgbm.txt`. Calibrate with `CalibratedClassifierCV(method="isotonic")` if time permits.
**Baseline (rules-only)**: edge if `dt ≤ 5 min AND graph_dist ≤ 2`. Report both.

### 5.6 Clustering (incremental, shared by batch and replay)
Process groups in `first_ts` order. For each new group score against window candidates; add edges with `score ≥ PAIR_THRESHOLD (0.60)`; union-find merges. If a component exceeds 150 groups or spans > 90 min, run Louvain (`resolution=1.0`, edge weight = score) and split. Maintain cluster stats on every update, re-evaluate surface rule.

### 5.7 Origin ranking
For each group *g* in a cluster: `E = 1 − rank_by_first_ts/(n−1)`; `U = (# other cluster services that transitively depend on service(g)) / (n_services−1)`; `T = 1 − tier/3`; `origin_score = 0.45·E + 0.40·U + 0.15·T`. Top = origin. `dep_path_from_origin` = shortest path (reverse direction) to each member service.

### 5.8 Priority & surfacing
`priority = 0.30·sev + 0.25·min(1, n_services/10) + 0.20·(blast_radius/70, cap 1) + 0.15·history_match + 0.10·min(1, ln(n_alerts)/ln(100))`, with `sev = (max_severity_num−1)/3`.
Bands: RED ≥ 0.75 or critical; ORANGE 0.55–0.75; YELLOW surfaced by safety net but < 0.55; else BACKGROUND.
**Surface if any**: `priority ≥ SURFACE_THRESHOLD (0.55)` · `max_severity_num == 4` · `history_match ≥ 0.80 AND n_groups ≥ 2` · `n_services ≥ 4`. `surface_reason` stores the first rule satisfied. Nothing is deleted; BACKGROUND clusters remain queryable.
`history_match` = max Jaccard (weighted by fingerprint volume) between cluster fingerprint set and each training-incident signature; 0 for held-out types by construction.

### 5.9 Noise candidates
Per `(fingerprint, service)` using the **training period**: `volume ≥ 50` and `incident_involvement = 0` ⇒ candidate; ambiguous (N7) has involvement ≥ 1 ⇒ `keep`. Involvement counts incidents where the fingerprint appeared as a labelled member, or fired on an affected service within 30 min before incident start. Recommendation rules: periodic (CV of gaps < 0.3) → `raise_threshold`; > 40% of repeats within 5 min → `require_consecutive`; severity ≥ medium and involvement 0 → `downgrade_severity`; same template across ≥ 5 services → `merge_rule`. Validate on the test week: no candidate may appear as a member of a test incident (reported as `noise_false_positive_count`).

### 5.10 Explanations
Templates (filled with real values):
- time: "{n} alerts within {minutes} min of each other."
- dependency: "{k} of {m} services depend on {origin} ({path example})."
- template: "Messages describe the same symptom: {top fingerprint words}."
- SHAP edge: "Strongest link: {a} ↔ {b} (distance {d}, Δt {s}s, text sim {x:.2f})."
Weak-link rule: edge score < 0.70 ⇒ flagged.

### 5.11 Evaluation (`eval/metrics.py`)
- **Compression** = raw alerts that day ÷ surfaced incidents that day (also overall mean on test week).
- **Recall** = truth incidents with ≥ 1 member group inside a surfaced cluster ÷ all truth incidents (test split). Buried and held-out reported separately.
- **Time-to-surface** = `surfaced_ts − first alert ts` of the truth incident; median and max.
- **Pairwise P/R** over alert-group pairs; **B-cubed P/R/F1** on groups with a truth incident; noise groups treated as singleton ground-truth clusters.
- **Origin top-1/top-3** vs `root_cause_service`.
- **Explainability** = surfaced incidents with ≥ 3 reasons ÷ surfaced incidents.

## 6. API Endpoints (`/api/v1`, JSON, no auth)
Error format: `{"error":{"code":"NOT_FOUND","message":"Incident not found","details":null}}`; codes: `VALIDATION_ERROR` (422), `NOT_FOUND` (404), `INTERNAL` (500).
Global query param `redact=true|false` (default true; ignored and forced true when `DEMO_MODE=1`). Every response includes `run_id`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | `{status:"ok", run_id, simulated:true}` |
| GET | `/days` | list of days with raw/surfaced counts, split |
| GET | `/summary?day=` | headline numbers + hourly series |
| GET | `/incidents?day=&band=&service=&include_background=false` | incident cards |
| GET | `/incidents/{id}` | full detail |
| GET | `/services/graph` | all services and edges |
| GET | `/noise-candidates?sort=volume` | rule suggestions with action status |
| POST | `/actions` | record a human decision |
| GET | `/actions?target_id=` | decisions for a target |
| GET | `/metrics` | scorecard data (learned vs baseline) |
| GET | `/replay/{day}` | ordered event list for the replay |

**GET /summary?day=2026-03-18**
```json
{"run_id":"run_...","day":"2026-03-18","raw_alerts":612,"alert_groups":388,
 "surfaced_incidents":5,"background_clusters":71,"reduction_pct":99.2,
 "hourly":[{"hour":"2026-03-18T14:00:00Z","alerts":148,"incidents_started":1}]}
```
**GET /incidents**
```json
{"run_id":"...","items":[{"incident_id":"inc_run1_12","title":"Database slow","band":"RED",
 "first_ts":"...","last_ts":"...","origin_service":"db-primary","n_services":7,"n_alerts_raw":58,
 "priority_score":0.83,"surface_reason":"priority","reason_summary":"58 alerts in 12 min; 7 services depend on db-primary",
 "status":"new|acknowledged|escalated"}]}
```
**GET /incidents/{id}**
```json
{"incident_id":"...","title":"...","band":"RED","priority_score":0.83,"origin":{"service":"db-primary","group_id":"grp_..","score":0.91},
 "stats":{"first_ts":"...","last_ts":"...","n_alerts_raw":58,"n_services":7,"blast_radius":23,"max_severity":"critical","history_match":0.72,"history_match_type":"db_slowdown"},
 "timeline":[{"group_id":"...","ts":"...","service":"cart","severity":"high","source":"logging","message":"...","count":4,"origin_rank":5}],
 "graph":{"nodes":[{"id":"db-primary","tier":0,"role":"origin|affected|other"}],"edges":[{"src":"cart","dst":"db-primary","on_path":true}]},
 "reasons":[{"kind":"time","text":"..."},{"kind":"dependency","text":"..."},{"kind":"template","text":"..."}],
 "strong_edges":[{"a":"grp_1","b":"grp_2","score":0.93,"weak":false,"shap":[{"feature":"graph_dist","value":1,"contribution":0.42}]}],
 "actions":[{"action_type":"acknowledge","ts":"...","note":null}]}
```
**POST /actions** request `{"target_type":"incident","target_id":"inc_..","action_type":"acknowledge","note":"optional ≤ 500 chars"}` → 201 `{"action_id":17,"recorded":true,"message":"Recorded only. No live system was changed."}`. Validation: target must exist; `approve|ignore` only for `noise_candidate`; `acknowledge|escalate` only for `incident`.
**GET /noise-candidates**: items `{fingerprint_id,template,service,volume,incident_involvement,precursor_rate,recommendation_type,recommendation_text,evidence,status}`.
**GET /replay/{day}** → `{"day":"...","start":"...","end":"...","events":[{"t":"...","type":"alert","raw_total":131},{"t":"...","type":"incident_surfaced","incident_id":"..","title":"..","band":"ORANGE"},{"t":"...","type":"incident_update","incident_id":"..","n_alerts_raw":21,"n_services":3,"band":"RED"},{"t":"...","type":"origin_set","incident_id":"..","origin_service":"db-primary"}]}`. Events are precomputed by running the correlator incrementally (`pipeline replay-cache`), max ~2,000 events/day (alert events are batched per 10 simulated seconds).

## 7. Validation Rules
- `day`: `YYYY-MM-DD` within data range, else 422.
- `band`: one of RED|ORANGE|YELLOW.
- `note`: ≤ 500 chars, stripped, stored as text (never rendered as HTML).
- IDs: regex `^[A-Za-z0-9_\-]{1,64}$`.

## 8. Caching & Performance
- Indexes in section 4. Pipeline writes in bulk (`executemany`, one transaction per stage).
- `lru_cache` for the service graph and metrics; replay events cached as `data/replay_<day>.json`.
- Dashboard `st.cache_data(ttl=30)` except during replay.

## 9. Migrations & Reproducibility
- Hackathon: `pipeline run --all` drops and recreates tables (`DROP TABLE IF EXISTS`), then reloads. Schema SQL lives in `src/alertlens/api/schema.sql`.
- Every run stores seed + config in `runs`. Re-running with the same seed must give identical metrics.

## 10. Testing Requirements
- Simulator tests (3.6), redaction test (no raw host/IP in `message_redacted`), dedupe test (no group spans two truth incidents), leakage test (training pairs contain no test-split groups), API contract tests with `TestClient`, "no live writes" test (grep that no outbound HTTP client is used in `pipeline/` or write routes), metric function unit tests on a hand-made 10-alert example.

## 11. Known Limitations (feed into README failure modes)
Simulated data (circularity); dependency map assumed correct; novel incident types lean on time/dependency only (`history_match = 0`); wide-blast incidents (DNS) can create very large clusters; flapping rules inflate dedup counts; thresholds tuned on simulated week 1–2 may not transfer.
