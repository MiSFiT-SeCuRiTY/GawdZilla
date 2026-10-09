"""
GawdZilla — Real-time pages and APIs
Device detail with charts, live map data, alert feed.
Created by MiSFiT SeCuRiTY
"""

import json
from flask import render_template, request, jsonify
from flask_login import login_required

from core import db, alerts


def register(app):

    # ──────────────────────────────────────────────────────────────
    #  Device detail page
    # ──────────────────────────────────────────────────────────────
    @app.route("/admin/device/<int:did>")
    @login_required
    def device_detail_page(did):
        c = db.conn()
        dev = c.execute(
            "SELECT d.*, ch.name AS child_name FROM devices d "
            "LEFT JOIN children ch ON ch.id = d.child_id WHERE d.id=?",
            (did,),
        ).fetchone()
        if not dev:
            c.close()
            return "Device not found", 404

        cmds = c.execute(
            "SELECT id, cmd, status, substr(result,1,120) AS result, created_at "
            "FROM commands WHERE device_id=? ORDER BY id DESC LIMIT 30",
            (did,),
        ).fetchall()
        evts = c.execute(
            "SELECT kind, substr(payload,1,100) AS payload, ts FROM events "
            "WHERE device_id=? ORDER BY id DESC LIMIT 40",
            (did,),
        ).fetchall()
        locs = c.execute(
            "SELECT lat, lon, accuracy_m, ts FROM locations WHERE device_id=? "
            "ORDER BY id DESC LIMIT 5",
            (did,),
        ).fetchall()
        c.close()
        return render_template(
            "device_detail.html",
            dev=dev, cmds=cmds, evts=evts, locs=locs,
        )

    # ──────────────────────────────────────────────────────────────
    #  Chart data
    # ──────────────────────────────────────────────────────────────
    @app.route("/api/device/<int:did>/chart/cpu")
    @login_required
    def api_chart_cpu(did):
        limit = int(request.args.get("limit", 60))
        c = db.conn()
        rows = c.execute(
            "SELECT payload, ts FROM events WHERE device_id=? AND kind='heartbeat' "
            "ORDER BY id DESC LIMIT ?",
            (did, limit),
        ).fetchall()
        c.close()
        out = []
        for r in rows:
            try:
                cpu = None
                p = r["payload"] or ""
                # payload format: {'name': ..., 'cpu': ..., 'ram': ..., 'disk': ...}
                import ast
                d = ast.literal_eval(p)
                cpu = d.get("cpu")
            except Exception:
                cpu = None
            out.append({"ts": r["ts"], "value": cpu})
        out.reverse()
        return jsonify(ok=True, points=out)

    @app.route("/api/device/<int:did>/chart/ram")
    @login_required
    def api_chart_ram(did):
        limit = int(request.args.get("limit", 60))
        c = db.conn()
        rows = c.execute(
            "SELECT payload, ts FROM events WHERE device_id=? AND kind='heartbeat' "
            "ORDER BY id DESC LIMIT ?",
            (did, limit),
        ).fetchall()
        c.close()
        out = []
        for r in rows:
            try:
                import ast
                d = ast.literal_eval(r["payload"] or "{}")
                ram = d.get("ram")
            except Exception:
                ram = None
            out.append({"ts": r["ts"], "value": ram})
        out.reverse()
        return jsonify(ok=True, points=out)

    @app.route("/api/device/<int:did>/chart/battery")
    @login_required
    def api_chart_battery(did):
        limit = int(request.args.get("limit", 60))
        c = db.conn()
        rows = c.execute(
            "SELECT payload, ts FROM events WHERE device_id=? AND kind='heartbeat' "
            "ORDER BY id DESC LIMIT ?",
            (did, limit),
        ).fetchall()
        c.close()
        out = []
        for r in rows:
            try:
                import ast
                d = ast.literal_eval(r["payload"] or "{}")
                b = d.get("battery")
            except Exception:
                b = None
            out.append({"ts": r["ts"], "value": b})
        out.reverse()
        return jsonify(ok=True, points=out)

    # ──────────────────────────────────────────────────────────────
    #  Alerts feed
    # ──────────────────────────────────────────────────────────────
    @app.route("/api/alerts")
    @login_required
    def api_alerts():
        limit = int(request.args.get("limit", 20))
        return jsonify(ok=True, alerts=alerts.recent(limit))

    # ──────────────────────────────────────────────────────────────
    #  Trigger offline check on demand
    # ──────────────────────────────────────────────────────────────
    @app.route("/api/alerts/check-offline", methods=["POST"])
    @login_required
    def api_check_offline():
        alerts.check_offline()
        return jsonify(ok=True)

    # ──────────────────────────────────────────────────────────────
    #  All latest device positions (for live map)
    # ──────────────────────────────────────────────────────────────
    @app.route("/api/locations/latest")
    @login_required
    def api_locations_latest():
        c = db.conn()
        devices = c.execute("SELECT id, name, platform, status FROM devices").fetchall()
        out = []
        for d in devices:
            row = c.execute(
                "SELECT lat, lon, accuracy_m, ts FROM locations "
                "WHERE device_id=? ORDER BY id DESC LIMIT 1",
                (d["id"],),
            ).fetchone()
            if row:
                out.append({
                    "device_id": d["id"],
                    "name": d["name"],
                    "platform": d["platform"],
                    "status": d["status"],
                    "lat": row["lat"],
                    "lon": row["lon"],
                    "accuracy_m": row["accuracy_m"],
                    "ts": row["ts"],
                })
        c.close()
        return jsonify(ok=True, devices=out)
