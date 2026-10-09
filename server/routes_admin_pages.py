"""
GawdZilla — Admin pages
Children, devices, policies, audit, monitor, location, apps, web, sync,
remote, terminal, map, charts, backup, settings.
Created by MiSFiT SeCuRiTY
"""

import json
from flask import (
    render_template, request, redirect, url_for, jsonify,
    send_file, abort,
)
from flask_login import login_required, current_user

from core import db, config, events, backups


def register(app):

    # ──────────────────────────────────────────────────────────────
    #  CHILDREN
    # ──────────────────────────────────────────────────────────────
    @app.route("/admin/children", methods=["GET", "POST"])
    @login_required
    def children_page():
        if request.method == "POST":
            name = (request.form.get("name") or "").strip()
            birthdate = (request.form.get("birthdate") or "").strip()
            notes = (request.form.get("notes") or "").strip()
            if name:
                c = db.conn()
                c.execute(
                    "INSERT INTO children (name, birthdate, notes) VALUES (?,?,?)",
                    (name, birthdate, notes),
                )
                c.commit()
                c.close()
                db.audit(current_user.username, "child.create", name)
            return redirect(url_for("children_page"))
        c = db.conn()
        children = c.execute("SELECT * FROM children ORDER BY name").fetchall()
        c.close()
        return render_template("devices.html", children=children, devices=[], view="children")

    @app.route("/admin/children/<int:cid>/delete", methods=["POST"])
    @login_required
    def child_delete(cid):
        c = db.conn()
        c.execute("DELETE FROM children WHERE id=?", (cid,))
        c.commit()
        c.close()
        db.audit(current_user.username, "child.delete", str(cid))
        return redirect(url_for("children_page"))

    # ──────────────────────────────────────────────────────────────
    #  DEVICES
    # ──────────────────────────────────────────────────────────────
    @app.route("/admin/devices")
    @login_required
    def devices_page():
        c = db.conn()
        devices = c.execute(
            "SELECT d.*, ch.name AS child_name FROM devices d "
            "LEFT JOIN children ch ON ch.id = d.child_id "
            "ORDER BY d.last_seen DESC"
        ).fetchall()
        children = c.execute("SELECT * FROM children ORDER BY name").fetchall()
        c.close()
        return render_template("devices.html", devices=devices, children=children, view="devices")

    @app.route("/admin/devices/<int:did>/delete", methods=["POST"])
    @login_required
    def device_delete(did):
        c = db.conn()
        c.execute("DELETE FROM devices WHERE id=?", (did,))
        c.commit()
        c.close()
        db.audit(current_user.username, "device.delete", str(did))
        return redirect(url_for("devices_page"))

    @app.route("/admin/devices/<int:did>/assign", methods=["POST"])
    @login_required
    def device_assign(did):
        cid = request.form.get("child_id") or None
        c = db.conn()
        c.execute("UPDATE devices SET child_id=? WHERE id=?", (cid, did))
        c.commit()
        c.close()
        db.audit(current_user.username, "device.assign", f"{did}->{cid}")
        return redirect(url_for("devices_page"))

    # ──────────────────────────────────────────────────────────────
    #  POLICIES
    # ──────────────────────────────────────────────────────────────
    @app.route("/admin/policies", methods=["GET", "POST"])
    @login_required
    def policies_page():
        if request.method == "POST":
            scope = request.form.get("scope") or "family"
            scope_id = request.form.get("scope_id") or None
            name = (request.form.get("name") or "").strip()
            enabled = 1
            config_json = {
                "screen_time_minutes": int(request.form.get("screen_time") or 0),
                "bedtime_start":       request.form.get("bedtime_start") or "",
                "bedtime_end":         request.form.get("bedtime_end") or "",
                "internet_pause":      bool(request.form.get("internet_pause")),
                "blocked_apps":        [x.strip() for x in (request.form.get("blocked_apps") or "").split(",") if x.strip()],
                "blocked_sites":       [x.strip() for x in (request.form.get("blocked_sites") or "").split(",") if x.strip()],
            }
            if name:
                c = db.conn()
                c.execute(
                    "INSERT INTO policies (scope, scope_id, name, enabled, config_json) VALUES (?,?,?,?,?)",
                    (scope, scope_id, name, enabled, json.dumps(config_json)),
                )
                c.commit()
                c.close()
                db.audit(current_user.username, "policy.create", name)
            return redirect(url_for("policies_page"))
        c = db.conn()
        policies = c.execute("SELECT * FROM policies ORDER BY created_at DESC").fetchall()
        children = c.execute("SELECT * FROM children ORDER BY name").fetchall()
        c.close()
        return render_template("policies.html", policies=policies, children=children)

    @app.route("/admin/policies/<int:pid>/delete", methods=["POST"])
    @login_required
    def policy_delete(pid):
        c = db.conn()
        c.execute("DELETE FROM policies WHERE id=?", (pid,))
        c.commit()
        c.close()
        db.audit(current_user.username, "policy.delete", str(pid))
        return redirect(url_for("policies_page"))

    # ──────────────────────────────────────────────────────────────
    #  AUDIT
    # ──────────────────────────────────────────────────────────────
    @app.route("/admin/audit")
    @login_required
    def audit_page():
        c = db.conn()
        rows = c.execute("SELECT * FROM audit_log ORDER BY ts DESC LIMIT 200").fetchall()
        c.close()
        return render_template("audit.html", rows=rows)

    # ──────────────────────────────────────────────────────────────
    #  MONITOR
    # ──────────────────────────────────────────────────────────────
    @app.route("/admin/monitor")
    @login_required
    def monitor_page():
        c = db.conn()
        devs = c.execute(
            "SELECT id, name, platform, status, last_seen FROM devices ORDER BY last_seen DESC"
        ).fetchall()
        ev = c.execute("SELECT * FROM events ORDER BY id DESC LIMIT 50").fetchall()
        c.close()
        return render_template("monitor.html", devices=devs, events=ev)

    # ──────────────────────────────────────────────────────────────
    #  LOCATION
    # ──────────────────────────────────────────────────────────────
    @app.route("/admin/location")
    @login_required
    def location_page():
        c = db.conn()
        devices = c.execute(
            "SELECT id, name, platform, status, last_seen FROM devices ORDER BY last_seen DESC"
        ).fetchall()

        latest = {}
        for d in devices:
            row = c.execute(
                "SELECT lat, lon, accuracy_m, ts FROM locations WHERE device_id=? ORDER BY id DESC LIMIT 1",
                (d["id"],),
            ).fetchone()
            if row:
                latest[d["id"]] = dict(row)

        geofences = c.execute("SELECT * FROM geofences ORDER BY created_at DESC").fetchall()
        gfe = c.execute(
            "SELECT gfe.*, g.name AS fence_name, d.name AS device_name FROM geofence_events gfe "
            "LEFT JOIN geofences g ON g.id = gfe.geofence_id "
            "LEFT JOIN devices d ON d.id = gfe.device_id "
            "ORDER BY gfe.id DESC LIMIT 50"
        ).fetchall()
        c.close()
        return render_template(
            "location.html",
            devices=devices,
            latest=latest,
            geofences=geofences,
            geofence_events=gfe,
        )

    @app.route("/admin/location/geofences/create", methods=["POST"])
    @login_required
    def geofence_create():
        name = (request.form.get("name") or "").strip()
        try:
            lat = float(request.form.get("lat") or 0)
            lon = float(request.form.get("lon") or 0)
            radius = float(request.form.get("radius_m") or 100)
        except ValueError:
            return redirect(url_for("location_page"))
        child_id = request.form.get("child_id") or None
        if not name:
            return redirect(url_for("location_page"))
        c = db.conn()
        c.execute(
            "INSERT INTO geofences (name, lat, lon, radius_m, child_id, notify_on_enter, notify_on_exit) "
            "VALUES (?,?,?,?,?,?,?)",
            (name, lat, lon, radius, child_id,
             1 if request.form.get("notify_on_enter") == "on" else 0,
             1 if request.form.get("notify_on_exit") == "on" else 0),
        )
        c.commit()
        c.close()
        db.audit(current_user.username, "geofence.create", name)
        return redirect(url_for("location_page"))

    @app.route("/admin/location/geofences/<int:gid>/delete", methods=["POST"])
    @login_required
    def geofence_delete(gid):
        c = db.conn()
        c.execute("DELETE FROM geofences WHERE id=?", (gid,))
        c.commit()
        c.close()
        db.audit(current_user.username, "geofence.delete", str(gid))
        return redirect(url_for("location_page"))

    @app.route("/api/location/<int:did>")
    @login_required
    def api_location_device(did):
        limit = int(request.args.get("limit", 500))
        c = db.conn()
        rows = [dict(r) for r in c.execute(
            "SELECT lat, lon, accuracy_m, speed_mps, ts FROM locations WHERE device_id=? ORDER BY id DESC LIMIT ?",
            (did, limit),
        ).fetchall()]
        c.close()
        return jsonify(ok=True, points=rows)

    @app.route("/api/geofences")
    @login_required
    def api_geofences():
        c = db.conn()
        rows = [dict(r) for r in c.execute("SELECT * FROM geofences").fetchall()]
        c.close()
        return jsonify(ok=True, geofences=rows)

    # ──────────────────────────────────────────────────────────────
    #  MAP + CHARTS
    # ──────────────────────────────────────────────────────────────
    @app.route("/admin/map")
    @login_required
    def map_page():
        return render_template("live_map.html")

    @app.route("/admin/charts")
    @login_required
    def charts_page():
        c = db.conn()
        devices = c.execute(
            "SELECT id, name, platform FROM devices ORDER BY last_seen DESC"
        ).fetchall()
        c.close()
        return render_template("charts.html", devices=devices)

    # ──────────────────────────────────────────────────────────────
    #  APPS
    # ──────────────────────────────────────────────────────────────
    @app.route("/admin/apps", methods=["GET", "POST"])
    @login_required
    def apps_page():
        if request.method == "POST":
            device_id = request.form.get("device_id") or None
            child_id  = request.form.get("child_id") or None
            package   = (request.form.get("package") or "").strip()
            name      = (request.form.get("name") or "").strip()
            action    = request.form.get("action") or "block"
            if package:
                c = db.conn()
                c.execute(
                    "INSERT INTO app_rules (device_id, child_id, package, name, action) VALUES (?,?,?,?,?)",
                    (device_id, child_id, package, name, action),
                )
                c.commit()
                c.close()
                db.audit(current_user.username, "app_rule.create", package)
            return redirect(url_for("apps_page"))

        c = db.conn()
        rules = c.execute("""
            SELECT ar.*, d.name AS device_name, ch.name AS child_name
            FROM app_rules ar
            LEFT JOIN devices d ON d.id = ar.device_id
            LEFT JOIN children ch ON ch.id = ar.child_id
            ORDER BY ar.created_at DESC
        """).fetchall()
        devices = c.execute("SELECT id, name FROM devices ORDER BY name").fetchall()
        children = c.execute("SELECT id, name FROM children ORDER BY name").fetchall()
        c.close()
        return render_template("apps.html", rules=rules, devices=devices, children=children)

    @app.route("/admin/apps/<int:rid>/delete", methods=["POST"])
    @login_required
    def app_rule_delete(rid):
        c = db.conn()
        c.execute("DELETE FROM app_rules WHERE id=?", (rid,))
        c.commit()
        c.close()
        db.audit(current_user.username, "app_rule.delete", str(rid))
        return redirect(url_for("apps_page"))

    @app.route("/api/app_rules")
    @login_required
    def api_app_rules():
        c = db.conn()
        rows = [dict(r) for r in c.execute("SELECT * FROM app_rules ORDER BY id DESC").fetchall()]
        c.close()
        return jsonify(ok=True, rules=rows)

    # ──────────────────────────────────────────────────────────────
    #  WEB
    # ──────────────────────────────────────────────────────────────
    @app.route("/admin/web", methods=["GET", "POST"])
    @login_required
    def web_page():
        if request.method == "POST":
            device_id = request.form.get("device_id") or None
            child_id  = request.form.get("child_id") or None
            domain    = (request.form.get("domain") or "").strip().lower()
            action    = request.form.get("action") or "block"
            category  = (request.form.get("category") or "").strip()
            if domain:
                c = db.conn()
                c.execute(
                    "INSERT INTO web_rules (device_id, child_id, domain, action, category) VALUES (?,?,?,?,?)",
                    (device_id, child_id, domain, action, category),
                )
                c.commit()
                c.close()
                db.audit(current_user.username, "web_rule.create", domain)
            return redirect(url_for("web_page"))

        c = db.conn()
        rules = c.execute("""
            SELECT wr.*, d.name AS device_name, ch.name AS child_name
            FROM web_rules wr
            LEFT JOIN devices d ON d.id = wr.device_id
            LEFT JOIN children ch ON ch.id = wr.child_id
            ORDER BY wr.created_at DESC
        """).fetchall()
        devices = c.execute("SELECT id, name FROM devices ORDER BY name").fetchall()
        children = c.execute("SELECT id, name FROM children ORDER BY name").fetchall()
        c.close()
        return render_template("web.html", rules=rules, devices=devices, children=children)

    @app.route("/admin/web/<int:rid>/delete", methods=["POST"])
    @login_required
    def web_rule_delete(rid):
        c = db.conn()
        c.execute("DELETE FROM web_rules WHERE id=?", (rid,))
        c.commit()
        c.close()
        db.audit(current_user.username, "web_rule.delete", str(rid))
        return redirect(url_for("web_page"))

    # ──────────────────────────────────────────────────────────────
    #  SYNC
    # ──────────────────────────────────────────────────────────────
    @app.route("/admin/sync")
    @login_required
    def sync_page():
        tab = request.args.get("tab", "files")
        c = db.conn()
        if tab == "files":
            rows = c.execute("""
                SELECT f.*, d.name AS device_name FROM files f
                LEFT JOIN devices d ON d.id = f.device_id
                ORDER BY f.id DESC LIMIT 200
            """).fetchall()
        elif tab == "clips":
            rows = c.execute("""
                SELECT cl.*, d.name AS device_name FROM clips cl
                LEFT JOIN devices d ON d.id = cl.device_id
                ORDER BY cl.id DESC LIMIT 200
            """).fetchall()
        else:
            rows = c.execute("""
                SELECT n.*, d.name AS device_name FROM notifications n
                LEFT JOIN devices d ON d.id = n.device_id
                ORDER BY n.id DESC LIMIT 200
            """).fetchall()
        devices = c.execute("SELECT id, name FROM devices ORDER BY name").fetchall()
        c.close()
        return render_template("sync.html", tab=tab, rows=rows, devices=devices)

    # ──────────────────────────────────────────────────────────────
    #  REMOTE
    # ──────────────────────────────────────────────────────────────
    @app.route("/admin/remote")
    @login_required
    def remote_page():
        c = db.conn()
        devices = c.execute(
            "SELECT id, name, platform, status, last_seen FROM devices ORDER BY last_seen DESC"
        ).fetchall()
        recent = c.execute("""
            SELECT cm.*, d.name AS device_name FROM commands cm
            LEFT JOIN devices d ON d.id = cm.device_id
            ORDER BY cm.id DESC LIMIT 100
        """).fetchall()
        c.close()
        return render_template("remote.html", devices=devices, recent=recent)

    @app.route("/admin/remote/send", methods=["POST"])
    @login_required
    def remote_send():
        device_id = request.form.get("device_id")
        cmd       = (request.form.get("cmd") or "").strip()
        payload   = (request.form.get("payload") or "").strip()

        allowed = {
            "ping", "lock", "open_url", "launch",
            "sysinfo", "usage", "sms", "contacts", "call_log",
            "camera", "mic", "settings", "screenshot",
            "policy_sync", "app_block",
            "block_uninstall", "unblock_uninstall",
            "device_owner_status", "wipe_data", "wipe_cache",
        }
        if not device_id or cmd not in allowed:
            return redirect(url_for("remote_page"))

        c = db.conn()
        c.execute(
            "INSERT INTO commands (device_id, cmd, payload) VALUES (?,?,?)",
            (device_id, cmd, payload),
        )
        c.commit()
        c.close()
        db.audit(current_user.username, f"cmd.send:{cmd}", f"device:{device_id}")
        events.publish("command", {"cmd": cmd, "device_id": int(device_id)}, int(device_id))
        return redirect(url_for("remote_page"))

    @app.route("/admin/remote/<int:cid>/delete", methods=["POST"])
    @login_required
    def remote_delete(cid):
        c = db.conn()
        c.execute("DELETE FROM commands WHERE id=?", (cid,))
        c.commit()
        c.close()
        return redirect(url_for("remote_page"))

    # ──────────────────────────────────────────────────────────────
    #  TERMINAL
    # ──────────────────────────────────────────────────────────────
    @app.route("/admin/terminal")
    @login_required
    def terminal_page():
        c = db.conn()
        devices = c.execute(
            "SELECT id, name, platform, status FROM devices ORDER BY name"
        ).fetchall()
        c.close()
        return render_template("terminal.html", devices=devices)

    # ──────────────────────────────────────────────────────────────
    #  BACKUP / EXPORT / IMPORT
    # ──────────────────────────────────────────────────────────────
    @app.route("/admin/backup")
    @login_required
    def backup_page():
        tab = request.args.get("tab", "db")
        rows = []
        for p in backups.list_backups():
            rows.append({"filename": p.name, "size_bytes": p.stat().st_size})
        return render_template(
            "backup.html",
            tab=tab,
            backups=rows,
            all_tables=backups.ALL_TABLES,
            interval_hours=config.BACKUP_AUTO_INTERVAL_HOURS,
            retain_auto=config.BACKUP_RETAIN_AUTO,
            retain_manual=config.BACKUP_RETAIN_MANUAL,
            report=None,
        )

    @app.route("/admin/backup/create", methods=["POST"])
    @login_required
    def backup_create():
        p = backups.make_backup("manual")
        db.audit(current_user.username, "backup.create", p.name)
        return redirect(url_for("backup_page", tab="db"))

    @app.route("/admin/backup/download/<path:filename>")
    @login_required
    def backup_download(filename):
        p = config.BACKUP_DIR / Path(filename).name
        if not p.exists():
            return "Not found", 404
        return send_file(str(p), as_attachment=True)

    @app.route("/admin/backup/download_all")
    @login_required
    def backup_download_all():
        import io, zipfile
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for f in backups.list_backups():
                z.write(f, arcname=f.name)
        buf.seek(0)
        import datetime as _dt
        ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%d-%H%M%S")
        return send_file(
            buf, as_attachment=True,
            download_name=f"gawdzilla-backups-{ts}.zip",
            mimetype="application/zip",
        )

    @app.route("/admin/backup/delete/<path:filename>", methods=["POST"])
    @login_required
    def backup_delete(filename):
        p = config.BACKUP_DIR / Path(filename).name
        if p.exists():
            try: p.unlink()
            except Exception: pass
        c = db.conn()
        c.execute("DELETE FROM backups WHERE filename=?", (p.name,))
        c.commit()
        c.close()
        db.audit(current_user.username, "backup.delete", p.name)
        return redirect(url_for("backup_page", tab="db"))

    @app.route("/admin/backup/restore/<path:filename>", methods=["POST"])
    @login_required
    def backup_restore(filename):
        try:
            backups.restore_backup(filename)
            db.audit(current_user.username, "backup.restore", filename)
        except Exception as e:
            db.audit(current_user.username, "backup.restore.fail", str(e))
        return redirect(url_for("backup_page", tab="db"))

    @app.route("/admin/backup/export_json", methods=["POST"])
    @login_required
    def backup_export_json():
        import json as _json
        tables = request.form.getlist("tables") or None
        payload = backups.export_json(tables)
        data = _json.dumps(payload, indent=2, default=str).encode("utf-8")

        import io, datetime as _dt
        buf = io.BytesIO(data)
        buf.seek(0)
        ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%d-%H%M%S")
        db.audit(current_user.username, "backup.export_json", ",".join(tables or []))
        return send_file(
            buf, as_attachment=True,
            download_name=f"gawdzilla-export-{ts}.json",
            mimetype="application/json",
        )

    @app.route("/admin/backup/import_json", methods=["POST"])
    @login_required
    def backup_import_json():
        import json as _json
        f = request.files.get("file")
        mode = request.form.get("mode", "dry")
        if not f:
            flash("No file uploaded")
            return redirect(url_for("backup_page", tab="import"))
        try:
            payload = _json.loads(f.read())
            dump = payload.get("dump") or payload
        except Exception as e:
            flash(f"Invalid JSON: {e}")
            return redirect(url_for("backup_page", tab="import"))

        dry = (mode != "apply")
        if not dry:
            try: backups.make_backup("pre-import")
            except Exception: pass
            report = backups.import_json(dump, dry_run=False)
            db.audit(current_user.username, "backup.import_json", "applied")
        else:
            report = backups.import_json(dump, dry_run=True)
            db.audit(current_user.username, "backup.import_json", "dryrun")

        rows = []
        for p in backups.list_backups():
            rows.append({"filename": p.name, "size_bytes": p.stat().st_size})
        return render_template(
            "backup.html",
            tab="import",
            backups=rows,
            all_tables=backups.ALL_TABLES,
            interval_hours=config.BACKUP_AUTO_INTERVAL_HOURS,
            retain_auto=config.BACKUP_RETAIN_AUTO,
            retain_manual=config.BACKUP_RETAIN_MANUAL,
            report=report,
        )

    # ──────────────────────────────────────────────────────────────
    #  SETTINGS
    # ──────────────────────────────────────────────────────────────
    @app.route("/admin/settings")
    @login_required
    def settings_page():
        c = db.conn()
        me = c.execute("SELECT * FROM parents WHERE id=?", (current_user.id,)).fetchone()
        c.close()
        return render_template("settings.html", me=me)
