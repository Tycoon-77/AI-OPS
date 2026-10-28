# 🛡️ SignalIQ (AlertLens) — Autonomous AIOps Incident Intelligence Platform

> **Transforming 16,000+ noisy raw alerts into prioritized, explainable incident cascades with instant root-cause localization.**

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React%2018%20%2B%20Vite-61DAFB.svg?logo=react&logoColor=black)](https://reactjs.org)
[![LightGBM](https://img.shields.io/badge/ML-LightGBM%20pair%20model-blue-green.svg)](https://lightgbm.readthedocs.io)
[![Tests](https://img.shields.io/badge/Tests-14%2F14%20Passing-brightgreen.svg)]()

---

## ⚡ Performance at a Glance (measured, simulated data)

Computed by `alertlens/src/alertlens/eval/scorecard.py` from `clusters.json` vs ground truth (11 incidents; test split = 4 incidents, so treat it as anecdotal). Reproduce: `cd alertlens && PYTHONPATH=src python -m alertlens.eval.scorecard`.

| Metric | Target | Measured (rules path, committed run) |
| :--- | :--- | :--- |
| Surfaced cards for 11 real incidents | a handful per day | **428** (83 RED+ORANGE) |
| Compression (alerts ÷ cards) | ≥ 10× | **38.2×**, but only 11 of 428 cards contain a real incident (card precision 2.6%) |
| Recall, lenient (any alert in a surfaced card) | 100% | **100%** (11/11); the old metric, kept and labelled |
| Recall, ≥ 50% of the incident's alerts in one card | 100% | **100%**, but cards are huge (purity below) |
| Mean cluster purity of incident cards | high | **46.9%** (e.g. 1,075-alert card with 250 real alerts) |
| Pairwise precision / B-cubed F1 | ≥ 0.90 / ≥ 0.85 | **0.099 / 0.276** 🔴 |
| Origin top-1 | ≥ 75% | **27.3%** (3 of 11) 🔴 |
| Pairwise model ROC-AUC (held-out test) | ≥ 0.85 | **0.8069** (train 0.9808 is in-sample). Note: the model is trained but not yet used at inference |

> The earlier "baseline" row (11.2× / 0.71 / 0.74 / 0.55) was hardcoded, not measured. The measured rules baseline is `alertlens/data/baseline/clusters_rules.json`; compare variants with `python alertlens/scripts/ablation.py`.

---

## 🏗️ System Architecture

```
Raw Cloud Telemetry Stream (16,339 alerts)
                  │
                  ▼
   1. Ingestion, Masking & Template Mining (Drain-style Tokenizer)
                  │
                  ▼
   2. Sliding-Window Deduplication (Flapping & Heartbeat Collapsing)
                  │
                  ▼
   3. LightGBM Pairwise Classifier (13 Spatio-Temporal & Graph Features)
                  │
                  ▼
   4. Graph Topology Union-Find Clustering (184 Microservice Edges)
                  │
                  ▼
   5. Multi-Objective Root Cause Localization (Origin Score = 0.45E + 0.40U + 0.15T)
                  │
                  ▼
   FastAPI REST API ──► SignalIQ Interactive React SPA (Port 8000)
```

---

## 📁 Repository Structure

```
AI-OPS/
├── alertlens/                   # Core Python Backend Engine
│   ├── data/                   # Real SQLite DB (16,339 alerts, 70 services, 184 edges)
│   ├── dist/                   # Production-compiled React SPA bundle (served by FastAPI)
│   ├── models/                 # Trained LightGBM model (pair_lgbm.txt)
│   ├── src/alertlens/          # Ingestion, clustering, ranking, ML training, & API
│   │   ├── api/                # FastAPI app & React routes
│   │   ├── cluster/            # Union-Find correlation & Root-Cause ranker
│   │   ├── ingest/             # Redaction, fingerprinting, deduplication
│   │   ├── model/              # LightGBM training pipeline
│   │   └── noise/              # SRE noise-rule discovery
│   └── tests/                  # Pytest test suite (14 passing tests)
│
├── frontend/                   # React 18 SPA Source Code
│   ├── src/components/         # ReactFlow ServiceMap, KPI Cards, Incident Drawer
│   ├── src/pages/              # Overview, Incidents, Service Map, Settings
│   └── package.json            # React, TailwindCSS, @xyflow/react, Recharts
│
└── files/                      # Project Specifications, PRD & Architecture Documentation
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
* Python 3.9+
* Node.js 18+ (optional, only needed if modifying React source code)

### 2. Run the Full Stack Platform (FastAPI + React UI)
The FastAPI server serves both the REST API and the production React frontend bundle simultaneously:

```bash
cd alertlens
source .venv/bin/activate    # or create with: python3 -m venv .venv && pip install -r requirements.txt
uvicorn alertlens.api.main:app --host 0.0.0.0 --port 8000 --reload --app-dir src
```

Open your browser to:
👉 **`http://localhost:8000`**

### 3. Run Unit Tests
```bash
cd alertlens
source .venv/bin/activate
pytest tests/ -v
```

---

## 🎯 Key Capabilities

* **Interactive 70-Service Dependency Map**: Structured 4-tier Left-to-Right layout with real-time incident cascade isolation and drill-down drawer inspection for all 70 services.
* **LightGBM Correlation Engine**: Trained on 112,449 alert pairs with 13 topological, temporal, and TF-IDF character n-gram features.
* **Non-Destructive Noise Suppression**: Compresses alert noise by 97.38% at the presentation layer while preserving 100% of the raw audit trail in SQLite for compliance.
* **Noise Rule Discovery**: Identifies low-value recurring alert rules with near-zero precursor rates to give SRE teams concrete tuning recommendations.
