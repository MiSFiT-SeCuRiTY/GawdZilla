"""
GawdZilla — Supplementary routes
Provisioning, 2FA helpers, backup export/import, device detail.
Created by MiSFiT SeCuRiTY
"""

import io
import json
import zipfile
import datetime
from pathlib import Path

from flask import (
    render_template, request, redirect, url_for, jsonify,
    send_file, flash, abort,
)
from flask_login import login_required, current_user

from core import db, config, backups, auth


def register(app):

    # ──────────────────────────────────────────────────────────
    #  2FA endpoints referenced by templates
    # ──────────────────────────────────────────────────────────
    @app.route("/admin/setup_2fa")
    @login_required
    def setup_2fa():
        return redirect(url_for("totp_setup"))

    @app.route("/admin/enable_2fa")
    @login_required
    def enable_2fa():
        return redirect(url_for("totp_setup"))

    @app.route("/admin/disable_2fa")
    @login_required
    def disable_2fa():
        return redirect(url_for("totp_setup"))

    # ──────────────────────────────────────────────────────────
    #  Change password alias (templates use this name)
    # ──────────────────────────────────────────────────────────
    @app.route("/admin/change_password")
    @login_required
    def change_password():
        return redirect(url_for("password_change"))

    # ──────────────────────────────────────────────────────────
    #  Device detail page
    # ──────────────────────────────────────────────────────────
    @app.route("/admin/devices/<int:did>")
    @login_required
    def device_detail_page(did):
        c = db.conn()
        device = c.execute(
            """SELECT d.*, ch.name AS child_name FROM devices d
               LEFT JOIN children ch ON ch.id = d.child_id
               WHERE d.id=?""", (did,)
        ).fetchone()
        if not device:
            c.close()
            abort(404)

        recent_events = c.execute(
            "SELECT kind, payload, ts FROM events WHERE device_id=? ORDER BY id DESC LIMIT 50",
            (did,)
        ).fetchall()
        recent_commands = c.execute(
            "SELECT id, cmd, status, result, created_at FROM commands WHERE device_id=? ORDER BY id DESC LIMIT 30",
            (did,)
        ).fetchall()
        loc = c.execute(
            "SELECT lat, lon, accuracy_m, ts FROM locations WHERE device_id=? ORDER BY id DESC LIMIT 1",
            (did,)
        ).fetchone()
        c.close()

        return render_template(
            "device_detail.html",
            device=device,
            events=recent_events,
            commands=recent_commands,
            location=loc,
        )

    # ──────────────────────────────────────────────────────────
    #  Provisioning page
    # ──────────────────────────────────────────────────────────
    @app.route("/admin/provision")
    @login_required
    def provision_page():
        c = db.conn()
        tokens = c.execute(
            "SELECT * FROM enroll_tokens WHERE used=0 ORDER BY id DESC LIMIT 20"
        ).fetchall()
        c.close()
        return render_template("provision.html", tokens=tokens)

    # ──────────────────────────────────────────────────────────
    #  Backup helpers referenced by templates

    @app.route("/admin/backup/export")
    @login_required
    def backup_export():
        """Export the DB as a JSON dump inside a ZIP."""
        c = db.conn()
        dump = {}
        for table in ("parents", "children", "devices", "policies",
                      "builds", "enroll_tokens", "commands",
                      "audit_log", "events", "locations",
                      "geofences", "geofence_events",
                      "app_rules", "web_rules",
                      "files", "clips", "notifications",
                      "backups", "alerts", "metrics"):
            try:
                rows = c.execute(f"SELECT * FROM {table}").fetchall()
                dump[table] = [dict(r) for r in rows]
            except Exception:
                dump[table] = []
        c.close()

        # remove secrets
        for p in dump.get("parents", []):
            p.pop("pw_hash", None)
            p.pop("totp_secret", None)

        meta = {
            "product": config.APP_NAME,
            "version": config.APP_VERSION,
            "exported_at": auth.iso(),
            "author": config.APP_AUTHOR,
        }

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("meta.json", json.dumps(meta, indent=2))
            z.writestr("dump.json", json.dumps(dump, indent=2, default=str))
        buf.seek(0)

        ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
        return send_file(
            buf,
            as_attachment=True,
            download_name=f"gawdzilla-export-{ts}.zip",
            mimetype="application/zip",
        )

    @app.route("/admin/backup/import", methods=["POST"])
    @login_required
    def backup_import():
        f = request.files.get("file")
        if not f:
            flash("No file uploaded")
            return redirect(url_for("backup_page"))

        try:
            data = f.read()
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                names = z.namelist()
                if "dump.json" not in names:
                    flash("Invalid export: dump.json missing")
                    return redirect(url_for("backup_page"))
                dump = json.loads(z.read("dump.json"))
        except Exception as e:
            flash(f"Import failed: {e}")
            return redirect(url_for("backup_page"))

        # Snapshot the current DB before we change anything
        try:
            backups.make_backup("pre-import")
        except Exception:
            pass

        c = db.conn()
        imported = {}
        for table, rows in dump.items():
            if table == "parents":
                continue  # never overwrite parents on import
            try:
                c.execute(f"DELETE FROM {table}")
                for r in rows:
                    cols = list(r.keys())
                    ph = ",".join(["?"] * len(cols))
                    c.execute(
                        f"INSERT INTO {table} ({','.join(cols)}) VALUES ({ph})",
                        tuple(r[k] for k in cols),
                    )
                imported[table] = len(rows)
            except Exception as e:
                imported[table] = f"error: {e}"
        c.commit()
        c.close()

        db.audit(current_user.username, "backup.import", "ok")
        flash("Imported: " + ", ".join(f"{k}={v}" for k, v in imported.items()))
        return redirect(url_for("backup_page"))
