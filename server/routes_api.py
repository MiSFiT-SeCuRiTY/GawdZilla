"""
GawdZilla — JSON API
Created by MiSFiT SeCuRiTY
"""

import datetime
from flask import jsonify, request, send_file
from flask_login import login_required, current_user

from core import db, config, auth, events, backups


def register(app):

    @app.route("/api/status")
    def api_status():
        c = db.conn()
        d = c.execute("SELECT COUNT(*) AS n FROM devices").fetchone()["n"]
        o = c.execute("SELECT COUNT(*) AS n FROM devices WHERE status='online'").fetchone()["n"]
        ch = c.execute("SELECT COUNT(*) AS n FROM children").fetchone()["n"]
        p = c.execute("SELECT COUNT(*) AS n FROM policies WHERE enabled=1").fetchone()["n"]
        c.close()
        return jsonify(ok=True, app=config.APP_NAME, version=config.APP_VERSION,
                       devices=d, online=o, children=ch, policies=p, ts=auth.iso())

    @app.route("/api/devices")
    @login_required
    def api_devices():
        c = db.conn()
        rows = [dict(r) for r in c.execute("SELECT * FROM devices ORDER BY last_seen DESC").fetchall()]
        c.close()
        return jsonify(ok=True, devices=rows)

    @app.route("/api/children")
    @login_required
    def api_children():
        c = db.conn()
        rows = [dict(r) for r in c.execute("SELECT * FROM children ORDER BY name").fetchall()]
        c.close()
        return jsonify(ok=True, children=rows)

    @app.route("/api/policies")
    @login_required
    def api_policies():
        c = db.conn()
        rows = [dict(r) for r in c.execute("SELECT * FROM policies ORDER BY created_at DESC").fetchall()]
        c.close()
        return jsonify(ok=True, policies=rows)

    @app.route("/api/events")
    @login_required
    def api_events():
        limit = int(request.args.get("limit", 100))
        c = db.conn()
        rows = [dict(r) for r in c.execute(
            "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()]
        c.close()
        return jsonify(ok=True, events=rows)

    @app.route("/api/device/<int:did>/command", methods=["POST"])
    @login_required
    def api_device_command(did):
        data = request.get_json(silent=True) or {}
        cmd = data.get("cmd")
        if not cmd:
            return jsonify(ok=False, error="missing cmd"), 400
        c = db.conn()
        c.execute("INSERT INTO commands (device_id, cmd, payload) VALUES (?,?,?)",
                  (did, cmd, data.get("payload") or ""))
        c.commit()
        c.close()
        db.audit(current_user.username, f"cmd:{cmd}", f"device:{did}")
        events.publish("command", {"cmd": cmd, "device_id": did}, did)
        return jsonify(ok=True, queued=cmd)

    # ── Backups ─────────────────────────────────────────
    @app.route("/api/backups")
    @login_required
    def api_backups():
        rows = []
        for p in backups.list_backups():
            rows.append({"filename": p.name, "size_bytes": p.stat().st_size})
        return jsonify(ok=True, backups=rows)

    @app.route("/api/backups/create", methods=["POST"])
    @login_required
    def api_backup_create():
        p = backups.make_backup("manual")
        db.audit(current_user.username, "backup.create", p.name)
        return jsonify(ok=True, filename=p.name, size_bytes=p.stat().st_size)

    @app.route("/api/backups/download/<path:filename>")
    @login_required
    def api_backup_download(filename):
        p = config.BACKUP_DIR / filename
        if not p.exists():
            return jsonify(ok=False, error="not found"), 404
        return send_file(str(p), as_attachment=True)

    @app.route("/api/backups/restore/<path:filename>", methods=["POST"])
    @login_required
    def api_backup_restore(filename):
        try:
            backups.restore_backup(filename)
            db.audit(current_user.username, "backup.restore", filename)
            return jsonify(ok=True)
        except Exception as e:
            return jsonify(ok=False, error=str(e)), 400

    # ── File sync ───────────────────────────────────────
    @app.route("/api/files")
    @login_required
    def api_files():
        c = db.conn()
        rows = [dict(r) for r in c.execute(
            "SELECT * FROM files ORDER BY id DESC LIMIT 200"
        ).fetchall()]
        c.close()
        return jsonify(ok=True, files=rows)

    # ── Clipboard sync ──────────────────────────────────
    @app.route("/api/clips")
    @login_required
    def api_clips():
        c = db.conn()
        rows = [dict(r) for r in c.execute(
            "SELECT * FROM clips ORDER BY id DESC LIMIT 200"
        ).fetchall()]
        c.close()
        return jsonify(ok=True, clips=rows)

    # ── Notifications ───────────────────────────────────
    @app.route("/api/notifications")
    @login_required
    def api_notifications():
        c = db.conn()
        rows = [dict(r) for r in c.execute(
            "SELECT * FROM notifications ORDER BY id DESC LIMIT 200"
        ).fetchall()]
        c.close()
        return jsonify(ok=True, notifications=rows)


# ──────────────────────────────────────────────────────────────
#  Block 13 — metrics + alerts + live map data
# ──────────────────────────────────────────────────────────────
def _extend(app):
    from flask import jsonify, request
    from flask_login import login_required
    from core import db

    @app.route("/api/metrics/<int:did>")
    @login_required
    def api_metrics(did):
        limit = int(request.args.get("limit", 100))
        c = db.conn()
        rows = [dict(r) for r in c.execute(
            """SELECT cpu, ram, disk, battery, ts FROM metrics
               WHERE device_id=? ORDER BY id DESC LIMIT ?""",
            (did, limit)
        ).fetchall()]
        c.close()
        rows.reverse()
        return jsonify(ok=True, points=rows)

    @app.route("/api/alerts")
    @login_required
    def api_alerts():
        c = db.conn()
        rows = [dict(r) for r in c.execute(
            "SELECT * FROM alerts ORDER BY id DESC LIMIT 50"
        ).fetchall()]
        c.close()
        return jsonify(ok=True, alerts=rows)

    @app.route("/api/alerts/mark_seen", methods=["POST"])
    @login_required
    def api_alerts_mark_seen():
        c = db.conn()
        c.execute("UPDATE alerts SET seen=1 WHERE seen=0")
        c.commit()
        c.close()
        return jsonify(ok=True)

    @app.route("/api/locations/latest")
    @login_required
    def api_locations_latest():
        c = db.conn()
        rows = c.execute("""
            SELECT l.device_id, d.name AS device_name, l.lat, l.lon, l.accuracy_m, l.ts
            FROM locations l
            JOIN (
              SELECT device_id, MAX(id) AS max_id
              FROM locations GROUP BY device_id
            ) latest ON l.id = latest.max_id
            LEFT JOIN devices d ON d.id = l.device_id
        """).fetchall()
        c.close()
        return jsonify(ok=True, points=[dict(r) for r in rows])
