"""Schema SQL — AlertLens SQLite database."""

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS runs (
    run_id      TEXT PRIMARY KEY,
    created_at  TEXT NOT NULL,
    seed        INTEGER NOT NULL,
    config_json TEXT NOT NULL,
    model_path  TEXT,
    notes       TEXT
);

CREATE TABLE IF NOT EXISTS services (
    service_id  TEXT PRIMARY KEY,
    tier        INTEGER NOT NULL CHECK (tier BETWEEN 0 AND 3),
    team        TEXT,
    criticality INTEGER NOT NULL DEFAULT 3 CHECK (criticality BETWEEN 1 AND 5)
);

CREATE TABLE IF NOT EXISTS service_edges (
    src_service TEXT NOT NULL REFERENCES services(service_id),
    dst_service TEXT NOT NULL REFERENCES services(service_id),
    PRIMARY KEY (src_service, dst_service)
);

CREATE TABLE IF NOT EXISTS fingerprints (
    fingerprint_id TEXT PRIMARY KEY,
    template       TEXT NOT NULL,
    alert_type     TEXT,
    source         TEXT NOT NULL CHECK (source IN ('monitoring','logging','uptime')),
    first_seen     TEXT,
    volume_total   INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS alerts (
    alert_id         TEXT PRIMARY KEY,
    ts               TEXT NOT NULL,
    source           TEXT NOT NULL CHECK (source IN ('monitoring','logging','uptime')),
    service_id       TEXT NOT NULL REFERENCES services(service_id),
    severity         TEXT NOT NULL CHECK (severity IN ('low','medium','high','critical')),
    severity_num     INTEGER NOT NULL,
    message_raw      TEXT NOT NULL,
    message_redacted TEXT NOT NULL,
    fingerprint_id   TEXT NOT NULL REFERENCES fingerprints(fingerprint_id),
    group_id         TEXT,
    split            TEXT NOT NULL CHECK (split IN ('train','test')),
    truth_incident_id TEXT,
    truth_kind       TEXT
);
CREATE INDEX IF NOT EXISTS idx_alerts_ts           ON alerts(ts);
CREATE INDEX IF NOT EXISTS idx_alerts_group        ON alerts(group_id);
CREATE INDEX IF NOT EXISTS idx_alerts_service_ts   ON alerts(service_id, ts);

CREATE TABLE IF NOT EXISTS alert_groups (
    group_id         TEXT PRIMARY KEY,
    fingerprint_id   TEXT NOT NULL REFERENCES fingerprints(fingerprint_id),
    service_id       TEXT NOT NULL REFERENCES services(service_id),
    source           TEXT NOT NULL,
    first_ts         TEXT NOT NULL,
    last_ts          TEXT NOT NULL,
    alert_count      INTEGER NOT NULL,
    max_severity_num INTEGER NOT NULL,
    split            TEXT NOT NULL,
    truth_incident_id TEXT
);
CREATE INDEX IF NOT EXISTS idx_groups_first ON alert_groups(first_ts);

CREATE TABLE IF NOT EXISTS incidents_truth (
    incident_id          TEXT PRIMARY KEY,
    type                 TEXT NOT NULL,
    start_ts             TEXT NOT NULL,
    end_ts               TEXT NOT NULL,
    root_cause_service   TEXT NOT NULL REFERENCES services(service_id),
    root_cause_description TEXT,
    buried               INTEGER NOT NULL DEFAULT 0,
    split                TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pair_scores (
    run_id          TEXT NOT NULL REFERENCES runs(run_id),
    group_a         TEXT NOT NULL,
    group_b         TEXT NOT NULL,
    score           REAL NOT NULL,
    features_json   TEXT NOT NULL,
    top_reasons_json TEXT,
    PRIMARY KEY (run_id, group_a, group_b)
);

CREATE TABLE IF NOT EXISTS incidents_pred (
    incident_pred_id  TEXT NOT NULL,
    run_id            TEXT NOT NULL REFERENCES runs(run_id),
    title             TEXT NOT NULL,
    day               TEXT NOT NULL,
    first_ts          TEXT NOT NULL,
    last_ts           TEXT NOT NULL,
    origin_group_id   TEXT,
    origin_service    TEXT,
    origin_score      REAL,
    n_alerts_raw      INTEGER NOT NULL,
    n_groups          INTEGER NOT NULL,
    n_services        INTEGER NOT NULL,
    blast_radius      INTEGER NOT NULL,
    max_severity_num  INTEGER NOT NULL,
    history_match     REAL NOT NULL DEFAULT 0,
    history_match_type TEXT,
    priority_score    REAL NOT NULL,
    band              TEXT NOT NULL CHECK (band IN ('RED','ORANGE','YELLOW','BACKGROUND')),
    surfaced          INTEGER NOT NULL,
    surfaced_ts       TEXT,
    surface_reason    TEXT,
    reasons_json      TEXT NOT NULL,
    PRIMARY KEY (run_id, incident_pred_id)
);
CREATE INDEX IF NOT EXISTS idx_pred_day ON incidents_pred(run_id, day, surfaced);

CREATE TABLE IF NOT EXISTS incident_members (
    run_id            TEXT NOT NULL,
    incident_pred_id  TEXT NOT NULL,
    group_id          TEXT NOT NULL REFERENCES alert_groups(group_id),
    origin_rank       INTEGER NOT NULL,
    origin_score      REAL NOT NULL,
    dep_path_from_origin TEXT,
    PRIMARY KEY (run_id, incident_pred_id, group_id),
    FOREIGN KEY (run_id, incident_pred_id) REFERENCES incidents_pred(run_id, incident_pred_id)
);

CREATE TABLE IF NOT EXISTS noise_candidates (
    run_id               TEXT NOT NULL,
    fingerprint_id       TEXT NOT NULL REFERENCES fingerprints(fingerprint_id),
    service_id           TEXT,
    volume               INTEGER NOT NULL,
    incident_involvement INTEGER NOT NULL,
    precursor_rate       REAL NOT NULL,
    pattern              TEXT,
    recommendation_type  TEXT NOT NULL CHECK (recommendation_type IN
        ('raise_threshold','merge_rule','downgrade_severity','require_consecutive','keep')),
    recommendation_text  TEXT NOT NULL,
    evidence_json        TEXT NOT NULL,
    PRIMARY KEY (run_id, fingerprint_id, service_id)
);

CREATE TABLE IF NOT EXISTS actions (
    action_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT NOT NULL,
    actor       TEXT NOT NULL DEFAULT 'demo-user',
    target_type TEXT NOT NULL CHECK (target_type IN ('incident','noise_candidate')),
    target_id   TEXT NOT NULL,
    action_type TEXT NOT NULL CHECK (action_type IN ('acknowledge','escalate','approve','ignore')),
    note        TEXT
);
CREATE INDEX IF NOT EXISTS idx_actions_target ON actions(target_type, target_id);

CREATE TABLE IF NOT EXISTS metrics (
    run_id      TEXT NOT NULL,
    name        TEXT NOT NULL,
    split       TEXT NOT NULL,
    value       REAL,
    detail_json TEXT,
    PRIMARY KEY (run_id, name, split)
);
"""
