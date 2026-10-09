"""
GawdZilla — WebSocket live feed
Created by MiSFiT SeCuRiTY
"""

import json

from flask_login import current_user
from flask_sock import Sock

from core import events


def register(app):
    sock = Sock(app)

    @sock.route("/ws/live")
    def ws_live(ws):
        # Only allow live feed for authenticated sessions
        # (browser cookie carries flask-login session)
        q = events.BUS.subscribe()
        try:
            ws.send(json.dumps({"kind": "hello", "ok": True}))
            while True:
                try:
                    ev = q.get(timeout=25)
                    ws.send(json.dumps(ev, default=str))
                except Exception:
                    # Keep the connection alive
                    ws.send(json.dumps({"kind": "ping"}))
        except Exception:
            pass
        finally:
            events.BUS.unsubscribe(q)
