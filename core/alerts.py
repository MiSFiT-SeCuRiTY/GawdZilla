"""
GawdZilla — Alert rules
Triggers on new-app installs, geofence events, offline devices.
Created by MiSFiT SeCuRiTY
"""

import datetime
from core import db, auth


def record(kind: str, device_id: int, message: str, meta: str = ""):
    c = db.conn()
    try:
        c.execute(
            "INSERT INTO events (device_id, kind, payload) VALUES (?,?,?)",
            (device_id, f"alert_{kind}", f"{message}|{meta}"),
        )
        c.commit()
    except Exception:
        pass
    c.close()


def recent(limit: int = 20):
    c = db.conn()
    rows = c.execute(
        "SELECT e.*, d.name AS device_name FROM events e "
        "LEFT JOIN devices d ON d.id = e.device_id "
        "WHERE e.kind LIKE 'alert_%' "
        "ORDER BY e.id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    c.close()
    out = []
    for r in rows:
        payload = r["payload"] or ""
        msg, _, meta = payload.partition("|")
        out.append({
            "id": r["id"],
            "kind": (r["kind"] or "").replace("alert_", ""),
            "device": r["device_name"] or "—",
            "message": msg,
            "meta": meta,
            "ts": r["ts"],
        })
    return out


def check_offline():
    """Called periodically (or on dashboard load) to flag devices offline >15 min."""
    threshold = (
        datetime.datetime.now(datetime.timezone.utc)
        - datetime.timedelta(minutes=15)
    ).replace(tzinfo=None).isoformat(timespec="seconds")

    c = db.conn()
    rows = c.execute(
        "SELECT id, name, last_seen FROM devices "
        "WHERE status='online' AND (last_seen IS NULL OR last_seen < ?)",
        (threshold,),
    ).fetchall()
    for r in rows:
        c.execute("UPDATE devices SET status='offline' WHERE id=?", (r["id"],))
        record("offline", r["id"], f"{r['name']} went offline", r["last_seen"] or "")
    c.commit()
    c.close()
