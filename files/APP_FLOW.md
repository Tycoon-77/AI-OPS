# Application Flow Documentation – AlertLens

## 1. Entry Points
- **Direct URL**: `http://localhost:8501` opens **Incidents** (home) for the latest day in the test week.
- **Deep link**: `/Incident_Detail?incident_id=<id>` opens a specific incident (used by cards and by the demo script).
- **Demo link**: `/?day=YYYY-MM-DD&replay=1` opens the chosen day with replay ready.
- No login, no OAuth, no marketing entry points (local hackathon tool, no auth).

## 2. Core User Flows

### Flow 1: Triage the day
**Goal**: Know what needs a human now.
**Entry Point**: Incidents page.
**Frequency**: Every shift / every demo.

#### Happy Path
1. **Page: Incidents**
   - Elements: header counter ("612 alerts → 5 incidents"), hourly line chart, before/after bar, incident cards, "Background (n)" expander, date picker, band/service filters, Redact toggle, Replay controls
   - User Action: reads cards (sorted RED → ORANGE → YELLOW, then newest)
   - Trigger: clicks **View details** on a card
2. **Page: Incident Detail** (Flow 2)

#### Error States
- **API unreachable**: red banner "Cannot reach backend", Retry button; page shows last cached data if present.
- **No data for date**: empty state "No alerts for this day", date picker stays active.
- **No surfaced incidents**: "No incidents need attention" + link to Background list.

#### Edge Cases
- Day with > 20 incidents → show top 20, "Show all" button.
- Date outside data range → picker clamps to range.

#### Exit Points
- Detail page, Noise page, Scorecard page, tab close.

---

### Flow 2: Understand one incident
**Goal**: Trust or reject the grouping, find the origin, record a decision.
**Entry Point**: View details, or deep link.

#### Happy Path
1. **Page: Incident Detail**
   - Elements: title + band badge, stats row (first/last time, alerts, services, blast radius), **Timeline** (dots per alert group; origin starred), **Service map** (origin red, affected orange, healthy grey, edges = depends-on), **Why grouped** panel (3+ sentences + top evidence edges), **Alerts table** (time, service, source, severity, message-redacted, count), Acknowledge / Escalate buttons, optional note field
   - User Action: reviews, clicks **Acknowledge** or **Escalate**
   - System Action: `POST /actions` writes a row; toast "Recorded. No live system was changed."
2. Back to Incidents via breadcrumb.

#### Error States
- **Incident ID not found**: "Incident not found" + link to Incidents.
- **Action save fails**: error toast, buttons re-enabled, nothing assumed saved.

#### Edge Cases
- Incident with 300+ alerts → table paginated (50/page); timeline downsampled with count labels.
- Already acknowledged → button shows "Acknowledged ✓" and timestamp; Escalate still available.
- Low-confidence edges → "Why grouped" shows a yellow "Weak link" tag.

---

### Flow 3: Review noisy rules
**Goal**: Decide which suggestions to accept.
**Entry Point**: Noise Candidates tab.

#### Happy Path
1. **Page: Noise Candidates**
   - Elements: bar chart (top 10 by volume), table (rule/fingerprint, service, times fired, precursor count, precursor rate, recommendation, evidence), Approve / Ignore buttons, info banner "Suggestions only"
   - User Action: sorts, expands evidence, clicks **Approve** or **Ignore**
   - System Action: `POST /actions`; row shows status chip "Approved (recorded)".

#### Error States / Edge Cases
- Rule with ≥ 1 precursor in history → row flagged "Keep – has preceded incidents"; Approve disabled.
- Empty table → "No noise candidates found".

---

### Flow 4: Replay a day (demo flow)
**Goal**: Show incidents forming live.
**Entry Point**: Replay controls on Incidents page.

#### Happy Path
1. User picks a date, presses **Play**.
2. Page requests `GET /replay/{date}`; receives ordered events.
3. Clock advances at selected speed (1×, 10×, 60×, 300×). Raw counter climbs; cards appear/grow/change band as events arrive; origin star appears when determined.
4. At end, banner "Day complete: 612 → 5 incidents". **Pause**, **Reset** available any time.

#### Error States / Edge Cases
- Pause mid-way then change date → replay resets.
- Replay on a day with no incidents → counter climbs, "Background only" message.
- Browser rerun/refresh → replay state lost; resets to start (documented).

---

### Flow 5: Read the scorecard
**Goal**: Verify quality and honesty.
1. **Page: Scorecard** – elements: big numbers (compression, recall, time-to-surface, precision, B-cubed F1), before/after bar, learned vs baseline comparison, held-out type result, buried incident result, failure-modes text, "Simulated data" banner.
2. Edge: no metrics yet → "Run the pipeline" instructions (shows the one command).

## 3. Navigation Map
```
AlertLens (Streamlit multipage; sidebar nav)
├── Incidents (home)            /
│   ├── Replay controls (inline)
│   └── Incident card → Incident Detail
├── Incident Detail             /Incident_Detail?incident_id=
├── Noise Candidates            /Noise_Candidates
└── Scorecard                   /Scorecard
Global: top bar = Redact toggle, date picker, run id badge, "SIMULATED DATA" tag
```

### Navigation Rules
- **Authentication Required**: none.
- **Redirect Logic**: invalid/missing `incident_id` → Incidents with warning toast.
- **Back Button Behavior**: date, filters and selected incident are kept in `st.session_state` and query params; replay state is not preserved.

## 4. Screen Inventory

### Screen: Incidents
- **Route**: `/`
- **Access**: Public (local)
- **Purpose**: triage
- **Key Elements**: KPI header, hourly chart, cards, background list, replay bar
- **Actions**: View details, filter, change date, Play/Pause/Reset/Speed, Redact toggle
- **State Variations**: loading (skeletons), empty, error, replay-running

### Screen: Incident Detail
- **Route**: `/Incident_Detail`
- **Purpose**: evidence and decision
- **Key Elements**: timeline, service map, why panel, alerts table, action buttons
- **State Variations**: loading, not found, already-acknowledged

### Screen: Noise Candidates
- **Route**: `/Noise_Candidates`
- **Key Elements**: bar chart, suggestion table, Approve/Ignore, "suggestions only" banner

### Screen: Scorecard
- **Route**: `/Scorecard`
- **Key Elements**: metric tiles, before/after bar, model comparison, failure modes, data disclaimer

## 5. Decision Points
```
Open Incidents
  └─ API ok?
       ├─ no  → error banner + Retry
       └─ yes → surfaced incidents > 0?
                  ├─ no  → empty state + Background link
                  └─ yes → show cards
                           └─ click card → Detail
                                 └─ Acknowledge | Escalate | Back
```

## 6. Responsive Behavior
- Desktop-first (≥ 1280 px demo screen). Tablet (≥ 768 px) stacks timeline above map. Phone is best-effort, not tested.

## 7. Error & Loading Standards
- Loading: skeleton or spinner with text, max 3 s before showing "still working".
- Errors: banner with plain text and Retry; never show stack traces.
- Toasts: success (green, 3 s), error (red, until dismissed).
- Every write action explains: "Recorded only. No live system was changed."
