# Technology Stack Documentation – AlertLens

**Last Updated**: 28 Oct 2026 | **Version**: 1.0

> Versions below are pinned, mutually compatible choices. Install from `requirements.txt` (section 8). If a pin fails to resolve on your machine, change only that line, run the tests, and note it here. Do not use "latest".

## 1. Stack Overview
- **Type**: Modular monolith, single repo, runs locally on one laptop
- **Pattern**: Offline batch pipeline → SQLite → FastAPI → Streamlit dashboard; an incremental correlator is shared by batch and replay
- **Deployment**: Local (optionally Docker Compose for the demo machine)

```
simulator → data/*.csv,json → pipeline (ingest→dedupe→features→model→cluster→origin→priority→noise→explain→eval)
        → SQLite alertlens.db → FastAPI (port 8000) → Streamlit (port 8501)
```

## 2. Language & Runtime
- **Python**: 3.11.9 (reason: wheels exist for every ML dependency; stable)
- **Package manager**: pip + venv (reason: zero setup friction in a hackathon)

## 3. Data & ML Stack
| Purpose | Library | Version | Reason |
|---|---|---|---|
| Dataframes | pandas | 2.2.3 | standard |
| Numerics | numpy | 1.26.4 | compatible with shap/lightgbm pins |
| Graph | networkx | 3.4.2 | dependency graph, shortest paths, Louvain (`community.louvain_communities`) |
| Pair classifier | lightgbm | 4.5.0 | fast, strong on tabular, works with SHAP |
| ML utilities | scikit-learn | 1.5.2 | TF-IDF, metrics, calibration |
| Explainability | shap | 0.46.0 | TreeExplainer on LightGBM |
| Clustering metrics | scikit-learn + custom | – | pairwise P/R, B-cubed (written in `eval/metrics.py`) |
| Faker | faker | 30.8.2 | hostnames, IDs for simulator |

**Text similarity decision**: TF-IDF (char n-grams 3–5) on fingerprint templates. Embeddings are P2.

## 4. Backend Stack
- **Framework**: FastAPI 0.115.4 (+ uvicorn[standard] 0.32.0). Reason: typed, auto-docs at `/docs`, fast to write.
- **Validation**: pydantic 2.9.2
- **ORM / DB access**: SQLAlchemy 2.0.36 (Core + declarative models)
- **Database**: SQLite 3 (stdlib), file `data/alertlens.db`, WAL mode. Reason: no server, 20k–60k rows is trivial, trivially portable. PostgreSQL is the documented upgrade path.
- **Config**: pydantic-settings 2.6.1 reading `.env`
- **Caching**: none (in-process `functools.lru_cache` for graph and metrics only)
- **Auth**: none (local demo). Documented as out of scope.

## 5. Frontend Stack
- **Framework**: Streamlit 1.40.1 multipage app. Reason: fastest path to 4 pages + replay in 24 h with Python-only team.
- **Charts**: Plotly 5.24.1 (`plotly.express`/`graph_objects`) – timeline, bars, service map (networkx layered layout drawn as Plotly scatter + line traces)
- **HTTP client**: httpx 0.27.2
- **Styling**: `.streamlit/config.toml` theme + one injected CSS file `dashboard/assets/style.css` (see FRONTEND_GUIDELINES.md)
- **Icons**: Unicode/emoji + Streamlit `:material/...:` icons
- **No React, no npm** in the MVP. (If your team is strong in React, swap only the `dashboard/` layer; the API contract in BACKEND_STRUCTURE.md stays identical.)

## 6. DevOps & Tooling
- **Version control**: Git, `main` + short-lived feature branches, PR optional under time pressure; commit at least hourly
- **Testing**: pytest 8.3.3, pytest-cov 5.0.0, httpx TestClient
- **Code quality**: ruff 0.7.1 (lint + format), mypy optional
- **Task runner**: `Makefile` targets (below)
- **Containers**: Docker optional (`python:3.11-slim`); not required to develop
- **CI**: none (GitHub Actions optional if time remains)
- **Hosting for demo**: laptop; fallback = recorded video

## 7. Environment Variables (`.env`)
```
ALERTLENS_DB_PATH=data/alertlens.db
ALERTLENS_SEED=42
ALERTLENS_API_URL=http://localhost:8000
ALERTLENS_DEMO_MODE=1          # forces redaction ON, hides toggle
ALERTLENS_REDACTION_SALT=change-me-local
ALERTLENS_SURFACE_THRESHOLD=0.55
ALERTLENS_PAIR_THRESHOLD=0.60
ALERTLENS_PAIR_WINDOW_MIN=10
ALERTLENS_DEDUP_WINDOW_MIN=5
```
`.env` is git-ignored; commit `.env.example`.

## 8. Dependency Lock (`requirements.txt`)
```
pandas==2.2.3
numpy==1.26.4
networkx==3.4.2
scikit-learn==1.5.2
lightgbm==4.5.0
shap==0.46.0
faker==30.8.2
fastapi==0.115.4
uvicorn[standard]==0.32.0
pydantic==2.9.2
pydantic-settings==2.6.1
SQLAlchemy==2.0.36
streamlit==1.40.1
plotly==5.24.1
httpx==0.27.2
pyarrow==18.0.0
pytest==8.3.3
pytest-cov==5.0.0
ruff==0.7.1
```

## 9. Makefile Targets
```
make setup      # python -m venv .venv && pip install -r requirements.txt
make data       # python -m alertlens.simulator.generate --seed 42
make pipeline   # python -m alertlens.pipeline run --all
make api        # uvicorn alertlens.api.main:app --port 8000 --reload
make ui         # streamlit run dashboard/app.py
make test       # pytest -q
make demo       # make data pipeline, then api & ui
```

## 10. Security Considerations
- Redaction at ingestion: hostnames, IPv4/IPv6, customer IDs (`cust-\d+`, UUIDs, emails) → stable salted-hash tokens (`host-7f3a`, `ip-91c2`, `cust-4d0e`).
- `message_raw` is stored for the toggle but returned only if `DEMO_MODE=0`.
- No endpoint writes to anything except the local `actions` table. A test asserts the `httpx`/`requests` modules are never imported in `pipeline` or `api` write paths.
- Dependencies pinned; no secrets in repo.

## 11. Version Upgrade Policy
Frozen for the hackathon. No upgrades after hour 4 unless a bug blocks the build.

## 12. Performance Budget
- Pipeline on 3 weeks (~20–60k raw alerts): ≤ 5 min
- Pair generation capped: window 10 min, ≤ 200 candidate neighbours per group, negative sampling ratio 1:5 for training
- API responses < 300 ms p95 (SQLite indexes in BACKEND_STRUCTURE.md)
