# Product Requirements Document (PRD)

## 1. Product Overview
- **Project Title**: AlertLens (placeholder name) – incident-level alert correlation for AO-01 "Four hundred alerts, three real incidents"
- **Version**: 1.0 (hackathon MVP, 24 hours)
- **Last Updated**: 28 Oct 2026
- **Owner**: Team of three (A: data/ML, B: clustering/analysis, C: dashboard/demo)

## 2. Problem Statement
A SaaS platform with 70 services emits 400–900 alerts/day from monitoring, logging and uptime tools. Most are the same few underlying faults seen from different angles (one failing database triggers latency alerts on every dependent service). On-call engineers bulk-acknowledge, and twice this year a real outage sat buried for over an hour.

**Job to be done:** reduce what an on-call engineer must look at to the few genuinely distinct situations that need a human, without hiding any real incident.

## 3. Goals & Objectives
### Business Goals
- G1: Reduce notifications per underlying incident by ≥ 90% (raw alerts → surfaced incident cards) on the test week.
- G2: Surface 100% of real incidents in the test week (including the 2 buried ones) and ≥ 90% of the held-out incident type.
- G3: Median time-to-surface ≤ 2 minutes after the first alert of an incident (in replay time).
- G4: Pairwise precision ≥ 0.90 and B-cubed F1 ≥ 0.85 against ground truth.
- G5: 100% of surfaced incidents carry a visible, human-readable reason.

### User Goals
- See what needs attention right now in under 10 seconds.
- Know where an incident most likely started and why alerts were grouped.
- Get safe, reviewable suggestions to tune useless alert rules.

## 4. Success Metrics
| Metric | Definition | Target |
|---|---|---|
| Compression | raw alerts/day ÷ surfaced incidents/day (test week) | ≥ 50× (≥ 90% reduction minimum) |
| Recall | real incidents with ≥1 member alert inside a surfaced cluster ÷ all real incidents | 100% (target), 0 buried incidents missed |
| Time-to-surface | first alert of incident → cluster crosses surface threshold (replay clock) | median ≤ 120 s |
| Pairwise precision / recall | on alert-group pairs vs ground truth | P ≥ 0.90, R ≥ 0.80 |
| B-cubed F1 | clustering quality vs ground truth | ≥ 0.85 |
| Origin accuracy | top-ranked origin service == true root cause service | ≥ 75% (top-1), ≥ 90% (top-3) |
| Explainability | surfaced incidents with ≥ 1 reason sentence | 100% |
| Held-out type recall | certificate-expiry incidents surfaced | ≥ 90% |

Measured by `eval/metrics.py` on the time-split test week; results shown on the Scorecard page and README. All numbers are on **simulated data** and labelled as such.

## 5. Target Users & Personas
### Primary Persona: Riya, on-call SRE
- **Demographics**: 26–35, 3–7 yrs experience, rotating on-call shifts, often at night.
- **Pain Points**: alert fatigue, bulk-acknowledging, can't tell cause from symptom, fear of missing the real one.
- **Goals**: a short prioritised list, probable origin, evidence she can trust in 30 seconds.
- **Technical Proficiency**: High (knows the services, not the ML).

### Secondary Persona: Arjun, SRE/platform lead
- **Demographics**: 35–45, owns monitoring quality and on-call health.
- **Pain Points**: hundreds of rules nobody dares to delete; no data on which rules ever mattered.
- **Goals**: ranked noise-rule list with evidence and tuning recommendations; KPI proof.
- **Technical Proficiency**: High.

### Tertiary: Hackathon judges
Need to understand the idea in 30 seconds, see it work live, and verify honesty (simulated data, failure modes).

## 6. Features & Requirements
### Must-Have Features (P0)
1. **Synthetic data simulator**
   - Description: Generates 3 weeks of alerts, service graph, incident records with ground truth.
   - User Story: As the team, we want labelled realistic data so that we can train and honestly evaluate.
   - Acceptance Criteria:
     - [ ] Produces `dependencies.json` (70 services, 4 tiers), `alerts.csv`, `incidents.csv` from a fixed seed; re-run gives byte-identical files
     - [ ] 400–900 baseline alerts/day; incident days spike higher
     - [ ] ≥ 8 incident types incl. certificate expiry; 2 buried incidents flagged `buried=true`
     - [ ] Includes flapping duplicates, multi-tool duplicates, chatty noise rules, message variants
   - Success Metric: noise share of alerts ≥ 70%; ground-truth coverage 100% of incident alerts.

2. **Ingestion, redaction, fingerprinting, de-duplication**
   - User Story: As an engineer, I want repeat alerts collapsed and sensitive values masked so that I see signal, not clutter.
   - Acceptance Criteria:
     - [ ] Hostnames, IPs, customer IDs masked before display; masked tokens are stable (same input → same token)
     - [ ] Variable parts (numbers, hosts, IDs) stripped to a template fingerprint
     - [ ] Same fingerprint + service within 5 min collapses to one alert group with a count
     - [ ] Every raw alert maps to exactly one group
   - Success Metric: dedup reduces raw rows by ≥ 30% with zero cross-incident merges in ground truth.

3. **Pair classifier + clustering**
   - User Story: As an engineer, I want related alerts grouped so that one fault = one card.
   - Acceptance Criteria:
     - [ ] Train/test split by time (weeks 1–2 train, week 3 test); cert-expiry excluded from training
     - [ ] LightGBM pair model with time gap, graph distance, text similarity, same source/severity, co-occurrence prior
     - [ ] Clusters built from pair scores via thresholded connected components with Louvain split for oversized components
     - [ ] A rules-only baseline exists and is reported next to the learned model
   - Success Metric: G4 targets.

4. **Origin ranking**
   - Acceptance Criteria:
     - [ ] Each cluster ranks alerts by earliness + upstream depth; top-1 flagged "probable origin"
     - [ ] Dependency path from origin to each affected service is available
   - Success Metric: origin accuracy targets.

5. **Prioritisation + recall safety net**
   - Acceptance Criteria:
     - [ ] Priority score from severity, services affected, blast radius, history similarity; maps to bands RED/ORANGE/YELLOW
     - [ ] Any cluster with critical severity OR history similarity ≥ threshold is always surfaced
     - [ ] Nothing is dropped: low-priority clusters go to a collapsed "Background" list, still viewable
   - Success Metric: recall target.

6. **Explanations ("why grouped")**
   - Acceptance Criteria:
     - [ ] Each incident shows ≥ 3 plain-language reasons (time window, dependency path, template similarity)
     - [ ] SHAP top-3 features available per strong edge
   - Success Metric: 100% explainability.

7. **Noise-candidate finder**
   - Acceptance Criteria:
     - [ ] Per fingerprint: volume, precursor count, precursor rate, recommendation (raise threshold / merge rule / downgrade severity / require N consecutive)
     - [ ] Computed from training period only, evaluated on test period
     - [ ] Approve/Ignore buttons only record a decision
   - Success Metric: ≥ 80% of ground-truth noise rules appear in the top-10 candidates; 0 noise candidates that preceded a real incident in test week.

8. **Dashboard (4 pages) + replay**
   - Acceptance Criteria:
     - [ ] Incidents, Incident Detail, Noise Candidates, Scorecard pages as in APP_FLOW.md
     - [ ] Replay streams a chosen day with Play/Pause/Speed; counter and cards update live
     - [ ] Redaction is ON by default and in demo mode cannot be turned off
   - Success Metric: full demo path completes in ≤ 3 minutes without errors.

9. **Human-in-the-loop action log**
   - Acceptance Criteria:
     - [ ] Acknowledge, Escalate, Approve, Ignore are written to the `actions` table only
     - [ ] No outbound call to any monitoring/alerting system exists in the codebase
   - Success Metric: code review + test asserting no network writes.

### Should-Have Features (P1)
1. **Live alert generator** for streaming into the replay (reuses simulator).
2. **Merge/split recommendation** buttons (recorded only).
3. **Filters** by band, service, date.
4. **Failure-modes page** in the Scorecard (held-out type results, buried-incident results).

### Nice-to-Have Features (P2)
1. Sentence-embedding similarity (replace TF-IDF).
2. Export incident report as Markdown.
3. Dark/light theme toggle.

## 7. Explicitly OUT OF SCOPE
- Replacing or integrating with a real monitoring stack (Prometheus, Datadog, etc.)
- Automated remediation, auto-mute, auto-close or any write to live systems
- Paging, escalation policies, on-call rota management
- User accounts, authentication, multi-tenancy
- Real-time ingestion from real tools (simulated replay only)
- Mobile-native app
- Deep learning / LLM-based correlation
- Training on real customer data
- Cloud autoscaling, HA deployment

## 8. User Scenarios
### Scenario 1: Morning triage
- **Context**: Riya starts a shift; 612 alerts arrived overnight.
- **Steps**: 1) Opens Incidents; header shows "612 → 5". 2) Sees one RED card "Database slow", 58 alerts. 3) Clicks View details. 4) Sees timeline, graph with Database glowing, reasons. 5) Clicks Acknowledge.
- **Expected Outcome**: She understands the incident in < 30 s; action is logged, nothing else changes.
- **Edge Cases**: no incidents that day → empty state "No incidents need attention" plus Background list link; API down → error banner with retry.

### Scenario 2: Buried outage
- **Context**: A real payment outage starts during a noisy batch period.
- **Steps**: 1) Replay the buried day. 2) Noise count climbs. 3) Payment cluster crosses threshold and a RED card appears. 4) Detail shows origin and reasons.
- **Expected Outcome**: Incident surfaced within 2 min replay time, ahead of the "lost for an hour" baseline.
- **Edge Cases**: payment alerts partly merged with unrelated noise → cluster splits via Louvain; shown reason lists the weaker edges.

### Scenario 3: Rule cleanup
- **Context**: Arjun reviews monthly rule health.
- **Steps**: 1) Opens Noise Candidates. 2) Sorts by volume. 3) Reads evidence "340 fires, 0 precursors". 4) Clicks Approve on "raise threshold to 90%".
- **Expected Outcome**: Decision recorded with note; a banner states "Recorded only; apply it in your monitoring tool".
- **Edge Cases**: rule has 2 precursors in test week → flagged "Keep" with explanation, no Approve button emphasised.

## 9. Dependencies & Constraints
- **Technical**: Python 3.11; runs on a laptop; no GPU; whole pipeline < 5 min end to end.
- **Business**: 24 hours, 3 people, demo in front of judges.
- **External**: none required at runtime. Optional: LogHub wording for message templates (offline, not needed).

## 10. Timeline & Milestones (24 h)
- **Hour 3**: Simulator output + tiny sample ready.
- **Hour 8 (MVP baseline)**: rules baseline clusters + 2 dashboard pages working on generated data.
- **Hour 16**: learned classifier, origin, priority, noise candidates, API.
- **Hour 20**: all 4 pages + replay.
- **Hour 24**: metrics report, README, demo video, slides. **Freeze code at hour 22.**

## 11. Risks & Assumptions
### Risks
- Synthetic circularity (model learns generator rules) → randomised propagation, missing hops, noise overlap, held-out type, explicit README disclosure.
- Time overrun → rules baseline at hour 8 guarantees a demoable build.
- Giant connected component (everything merges in a busy minute) → score threshold tuning + Louvain split + max cluster size guard.
- Over-compression hides an incident → safety net + recall as first-class metric.

### Assumptions
- Ground truth in generated data is correct (validated by unit tests on the simulator).
- Dependency map is accurate (assumed; stated as a limitation).

## 12. Non-Functional Requirements
- **Performance**: batch pipeline ≤ 5 min on 3 weeks of data; API p95 < 300 ms; dashboard page load < 2 s; replay at 60× smooth.
- **Security**: masked hostnames/IPs/customer IDs by default; no secrets in repo; local-only deployment; actions are append-only.
- **Accessibility**: WCAG 2.1 AA contrast; severity shown by text label and icon, not colour alone.
- **Scalability**: design handles 10× volume via indexed time-windowed queries (documented, not built).

## 13. References & Resources
- Problem statement AO-01 (HackBridge Pro)
- Online Boutique / Sock Shop (service structure seed)
- LogHub (optional wording)
