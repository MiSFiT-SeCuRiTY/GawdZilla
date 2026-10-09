"""
GawdZilla — Device Owner provisioning
Created by MiSFiT SeCuRiTY
"""

import json
import base64
import hashlib
import io

from flask import request, jsonify, render_template, send_file

from core import db, config


def register(app):

    @app.route("/admin/provision")
    def provision_page():
        token = request.args.get("token", "")
        server_url = request.host_url.rstrip("/")
        qr_svg = None
        valid = False

        if token:
            c = db.conn()
            row = c.execute(
                "SELECT * FROM enroll_tokens WHERE token=? AND used=0", (token,)
            ).fetchone()
            c.close()
            valid = bool(row)

            if valid:
                payload = _build_payload(server_url, token)
                qr_svg = _svg_qr(json.dumps(payload, separators=(",", ":")))

        return render_template(
            "provision.html",
            token=token,
            server_url=server_url,
            valid=valid,
            qr_svg=qr_svg,
        )

    @app.route("/api/provision/payload")
    def provision_payload():
        token = request.args.get("token", "")
        if not token:
            return jsonify(ok=False, error="missing token"), 400

        c = db.conn()
        row = c.execute(
            "SELECT * FROM enroll_tokens WHERE token=? AND used=0", (token,)
        ).fetchone()
        c.close()

        if not row:
            return jsonify(ok=False, error="invalid token"), 403

        server_url = request.host_url.rstrip("/")
        return jsonify(_build_payload(server_url, token))

    @app.route("/download/agent.apk")
    def download_agent():
        apk = config.DATA_DIR / "agent.apk"
        if not apk.exists():
            return "APK not uploaded. Place it at data/agent.apk", 404
        return send_file(str(apk), as_attachment=True, download_name="GawdZillaAgent.apk")


def _build_payload(server_url: str, token: str) -> dict:
    return {
        "android.app.extra.PROVISIONING_DEVICE_ADMIN_COMPONENT_NAME":
            "com.misfit.gawdzilla/.DeviceAdminReceiver",
        "android.app.extra.PROVISIONING_DEVICE_ADMIN_PACKAGE_DOWNLOAD_LOCATION":
            f"{server_url}/download/agent.apk",
        "android.app.extra.PROVISIONING_DEVICE_ADMIN_PACKAGE_CHECKSUM":
            _agent_checksum(),
        "android.app.extra.PROVISIONING_LEAVE_ALL_SYSTEM_APPS_ENABLED": True,
        "android.app.extra.PROVISIONING_ADMIN_EXTRAS_BUNDLE": {
            "server_url": server_url,
            "enroll_token": token,
        },
    }


def _agent_checksum() -> str:
    apk = config.DATA_DIR / "agent.apk"
    if not apk.exists():
        return ""
    h = hashlib.sha256()
    with open(apk, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return base64.urlsafe_b64encode(h.digest()).decode().rstrip("=")


def _svg_qr(text: str) -> str:
    try:
        import qrcode
        import qrcode.image.svg
        factory = qrcode.image.svg.SvgPathImage
        img = qrcode.make(text, image_factory=factory, box_size=10, border=2)
        buf = io.BytesIO()
        img.save(buf)
        return buf.getvalue().decode("utf-8")
    except Exception as e:
        return f"<pre style='color:red'>QR generation failed: {e}</pre>"
