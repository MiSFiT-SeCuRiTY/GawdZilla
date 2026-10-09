"""
GawdZilla — Database backup + restore + scheduler
Created by MiSFiT SeCuRiTY
"""

import shutil
import sqlite3
import threading
import time
import datetime
from pathlib import Path

from core import config, db


# ──────────────────────────────────────────────────────────────
#  Create
# ──────────────────────────────────────────────────────────────
def make_backup(kind: str = "manual") -> Path:
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
    name = f"gawdzilla-{kind}-{ts}.db"
    target = config.BACKUP_DIR / name

    src = sqlite3.connect(str(config.DB_PATH))
    dst = sqlite3.connect(str(target))
    with dst:
        src.backup(dst)
    dst.close()
    src.close()

    try:
        c = db.conn()
        c.execute(
            "INSERT INTO backups (filename, size_bytes, kind) VALUES (?,?,?)",
            (name, target.stat().st_size, kind),
        )
        c.commit()
        c.close()
    except Exception:
        pass

    enforce_retention()
    return target


# ──────────────────────────────────────────────────────────────
#  Retention
# ──────────────────────────────────────────────────────────────
def enforce_retention():
    """Keep the last N of each kind, delete the rest."""
    for kind, keep in (("auto", config.BACKUP_RETAIN_AUTO),
                       ("manual", config.BACKUP_RETAIN_MANUAL)):
        files = sorted(
            config.BACKUP_DIR.glob(f"gawdzilla-{kind}-*.db"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for old in files[keep:]:
            try: old.unlink()
            except Exception: pass
            try:
                c = db.conn()
                c.execute("DELETE FROM backups WHERE filename=?", (old.name,))
                c.commit()
                c.close()
            except Exception:
                pass


# ──────────────────────────────────────────────────────────────
#  List / restore
# ──────────────────────────────────────────────────────────────
def list_backups():
    return sorted(config.BACKUP_DIR.glob("gawdzilla-*.db"),
                  key=lambda p: p.stat().st_mtime, reverse=True)


def restore_backup(filename: str) -> Path:
    src = config.BACKUP_DIR / Path(filename).name
    if not src.exists():
        raise FileNotFoundError(filename)

    # Snapshot current DB before overwriting
    safety = config.BACKUP_DIR / f"gawdzilla-prerestore-{int(time.time())}.db"
    if config.DB_PATH.exists():
        shutil.copy2(config.DB_PATH, safety)

    shutil.copy2(src, config.DB_PATH)
    return src


# ──────────────────────────────────────────────────────────────
#  Background scheduler
# ──────────────────────────────────────────────────────────────
_scheduler_thread = None
_scheduler_stop = threading.Event()


def _scheduler_loop():
    interval = max(1, config.BACKUP_AUTO_INTERVAL_HOURS) * 3600
    # first run: 2 minutes after start
    _scheduler_stop.wait(120)
    while not _scheduler_stop.is_set():
        try:
            make_backup("auto")
        except Exception as e:
            print(f"[GawdZilla] auto-backup failed: {e}")
        _scheduler_stop.wait(interval)


def start_scheduler():
    global _scheduler_thread
    if _scheduler_thread and _scheduler_thread.is_alive():
        return
    _scheduler_stop.clear()
    _scheduler_thread = threading.Thread(target=_scheduler_loop, daemon=True)
    _scheduler_thread.start()
    print(f"[GawdZilla] backup scheduler started (every "
          f"{config.BACKUP_AUTO_INTERVAL_HOURS}h)")


def stop_scheduler():
    _scheduler_stop.set()


# ──────────────────────────────────────────────────────────────
#  Selective export
# ──────────────────────────────────────────────────────────────
ALL_TABLES = [
    "parents", "children", "devices", "policies",
    "builds", "enroll_tokens", "commands", "audit_log",
    "events", "locations", "geofences", "geofence_events",
    "app_rules", "web_rules", "files", "clips",
    "notifications", "backups", "alerts", "metrics",
]


def export_json(tables=None) -> dict:
    """Return a dict ready to be JSON-serialized."""
    from core import auth
    tables = tables or ALL_TABLES
    c = db.conn()
    dump = {}
    for t in tables:
        if t not in ALL_TABLES:
            continue
        try:
            rows = c.execute(f"SELECT * FROM {t}").fetchall()
            dump[t] = [dict(r) for r in rows]
        except Exception:
            dump[t] = []
    c.close()

    # never leak secrets
    for p in dump.get("parents", []):
        p.pop("pw_hash", None)
        p.pop("totp_secret", None)

    return {
        "meta": {
            "product": config.APP_NAME,
            "version": config.APP_VERSION,
            "author": config.APP_AUTHOR,
            "exported_at": auth.iso(),
            "tables": list(dump.keys()),
        },
        "dump": dump,
    }


def import_json(dump: dict, tables=None, dry_run: bool = True) -> dict:
    """
    Import selected tables from a dump dict.
    dry_run=True returns a report of what would change without writing.
    """
    tables = tables or list(dump.keys())
    report = {}
    c = db.conn()

    for t in tables:
        if t not in ALL_TABLES:
            continue
        if t == "parents":
            report[t] = "skipped (parents never imported)"
            continue
        rows = dump.get(t) or []
        try:
            existing = c.execute(f"SELECT COUNT(*) AS n FROM {t}").fetchone()["n"]
        except Exception:
            report[t] = "table missing"
            continue

        if dry_run:
            report[t] = {"would_delete": existing, "would_insert": len(rows)}
            continue

        try:
            c.execute(f"DELETE FROM {t}")
            for r in rows:
                cols = list(r.keys())
                ph = ",".join(["?"] * len(cols))
                c.execute(
                    f"INSERT INTO {t} ({','.join(cols)}) VALUES ({ph})",
                    tuple(r[k] for k in cols),
                )
            report[t] = {"deleted": existing, "inserted": len(rows)}
        except Exception as e:
            report[t] = f"error: {e}"

    if not dry_run:
        c.commit()
    c.close()
    return report
