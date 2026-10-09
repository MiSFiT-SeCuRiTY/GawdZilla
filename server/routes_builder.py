"""
GawdZilla — Builder routes (Android only)
Created by MiSFiT SeCuRiTY
"""

import json
from pathlib import Path

from flask import (
    render_template, request, redirect, url_for,
    send_file, jsonify, abort, flash,
)
from flask_login import login_required, current_user

from core import db, config, builder, auth


def register(app):

    @app.route("/admin/builder")
    @login_required
    def builder_page():
        c = db.conn()
        children = c.execute("SELECT * FROM children ORDER BY name").fetchall()
        builds = c.execute(
            "SELECT b.*, ch.name AS child_name FROM builds b "
            "LEFT JOIN children ch ON ch.id = b.child_id "
            "ORDER BY b.created_at DESC LIMIT 100"
        ).fetchall()
        c.close()

        return render_template(
            "builder.html",
            children=children,
            builds=builds,
            os_versions=builder.platform_os_options()["android"],
            archs=builder.platform_arch_options()["android"],
            caps=builder.capability_options(),
            human_size=builder.human_size,
            default_server=request.host_url.rstrip("/"),
        )

    @app.route("/admin/builder/create", methods=["POST"])
    @login_required
    def builder_create():
        os_version = request.form.get("os_version") or "Android 14 (API 34)"
        arch       = request.form.get("arch") or "arm64-v8a"
        child_id   = request.form.get("child_id") or None
        server_url = (request.form.get("server_url") or request.host_url).rstrip("/")
        app_name   = request.form.get("app_name") or "GawdZilla Agent"
        notes      = request.form.get("notes") or ""
        caps       = request.form.getlist("capabilities")

        if not caps:
            flash("Select at least one capability.")
            return redirect(url_for("builder_page"))

        result = builder.build_package(
            platform="android",
            os_version=os_version,
            arch=arch,
            child_id=child_id,
            capabilities=caps,
            server_url=server_url,
            app_name=app_name,
            notes=notes,
        )

        c = db.conn()
        c.execute(
            """INSERT INTO enroll_tokens (token, child_id, platform, expires_at, used)
               VALUES (?,?,?,?,0)""",
            (result["token"], child_id, "android", auth.token_expiry(7)),
        )
        c.execute(
            """INSERT INTO builds
                 (platform, os_version, arch, child_id, capabilities, server_url,
                  enroll_token, filename, sha256, size_bytes)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                "android", os_version, arch, child_id,
                ",".join(caps), server_url, result["token"],
                result["filename"], result["sha256"], result["size_bytes"],
            ),
        )
        c.commit()
        c.close()

        db.audit(current_user.username, "build.create", result["build_id"])
        return redirect(url_for("builder_page", built=result["filename"]))

    @app.route("/admin/builder/download/<path:filename>")
    @login_required
    def builder_download(filename):
        safe = Path(filename).name
        target = config.BUILD_DIR / safe
        if not target.exists() or target.parent != config.BUILD_DIR:
            abort(404)
        db.audit(current_user.username, "build.download", safe)
        return send_file(str(target), as_attachment=True, download_name=safe)

    @app.route("/admin/builder/delete/<int:bid>", methods=["POST"])
    @login_required
    def builder_delete(bid):
        c = db.conn()
        row = c.execute("SELECT filename FROM builds WHERE id=?", (bid,)).fetchone()
        if row and row["filename"]:
            f = config.BUILD_DIR / Path(row["filename"]).name
            if f.exists():
                try: f.unlink()
                except Exception: pass
            sha = f.with_suffix(".zip.sha256")
            if sha.exists():
                try: sha.unlink()
                except Exception: pass
        c.execute("DELETE FROM builds WHERE id=?", (bid,))
        c.commit()
        c.close()
        db.audit(current_user.username, "build.delete", str(bid))
        return redirect(url_for("builder_page"))

    @app.route("/admin/builder/tokens")
    @login_required
    def builder_tokens():
        c = db.conn()
        rows = c.execute(
            "SELECT * FROM enroll_tokens ORDER BY created_at DESC LIMIT 200"
        ).fetchall()
        c.close()
        return render_template("builder_tokens.html", tokens=rows)

    @app.route("/admin/builder/tokens/<int:tid>/revoke", methods=["POST"])
    @login_required
    def builder_token_revoke(tid):
        c = db.conn()
        c.execute("UPDATE enroll_tokens SET used=1 WHERE id=?", (tid,))
        c.commit()
        c.close()
        db.audit(current_user.username, "token.revoke", str(tid))
        return redirect(url_for("builder_tokens"))

    @app.route("/admin/builder/history")
    @login_required
    def builder_history():
        c = db.conn()
        builds = c.execute(
            "SELECT b.*, ch.name AS child_name FROM builds b "
            "LEFT JOIN children ch ON ch.id = b.child_id "
            "ORDER BY b.created_at DESC LIMIT 200"
        ).fetchall()
        c.close()
        return render_template(
            "builder_history.html",
            builds=builds,
            human_size=builder.human_size,
        )

    @app.route("/api/builder/options")
    @login_required
    def api_builder_options():
        return jsonify(
            os_versions=builder.platform_os_options(),
            archs=builder.platform_arch_options(),
            capabilities=[
                {"id": cid, "label": label}
                for cid, label in builder.capability_options()
            ],
        )
