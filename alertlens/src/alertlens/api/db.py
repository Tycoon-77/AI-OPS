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
    return conn


def init_db() -> sqlite3.Connection:
    """Create all tables (idempotent — uses IF NOT EXISTS)."""
    conn = get_connection()
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn
