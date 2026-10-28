# Implementation Plan – AlertLens (24-hour build, team of 3)

**MVP target**: hour 22 code freeze; hour 24 submission.
**Build philosophy**: documentation-first. Before each AI coding session, give the AI the relevant docs (PRD, APP_FLOW, TECH_STACK, FRONTEND_GUIDELINES, BACKEND_STRUCTURE) and say: "Follow these exactly. Ask if anything is ambiguous."
**Roles**: **A** data/ML (simulator → features → model → eval) · **B** clustering/origin/priority/noise/explain · **C** API, dashboard, replay, README/demo.
**Rule**: a working end-to-end baseline (rules only) by hour 8; never break `main`.

## Phase 0: Setup (Hour 0–1, all)
### Step 0.1 Repo & environment (20 min)
```bash
mkdir alertlens && cd alertlens && git init
python3.11 -m venv .venv && source .venv/bin/activate
# paste requirements.txt from TECH_STACK.md section 8
pip install -r requirements.txt
mkdir -p src/alertlens/{simulator,ingest,features,model,cluster,noise,explain,eval,api} dashboard/{pages,components,assets} tests data models docs
cp .env.example .env
```
Copy the six docs into `docs/`. Create the Makefile from TECH_STACK.md section 9.
**Success**: `python -c "import lightgbm, shap, fastapi, streamlit"` runs; first commit pushed.

### Step 0.2 Contracts first (40 min)
- A writes `schema.sql` from BACKEND_STRUCTURE.md section 4 and `config.py`.
- C writes `schemas.py` (pydantic models for every response in section 6) and a **mock API** returning hand-written JSON so the dashboard can start before real data exists.
- B writes a 30-alert hand-made sample `data/sample/` (one incident + noise) matching CSV formats.
**Success**: `uvicorn` serves `/health` and mocked `/incidents`; sample CSVs load into SQLite.

## Phase 1: Simulator (Hour 1–4, A leads; B/C use the sample)
### Step 1.1 Service graph (30 min)
Implement `simulator/graph.py` per BACKEND_STRUCTURE 3.1. Test: 70 nodes, 4 tiers, DAG, ≥ 6 dependents per tier-0 node.
### Step 1.2 Templates & incident cascades (1 h)
`templates.py` (≈45 alert types × 3–4 variants), `incidents.py` (9 types, cascade engine with probability/delay/silence).
### Step 1.3 Noise + schedule + writer (1 h)
`noise.py` (N1–N7, singletons, storms), `generate.py` (fixed schedule 3.4, writes 4 files).
```bash
make data && python -m pytest tests/test_simulator.py -q
```
**Success criteria**
- [ ] Two runs with seed 42 produce identical file hashes
- [ ] 400–900 baseline alerts/day; incident days higher
- [ ] 2 buried incidents flagged; `cert_expiry` only in test split
- [ ] ≥ 70% of alerts are noise/singletons
**Milestone M1 (hour 4): full dataset exists.**

## Phase 2: Ingest + rules baseline (Hour 3–8)
### Step 2.1 Ingest (A, 1 h)
`redact.py`, `fingerprint.py`, `dedupe.py`, `load.py` → fills `alerts`, `fingerprints`, `alert_groups`, `services`, `service_edges`, `incidents_truth`.
**Success**: no raw host/IP in `message_redacted`; each alert has a group; no group spans two truth incidents.
### Step 2.2 Rules baseline correlator (B, 2 h)
Incremental correlator with edge rule `dt ≤ 5 min AND graph_dist ≤ 2`; clusters → `incidents_pred` with simple band by max severity.
### Step 2.3 Metrics v0 (A, 1 h)
`eval/metrics.py`: compression, recall, pairwise P/R, B-cubed. Unit-test on a 10-alert example.
### Step 2.4 Real API + 2 pages (C, 4 h in parallel)
Replace mocks with DB-backed `/summary`, `/incidents`, `/incidents/{id}`; build Incidents page and Incident Detail (timeline + service map + reasons from time/dependency only).
**Milestone M2 (hour 8): demoable baseline**: `make pipeline`, open dashboard, see "N → k incidents" with baseline metrics. Tag `v0-baseline`.

## Phase 3: Learned model (Hour 8–13, A)
### Step 3.1 Pair generation + features (2 h)
`features/pairs.py`, `features/cooccurrence.py` (leave-one-incident-out). Test: no test-split group in training pairs.
### Step 3.2 Train & evaluate (1.5 h)
```bash
python -m alertlens.pipeline run --stage model   # trains on weeks 1-2 minus cert_expiry, scores week 3
```
Save model; report pairwise P/R vs baseline; SHAP top-3 for strong edges into `pair_scores`.
### Step 3.3 Threshold tuning (1 h)
Grid `PAIR_THRESHOLD ∈ {0.4…0.8}` on week 2 (validation), never on week 3. Choose, freeze, record in `runs.config_json`.
**Success**: pairwise precision ≥ 0.90 on test; model ≥ baseline on B-cubed F1. If not, inspect giant-component cases before adding features.

## Phase 4: Incident intelligence (Hour 8–16, B)
### Step 4.1 Origin ranking (1.5 h) – BACKEND 5.7. Test: top-3 accuracy on training incidents.
### Step 4.2 Priority, history match, surfacing + safety net (2 h) – BACKEND 5.8. Assert: every test truth incident has a surfaced cluster (else print the offending incident).
### Step 4.3 Noise candidates (2 h) – BACKEND 5.9. Assert N7 is `keep`, N1–N6 in top candidates, `noise_false_positive_count == 0`.
### Step 4.4 Explanations (1.5 h) – BACKEND 5.10, integrate SHAP reasons.
### Step 4.5 Full evaluation + failure modes (1.5 h)
Report: held-out cert_expiry recall, buried-incident recall, time-to-surface, origin accuracy. Write the failure-mode notes from real misses.
**Milestone M3 (hour 16): full backend pipeline + metrics in DB.**

## Phase 5: API completion (Hour 12–16, C)
Implement `/noise-candidates`, `POST/GET /actions`, `/metrics`, `/days`, `/services/graph`, validation and error format. API contract tests via `TestClient`.
**Success**: all endpoints in BACKEND 6 respond per spec; `POST /actions` rejects invalid combinations.

## Phase 6: Dashboard (Hour 12–20, C; A/B help)
### Step 6.1 Theme & components (2 h)
`config.toml`, `style.css`, `card.py`, `kpi.py`, `charts.py`, `badges.py`, `api.py` per FRONTEND_GUIDELINES.
### Step 6.2 Pages (4 h)
Incidents (KPIs, hourly chart, before/after, cards, background expander), Incident Detail (timeline, service map, why panel, table, actions), Noise Candidates, Scorecard (learned vs baseline, held-out, buried, failure modes, simulated-data banner).
### Step 6.3 Replay (2 h)
`pipeline replay-cache` writes events; page plays them with Play/Pause/Reset/Speed (1×, 10×, 60×, 300×), ≤ 4 refreshes/s.
**Success**: all flows in APP_FLOW.md work; 3-minute demo path completes without errors.
**Milestone M4 (hour 20): feature complete.**

## Phase 7: Hardening & Delivery (Hour 20–24)
### Step 7.1 Tests & cleanup (1 h)
```bash
make test && ruff check . && ruff format .
```
Run the full demo from a clean clone: `make setup data pipeline` then `make api` + `make ui`.
### Step 7.2 README (45 min, C)
Setup, architecture diagram, results table (learned vs baseline), **simulated-data disclosure**, failure modes & bias toward past patterns, safety design (no auto-actions), redaction.
### Step 7.3 Demo & slides (1.5 h, all)
Demo script (3 min): 0:00–0:30 problem + "data is simulated"; 0:30–1:30 replay of the buried day; 1:30–2:15 incident detail (origin, why grouped, Acknowledge = recorded only); 2:15–2:45 noise suggestions; 2:45–3:00 scorecard. Record a backup video.
**Freeze at hour 22. Hours 22–24 = bugs, video, submission only.**

## Milestones
| # | Hour | Deliverable |
|---|---|---|
| M1 | 4 | Simulator + dataset + tests |
| M2 | 8 | Rules baseline end-to-end, 2 pages |
| M3 | 16 | Learned model, origin, priority, noise, explanations, metrics |
| M4 | 20 | All 4 pages + replay |
| M5 | 24 | README, video, slides, submission |

## Risk Mitigation
### Technical
| Risk | Impact | Mitigation |
|---|---|---|
| Giant component merges everything | High | threshold tuning on week 2, Louvain split, size guard |
| Synthetic circularity | High | probabilistic cascades, silent hops, overlapping noise, held-out type, disclosure |
| Model recall misses an incident | Critical | safety net rules; per-incident assertion in the pipeline |
| Leakage inflates metrics | High | time split, leakage test, co-occurrence leave-one-out |
| Streamlit replay laggy | Medium | precomputed events, batch per tick, cap refresh rate |
| Pin conflict in pip | Medium | change only that pin, re-run tests, note it |
### Timeline
| Risk | Impact | Mitigation |
|---|---|---|
| Simulator takes too long | High | A owns it alone for 3 h; B/C use hand sample |
| Scope creep | High | only P0 until M4; P1/P2 after |
| One person blocked | Medium | contracts (schemas, API mocks) agreed in Phase 0 |
| Late integration | High | integrate at M2, then at every milestone |

## Success Criteria (overall)
1. All P0 features in PRD.md work.
2. All flows in APP_FLOW.md work.
3. UI follows FRONTEND_GUIDELINES.md (incl. non-colour severity cues).
4. API and schema match BACKEND_STRUCTURE.md.
5. Test-week recall 100% (incl. buried and held-out), compression ≥ 90% reduction.
6. Every surfaced incident has reasons; no action writes outside the `actions` table.
7. README discloses simulated data and failure modes.

## AI Coding Session Template
```
I have documentation for AlertLens: PRD.md, APP_FLOW.md, TECH_STACK.md, FRONTEND_GUIDELINES.md,
BACKEND_STRUCTURE.md, IMPLEMENTATION_PLAN.md. Read the sections for <STEP>.
Implement <STEP> exactly as specified, with the pinned versions. Do not add features outside PRD P0/P1.
Write the tests listed in the step. Ask before deviating.
```

## Post-MVP Roadmap
1. P1: live generator streaming, merge/split recommendations, filters.
2. Sentence embeddings for text similarity.
3. Real alert ingestion adapters, PostgreSQL, auth.
4. Calibrated confidence and drift monitoring.
