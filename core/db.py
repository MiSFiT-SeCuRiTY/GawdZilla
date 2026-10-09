"""
GawdZilla — Database layer
SQLite schema, connection helper, init, migrations.
Created by MiSFiT SeCuRiTY
"""

import sqlite3
import datetime
from pathlib import Path

from core import config


# ──────────────────────────────────────────────────────────────
#  Schema
# ──────────────────────────────────────────────────────────────
SCHEMA = """
PRAGMA foreign_keys = ON;

-- Parents / admins
CREATE TABLE IF NOT EXISTS parents (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT UNIQUE NOT NULL,
    pw_hash       TEXT NOT NULL,
    totp_secret   TEXT,
    role          TEXT NOT NULL DEFAULT 'parent',   -- admin | parent
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login    TIMESTAMP
);

-- Children
CREATE TABLE IF NOT EXISTS children (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    birthdate     TEXT,
    notes         TEXT,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Devices (agents registered by children)
CREATE TABLE IF NOT EXISTS devices (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    child_id      INTEGER REFERENCES children(id) ON DELETE SET NULL,
    name          TEXT,
    platform      TEXT,        -- windows | linux | android
    os_version    TEXT,
    arch          TEXT,
    agent_version TEXT,
    enroll_token  TEXT UNIQUE,
    hw_id         TEXT,
    last_seen     TIMESTAMP,
    status        TEXT DEFAULT 'offline',   -- online | offline
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Policies
CREATE TABLE IF NOT EXISTS policies (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    scope         TEXT NOT NULL,     -- family | child | device
    scope_id      INTEGER,
    name          TEXT NOT NULL,
    enabled       INTEGER DEFAULT 1,
    config_json   TEXT,              -- full policy JSON
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Builds (Builder outputs)
CREATE TABLE IF NOT EXISTS builds (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    platform      TEXT,
    os_version    TEXT,
    arch          TEXT,
    child_id      INTEGER,
    capabilities  TEXT,          -- comma-separated
    server_url    TEXT,
    enroll_token  TEXT,
    filename      TEXT,
    sha256        TEXT,
    size_bytes    INTEGER,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Enrollment tokens (pending device pairing)
CREATE TABLE IF NOT EXISTS enroll_tokens (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    token         TEXT UNIQUE NOT NULL,
    child_id      INTEGER REFERENCES children(id) ON DELETE CASCADE,
    platform      TEXT,
    expires_at    TIMESTAMP,
    used          INTEGER DEFAULT 0,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Command queue (parent -> device)
CREATE TABLE IF NOT EXISTS commands (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id     INTEGER REFERENCES devices(id) ON DELETE CASCADE,
    cmd           TEXT NOT NULL,
    payload       TEXT,
    status        TEXT DEFAULT 'queued',   -- queued | sent | done | failed
    result        TEXT,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audit log
CREATE TABLE IF NOT EXISTS audit_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    actor         TEXT,
    action        TEXT,
    target        TEXT,
    meta          TEXT,
    ts            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common lookups
CREATE INDEX IF NOT EXISTS idx_devices_child      ON devices(child_id);
CREATE INDEX IF NOT EXISTS idx_devices_token      ON devices(enroll_token);
CREATE INDEX IF NOT EXISTS idx_devices_status     ON devices(status);
CREATE INDEX IF NOT EXISTS idx_policies_scope     ON policies(scope, scope_id);
CREATE INDEX IF NOT EXISTS idx_builds_created     ON builds(created_at);
CREATE INDEX IF NOT EXISTS idx_cmd_device_status  ON commands(device_id, status);
CREATE INDEX IF NOT EXISTS idx_audit_ts           ON audit_log(ts);
"""


# ──────────────────────────────────────────────────────────────
#  Connection
# ──────────────────────────────────────────────────────────────
def conn() -> sqlite3.Connection:
    """Return a SQLite connection with Row factory."""
    c = sqlite3.connect(str(config.DB_PATH), timeout=15)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    c.execute("PRAGMA journal_mode = WAL")
    return c


# ──────────────────────────────────────────────────────────────
#  Init
# ──────────────────────────────────────────────────────────────
def init():
    """Create tables if they do not exist."""
    c = conn()
    c.executescript(SCHEMA)
    c.commit()
    c.close()


# ──────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────
def audit(actor: str, action: str, target: str = "", meta: str = ""):
    """Insert an audit log row."""
    c = conn()
    c.execute(
        "INSERT INTO audit_log (actor, action, target, meta) VALUES (?,?,?,?)",
        (actor, action, target, meta),
    )
    c.commit()
    c.close()


def now_iso() -> str:
    return datetime.datetime.utcnow().isoformat(timespec="seconds")


# ──────────────────────────────────────────────────────────────
#  CLI test
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init()
    c = conn()
    tables = [r[0] for r in c.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()]
    c.close()
    print(f"[GawdZilla] DB initialized at: {config.DB_PATH}")
    print(f"[GawdZilla] Tables: {', '.join(tables)}")
