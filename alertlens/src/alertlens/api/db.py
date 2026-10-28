"""DB connection helpers."""
import sqlite3
from pathlib import Path

from alertlens.config import settings
from alertlens.api.schema import SCHEMA_SQL


def get_connection() -> sqlite3.Connection:
    db_path = Path(settings.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _hide_stale_sample_rows(conn)
    return conn


def _hide_stale_sample_rows(conn: sqlite3.Connection) -> None:
    """Read-only workaround (no data is deleted).

    The committed DB still contains the 30 hand-made sample alerts (ids a001..a030)
    on top of the 16,339 real alerts, because ingest/load.py never clears old rows.
    Real alert ids look like ``alt_NNNNNN``. TEMP views shadow the tables for
    every read in the API so dashboard counts match data/alerts.csv.
    Remove this once ingest resets its tables (needs a change in ingest/, which is
    outside the eval-ui folders).
    """
    try:
        tables = {r[0] for r in conn.execute("SELECT name FROM main.sqlite_master WHERE type='table'")}
        if "alerts" not in tables:
            return
        conn.execute(
            "CREATE TEMP VIEW alerts AS SELECT * FROM main.alerts WHERE alert_id LIKE 'alt\\_%' ESCAPE '\\'"
        )
        if "alert_groups" in tables:
            conn.execute(
                "CREATE TEMP VIEW alert_groups AS SELECT * FROM main.alert_groups WHERE group_id IN "
                "(SELECT DISTINCT group_id FROM main.alerts WHERE alert_id LIKE 'alt\\_%' ESCAPE '\\')"
            )
    except sqlite3.Error:
        pass


def init_db() -> sqlite3.Connection:
    """Create all tables (idempotent — uses IF NOT EXISTS)."""
    conn = get_connection()
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn
