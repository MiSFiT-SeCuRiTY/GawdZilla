"""
GawdZilla — CSRF middleware for Flask
Injects a token into templates, verifies it on all POST requests.
Created by MiSFiT SeCuRiTY
"""

import secrets
from flask import session, request, abort, g

from core import security


PUBLIC_POST_PATHS = {
    "/admin/login",
    "/device/enroll",
    "/device/heartbeat",
    "/device/command/result",
    "/device/location",
    "/device/usage",
    "/device/notify",
    "/device/clip",
    "/device/media",
    "/device/sms",
    "/device/contacts",
    "/device/calllog",
}


def register(app):

    @app.before_request
    def _ensure_csrf():
        if "_csrf" not in session:
            session["_csrf"] = security.new_csrf_token()
        g.csrf_token = session["_csrf"]

        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            # Skip for token-authenticated agent endpoints
            if request.path in PUBLIC_POST_PATHS:
                return
            # Skip for login (fresh session)
            if request.path == "/admin/login":
                return

            token = request.form.get("_csrf") or request.headers.get("X-CSRF-Token")
            sig   = request.form.get("_csrf_sig") or request.headers.get("X-CSRF-Sig")

            sid = request.cookies.get("session", "")
            if not token or not sig or not security.csrf_verify(sid, token, sig):
                abort(400, description="CSRF token missing or invalid")

    @app.context_processor
    def _inject_csrf():
        def csrf_field():
            token = session.get("_csrf", "")
            sid = request.cookies.get("session", "")
            sig = security.csrf_sign(sid, token) if token else ""
            from markupsafe import Markup
            return Markup(
                f'<input type="hidden" name="_csrf" value="{token}">'
                f'<input type="hidden" name="_csrf_sig" value="{sig}">'
            )
        return dict(csrf_field=csrf_field)
