# SignalIQ – Less Alert Noise. More Incident Intelligence.

> **AO-01 Problem Statement:** Four hundred alerts, three real incidents.

SignalIQ is an AI-powered alert correlation and incident intelligence platform designed for Site Reliability Engineers (SREs), DevOps engineers, and IT operations teams.

---

## 🎯 Key Architectural Principles

1. **Zero Destructive Actions Principle:** SignalIQ never deletes, mutes, or closes original alerts. 100% of telemetry, host metadata, and raw collector payloads are strictly preserved.
2. **Probable vs. Confirmed Cause:** Recommendations are mathematically graded with explicit confidence scores and evidence chains. Probable conclusions are visually distinguished from confirmed metric facts.
3. **Four-Axis Correlation Engine:**
   - **Time Proximity:** Sliding burst window clustering.
   - **Service Dependency Topology:** Directed graph traversal across upstream and downstream tiers.
   - **Semantic Text Similarity:** Cosine distance over alert message embeddings.
   - **Historical Association:** Fingerprint matching against recurring operational patterns.

---

## 🛠️ Technology Stack

- **Framework:** React 19 + Vite 8
- **Styling:** Tailwind CSS v4 + Obsidian Dark Mode design system
- **Routing:** React Router DOM v7
- **Data Visualizations:** Recharts
- **Service Dependency Graph:** React Flow (`@xyflow/react`)
- **Iconography:** Lucide React
- **API Client:** Axios with automatic backend autodetection & local fallback engine

---

## 🚀 Getting Started

### Prerequisites

- Node.js `v18+` (v20+ or v24+ recommended)
- npm `v9+`

### 1. Installation

```bash
# Clone the repository and navigate to the project directory
cd frontend

# Install dependencies
npm install
```

### 2. Environment Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

Ensure `VITE_API_BASE_URL` points to your Python FastAPI backend (default is `http://localhost:8000`):

```env
VITE_API_BASE_URL=http://localhost:8000
```

> **Note:** If the FastAPI backend is not running, SignalIQ automatically runs in **Live Demo Mode** using the 400-alert synthetic benchmark dataset without any broken UI or errors.

### 3. Start the Development Server

```bash
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

### 4. Build for Production

```bash
npm run build
npm run preview
```

---

## 📱 Pages & Features

| # | Page | Route | Description |
|---|---|---|---|
| 1 | **Overview Dashboard** | `/` | KPI metrics (400 alerts, 375 correlated, 93.75% noise cut), hourly volume chart, severity donut, incidents table, activity feed. |
| 2 | **Alert Explorer** | `/alerts` | Full 400-alert table, drag-and-drop CSV/JSON upload, real-time search, filters (Severity, Service, Status), pagination, slide-over telemetry inspector, CSV export. |
| 3 | **Incident Intelligence** | `/incidents` | Incident card grid and table list, confidence ratings, affected services, correlation engine trigger. |
| 3b | **Incident Detail** | `/incidents/:id` | Incident summary, probable root cause, confirmed vs probable evidence, chronological alert stream, correlation rationale. |
| 4 | **Root Cause Analysis** | `/root-cause` | Dedicated investigation interface, incident selector, directional failure propagation chain (`Database -> Payment -> API Gateway -> Orders`), hypothesis confidence meter. |
| 5 | **Service Map** | `/service-map` | Interactive React Flow canvas, node health color coding, pan/zoom controls, incident chain highlighting, node inspector drawer. |
| 6 | **Alert Analytics** | `/analytics` | 6 interactive charts (total vs correlated, hourly trends, severity, service distribution, deduplication rates) + transparent evaluation benchmarks (Precision: 94.2%, Recall: 96.1%, F1: 0.951). |
| 7 | **Settings** | `/settings` | General preferences, alert thresholds, correlation sliding window & similarity sliders, account & security profile. |

---

## 🔌 FastAPI Integration Endpoints

SignalIQ is wired to communicate with the following FastAPI endpoints:

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/alerts/upload` | Ingest CSV/JSON telemetry file and run deduplication |
| `GET` | `/api/alerts` | Query alerts with pagination, service, severity, and search |
| `GET` | `/api/alerts/{id}` | Inspect raw alert telemetry and metadata |
| `POST` | `/api/incidents/detect` | Trigger on-demand correlation clustering |
| `GET` | `/api/incidents` | Retrieve correlated incidents list |
| `GET` | `/api/incidents/{id}` | Retrieve incident summary, evidence, and affected services |
| `GET` | `/api/analytics/summary` | Query aggregated metrics, hourly charts, and model scores |
| `GET` | `/api/services/graph` | Fetch nodes, edges, and service health status |

---

## 🎨 Design System Palette

- **Main Background:** `#0B1020`
- **Sidebar Background:** `#111827`
- **Card Background:** `#151D2E`
- **Secondary Background:** `#1E293B`
- **Primary Accent:** `#6366F1` (Indigo)
- **Secondary Accent:** `#38BDF8` (Sky)
- **Critical / Danger:** `#EF4444`
- **Warning / Degraded:** `#F59E0B`
- **Success / Healthy:** `#22C55E`
- **Border:** `#293449`
