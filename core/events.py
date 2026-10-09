"""
GawdZilla — In-memory event bus + alert + metrics helpers
Created by MiSFiT SeCuRiTY
"""

import queue
import threading


class EventBus:
    def __init__(self):
        self._subs = []
        self._lock = threading.Lock()

    def subscribe(self) -> queue.Queue:
        q = queue.Queue(maxsize=200)
        with self._lock:
            self._subs.append(q)
        return q

    def unsubscribe(self, q: queue.Queue):
        with self._lock:
            if q in self._subs:
                self._subs.remove(q)

    def publish(self, event: dict):
        with self._lock:
            dead = []
            for q in self._subs:
                try:
                    q.put_nowait(event)
                except queue.Full:
                    dead.append(q)
            for q in dead:
                self._subs.remove(q)


BUS = EventBus()


def publish(kind: str, payload: dict, device_id: int = None):
    from core import db
    try:
        c = db.conn()
        c.execute(
            "INSERT INTO events (device_id, kind, payload) VALUES (?,?,?)",
            (device_id, kind, str(payload)[:2000]),
        )
        c.commit()
        c.close()
    except Exception:
        pass
    BUS.publish({"kind": kind, "device_id": device_id, "payload": payload})


def record_metrics(device_id: int, sysinfo: dict):
    """Insert a metrics row from a heartbeat sysinfo blob."""
    from core import db
    try:
        c = db.conn()
        c.execute(
            "INSERT INTO metrics (device_id, cpu, ram, disk, battery) VALUES (?,?,?,?,?)",
            (device_id,
             sysinfo.get("cpu_percent"),
             sysinfo.get("ram_percent"),
             sysinfo.get("disk_percent"),
             sysinfo.get("battery_percent")),
        )
        # Keep only the last 500 rows per device
        c.execute(
            """DELETE FROM metrics WHERE id IN (
                 SELECT id FROM metrics WHERE device_id=?
                 ORDER BY id DESC LIMIT -1 OFFSET 500
               )""",
            (device_id,),
        )
        c.commit()
        c.close()
    except Exception:
        pass


def raise_alert(device_id: int, level: str, title: str, body: str = ""):
    """Create an alert row and publish it on the bus."""
    from core import db
    try:
        c = db.conn()
        c.execute(
            "INSERT INTO alerts (device_id, level, title, body) VALUES (?,?,?,?)",
            (device_id, level, title, body),
        )
        c.commit()
        c.close()
    except Exception:
        pass
    BUS.publish({
        "kind": "alert",
        "device_id": device_id,
        "payload": {"level": level, "title": title, "body": body},
    })


# ──────────────────────────────────────────────────────────────
#  Device online/offline sweeper
# ──────────────────────────────────────────────────────────────
import threading as _th, time as _t

_sweeper_stop = _th.Event()


def _sweeper_loop():
    from core import db
    while not _sweeper_stop.is_set():
        try:
            c = db.conn()
            c.execute("""
                UPDATE devices SET status='offline'
                WHERE status='online'
                  AND (last_seen IS NULL
                       OR last_seen < datetime('now', '-90 seconds'))
            """)
            c.commit()
            c.close()
        except Exception:
            pass
        _sweeper_stop.wait(30)


def start_sweeper():
    if getattr(start_sweeper, "_started", False):
        return
    start_sweeper._started = True
    _th.Thread(target=_sweeper_loop, daemon=True).start()
    print("[GawdZilla] device status sweeper started")
