# Frontend Design System – AlertLens

Applies to the Streamlit dashboard in `dashboard/`. Goal: calm, dense, ops-grade UI that makes 5 incidents feel obviously better than 612 alerts.

## 1. Design Principles
1. **Signal first**: the answer ("612 → 5") is the biggest thing on the screen.
2. **Explain everything**: no grouping, origin or priority is shown without a reason within one click.
3. **Colour never alone**: every severity uses colour + text label + icon.
4. **Quiet by default**: noise lives in collapsed sections; only incidents are loud.
5. **Honest**: "SIMULATED DATA" tag always visible; "Recorded only" language on every action.
6. **Safe**: buttons say what they do, and never imply they change a live system.

## 2. Design Tokens

### Colour Palette (dark theme, default)
| Token | Hex | Use |
|---|---|---|
| `--bg` | `#0B1020` | app background |
| `--surface` | `#121A2F` | cards, panels |
| `--surface-2` | `#1A2440` | hover, table stripes |
| `--border` | `#2A3558` | 1 px borders |
| `--text` | `#E6EAF5` | primary text (contrast ≥ 12:1 on bg) |
| `--text-muted` | `#9AA6C6` | secondary text (≥ 5.5:1) |
| `--accent` | `#6C8CFF` | links, primary buttons, focus ring |
| `--sev-critical` | `#FF4D5E` | RED band / origin node |
| `--sev-high` | `#FF9F43` | ORANGE band / affected node |
| `--sev-medium` | `#F5D547` | YELLOW band |
| `--sev-low` | `#7C8AAE` | background / healthy node (grey) |
| `--ok` | `#3DDC97` | success, recorded, ✓ |
| `--info` | `#4DB6FF` | info banners |

Band mapping: **RED** = priority ≥ 0.75 or any critical severity; **ORANGE** = 0.55–0.75; **YELLOW** = surfaced but < 0.55 (history-match safety net); **BACKGROUND** = not surfaced.

### Typography
- **Body/UI**: Inter, fallback `system-ui, sans-serif`
- **Mono (alerts, IDs, times)**: JetBrains Mono, fallback `ui-monospace, monospace`
- **Scale**: Page title 28/700 · Section 20/600 · Card title 16/600 · Body 14/400 · Caption 12/400 · Big KPI 44/700 (mono)
- Line height 1.45 body, 1.2 headings.

### Spacing Scale (px)
`4, 8, 12, 16, 24, 32, 48`. Card padding 16; gap between cards 12; page side padding 24.

### Radius & Shadow
- Radius: chips 999, buttons 8, cards 12
- Shadow: cards `0 1px 2px rgba(0,0,0,.4)`; no heavy shadows.

## 3. Layout System
- Streamlit `layout="wide"`. Sidebar = navigation + date picker + filters + Redact toggle.
- **Incidents page**: row 1 KPI strip (3 tiles: Raw alerts, Incidents, Reduction %) · row 2 two columns (hourly line chart 60% | before/after bar 40%) · row 3 replay bar · row 4 cards (full width, stacked) · row 5 "Background (n)" expander.
- **Detail page**: title row · stats row (4 tiles) · two columns (Timeline 50% | Service map 50%) · "Why grouped" panel · alerts table · action row.
- **Noise page**: banner · bar chart · table.
- **Scorecard**: 4–5 KPI tiles · two charts · failure modes text.
- Breakpoints: ≥ 1280 two-column layouts; < 900 stack to one column.

## 4. Component Library

### Incident Card
- Container: `--surface`, 12 px radius, 4 px left border in band colour.
- Content: band badge (e.g. `● RED · CRITICAL`), title, meta line (`Started 14:00 · 7 services · 58 alerts`), `Likely cause: <service>` (mono), reason one-liner (muted), **View details** button (primary, right).
- States: default, hover (`--surface-2`), acknowledged (adds `✓ Acknowledged` chip), new-in-replay (1 s highlight pulse).

### KPI Tile
Label (caption, muted) · value (44 px mono) · delta/subtext. Reduction tile shows `612 → 5`.

### Badges / Chips
Pill, 12 px, uppercase. Variants: RED, ORANGE, YELLOW, BACKGROUND, ACKNOWLEDGED, ESCALATED, WEAK LINK, KEEP.

### Buttons
| Type | Use | Style |
|---|---|---|
| Primary | View details, Play, Approve | `--accent` fill, white text |
| Secondary | Acknowledge, Pause, Ignore | transparent, 1 px `--border` |
| Danger-ish | Escalate | `--sev-critical` outline |
- Height 36, padding 0 16, label in sentence case, disabled = 40% opacity + `not-allowed`.
- Every action button has `help=` tooltip: "Recorded only. No live system is changed."

### Tables (alerts, noise)
Zebra with `--surface`/`--surface-2`, sticky header, mono for time/service columns, severity as badge. Max 50 rows/page.

### Banners
Info (`--info`), warning (`--sev-medium`), error (`--sev-critical`), success (`--ok`). Icon + text, dismissible except SIMULATED DATA and "Suggestions only".

### Charts (Plotly)
- Template: transparent paper/plot bg, grid `--border` at 40% opacity, font Inter 12.
- **Hourly line**: x hour, y alerts; markers at hours with surfaced incidents.
- **Before/after bar**: two horizontal bars, raw (grey) vs incidents (accent), value labels outside.
- **Timeline**: scatter, x time, y service (sorted by tier), marker size by count, origin = star, colour by severity.
- **Service map**: networkx layered layout, y = tier (infra bottom → edge top), x spread by name hash; nodes: origin red + glow ring, affected orange, other grey (opacity .35); edges grey, edges on the origin→affected path accent-coloured; hover shows service, tier, first alert time. Node labels only for origin + affected.
- Always include alt text/caption sentence under each chart for accessibility.

## 5. Accessibility Guidelines (WCAG 2.1 AA)
- Contrast ≥ 4.5:1 body, ≥ 3:1 large text/UI.
- Severity: text label + icon + colour.
- Keyboard: all buttons reachable by Tab; visible focus ring 2 px `--accent`.
- Chart summaries in text below each chart ("5 incidents; largest began 14:00 at Database").
- Don't rely on hover for essential info (the Why panel is always visible).
- Respect `prefers-reduced-motion`: no pulse animation.

## 6. Animation Guidelines
- Allowed: 150–200 ms fades for cards entering; 1 s highlight on new/updated cards in replay.
- Not allowed: bouncing, long slide-ins, auto-scrolling.
- Replay refresh target: ≤ 4 UI refreshes per second regardless of speed (batch events per tick).

## 7. Icon System
Material symbols via Streamlit (`:material/warning:`, `:material/hub:`, `:material/schedule:`, `:material/check_circle:`, `:material/volume_off:`). Size 18–20 px, always paired with text.

## 8. State Indicators
- **Loading**: `st.spinner("Loading incidents…")` or skeleton blocks; > 3 s adds "still working".
- **Empty**: icon + one sentence + next step (e.g. "No incidents need attention. View Background (23)").
- **Error**: banner + Retry; never raw exceptions.
- **Success**: toast 3 s.
- **Replay running**: sticky chip `▶ REPLAY · 14:32:10 · 60×`.

## 9. Copy Rules
- Plain language: "Likely cause", "Why these were grouped", "Suggestion".
- Never say "fixed", "resolved", "muted" for recorded actions; say "Recorded".
- Mandatory microcopy: `SIMULATED DATA` tag (top bar); `Suggestions only – nothing is changed automatically` (Noise page); `Recorded only. No live system was changed.` (after any action).

## 10. Redaction in UI
- Redacted tokens displayed in mono with a subtle underline dotted style; tooltip "masked value".
- Redact toggle in sidebar; when `DEMO_MODE=1` it is shown disabled and ON.

## 11. Streamlit Implementation Notes
- `.streamlit/config.toml`:
```
[theme]
base = "dark"
primaryColor = "#6C8CFF"
backgroundColor = "#0B1020"
secondaryBackgroundColor = "#121A2F"
textColor = "#E6EAF5"
font = "sans serif"
```
- Shared helpers in `dashboard/components/`: `card.py`, `kpi.py`, `charts.py`, `badges.py`, `api.py`. Pages must not call `httpx` directly; they use `api.py`.
- Inject CSS once in `dashboard/theme.py` via `st.markdown("<style>…</style>", unsafe_allow_html=True)`.
- Cache GETs with `st.cache_data(ttl=30)`, except during replay.
- Keys: `st.session_state` keys prefixed `al_` (e.g. `al_day`, `al_redact`, `al_replay_idx`).

## 12. Browser Support
Latest Chrome/Edge/Firefox/Safari. Demo machine: Chrome, 1920×1080, zoom 100%.
