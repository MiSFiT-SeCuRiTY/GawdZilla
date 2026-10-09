"""
GawdZilla — Flask application factory
Created by MiSFiT SeCuRiTY
"""

import sys
import time
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flask import (
    Flask, redirect, url_for, render_template, request,
    jsonify, session,
)
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user,
)
from flask_wtf.csrf import CSRFProtect, generate_csrf

from core import config, db, auth


# ──────────────────────────────────────────────────────────────
#  Rate limiter
# ──────────────────────────────────────────────────────────────
_RATE = {}


def rate_ok(key, max_events, window_seconds):
    now = time.time()
    bucket = _RATE.setdefault(key, [])
    bucket[:] = [t for t in bucket if now - t < window_seconds]
    if len(bucket) >= max_events:
        return False
    bucket.append(now)
    return True


# ──────────────────────────────────────────────────────────────
#  User
# ──────────────────────────────────────────────────────────────
class Parent(UserMixin):
    def __init__(self, row):
        self.id       = row["id"]
        self.username = row["username"]
        self.role     = row["role"]


login_manager = LoginManager()
csrf = CSRFProtect()


# Endpoints that MUST bypass CSRF (device-side, token auth, not session)
DEVICE_ENDPOINTS = [
    "device_enroll",
    "device_heartbeat",
    "device_command",
    "device_command_result",
    "device_location",
    "device_usage",
    "device_notify",
    "device_clip",
    "device_media",
    "device_sms",
    "device_contacts",
    "device_calllog",
    "api_device_command",
]


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(ROOT / "templates"),
        static_folder=str(ROOT / "static"),
    )
    app.secret_key = config.SECRET_KEY

    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"]   = False
    app.config["PERMANENT_SESSION_LIFETIME"] = datetime.timedelta(days=7)
    app.config["WTF_CSRF_TIME_LIMIT"] = None

    login_manager.init_app(app)
    login_manager.login_view = "login"
    login_manager.login_message = None

    csrf.init_app(app)

    @app.context_processor
    def inject_csrf():
        return {"csrf_token": generate_csrf}

    @app.after_request
    def harden_headers(resp):
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "same-origin"
        resp.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return resp

    @login_manager.user_loader
    def load_user(uid):
        c = db.conn()
        row = c.execute("SELECT * FROM parents WHERE id=?", (uid,)).fetchone()
        c.close()
        return Parent(row) if row else None

    # ────────────────────────────────────────────────────
    #  Auth
    # ────────────────────────────────────────────────────
    @app.route("/admin/login", methods=["GET", "POST"])
    def login():
        err = None
        if request.method == "POST":
            ip = request.remote_addr or "?"
            if not rate_ok(f"login:{ip}", 10, 300):
                return render_template("login.html",
                                       err="Too many attempts. Try again later."), 429

            u = (request.form.get("username") or "").strip()
            p = request.form.get("password") or ""
            code = (request.form.get("totp") or "").strip()

            c = db.conn()
            row = c.execute("SELECT * FROM parents WHERE username=?", (u,)).fetchone()
            c.close()

            if row and auth.verify_password(p, row["pw_hash"]) \
                    and auth.verify_totp(row["totp_secret"], code):
                login_user(Parent(row))
                session.permanent = True
                c = db.conn()
                c.execute("UPDATE parents SET last_login=? WHERE id=?", (auth.iso(), row["id"]))
                c.commit()
                c.close()
                db.audit(u, "login", "admin")
                if u == "admin" and p == "admin":
                    return redirect(url_for("password_change", forced=1))
                return redirect(url_for("admin_dashboard"))
            err = "Invalid credentials"

        return render_template("login.html", err=err)

    @app.route("/admin/logout")
    @login_required
    def logout():
        db.audit(current_user.username, "logout", "admin")
        logout_user()
        return redirect(url_for("login"))

    @app.route("/admin/password", methods=["GET", "POST"])
    @login_required
    def password_change():
        err = None
        forced = bool(request.args.get("forced"))
        if request.method == "POST":
            old = request.form.get("old") or ""
            new = request.form.get("new") or ""
            confirm = request.form.get("confirm") or ""

            c = db.conn()
            row = c.execute("SELECT * FROM parents WHERE id=?", (current_user.id,)).fetchone()
            c.close()

            if not auth.verify_password(old, row["pw_hash"]):
                err = "Current password incorrect."
            elif len(new) < 8:
                err = "New password must be at least 8 characters."
            elif new != confirm:
                err = "Passwords don't match."
            elif new == "admin":
                err = "Pick something other than 'admin'."
            else:
                c = db.conn()
                c.execute("UPDATE parents SET pw_hash=? WHERE id=?",
                          (auth.hash_password(new), current_user.id))
                c.commit()
                c.close()
                db.audit(current_user.username, "password.change", "admin")
                return redirect(url_for("admin_dashboard"))

        return render_template("password.html", err=err, forced=forced)

    @app.route("/admin/2fa", methods=["GET", "POST"])
    @login_required
    def totp_setup():
        import pyotp, qrcode, io, base64
        c = db.conn()
        row = c.execute("SELECT * FROM parents WHERE id=?", (current_user.id,)).fetchone()
        c.close()

        err = None
        secret = row["totp_secret"]

        if request.method == "POST":
            action = request.form.get("action")
            if action == "enable":
                candidate = request.form.get("secret") or ""
                code = request.form.get("code") or ""
                if pyotp.TOTP(candidate).verify(code.strip(), valid_window=1):
                    c = db.conn()
                    c.execute("UPDATE parents SET totp_secret=? WHERE id=?",
                              (candidate, current_user.id))
                    c.commit()
                    c.close()
                    db.audit(current_user.username, "2fa.enable", "admin")
                    return redirect(url_for("totp_setup"))
                err = "Code didn't match. Try again."
            elif action == "disable":
                c = db.conn()
                c.execute("UPDATE parents SET totp_secret=NULL WHERE id=?", (current_user.id,))
                c.commit()
                c.close()
                db.audit(current_user.username, "2fa.disable", "admin")
                return redirect(url_for("totp_setup"))

        if not secret:
            secret = auth.new_totp_secret()

        uri = pyotp.TOTP(secret).provisioning_uri(
            name=current_user.username, issuer_name="GawdZilla")
        qr = qrcode.make(uri)
        buf = io.BytesIO()
        qr.save(buf, format="PNG")
        qr_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

        return render_template("totp.html",
                               secret=secret, qr_b64=qr_b64,
                               enabled=bool(row["totp_secret"]), err=err)

    # ────────────────────────────────────────────────────
    #  Root
    # ────────────────────────────────────────────────────
    @app.route("/")
    def index():
        return redirect(url_for("admin_dashboard"))

    @app.route("/admin")
    @login_required
    def admin_dashboard():
        c = db.conn()
        device_count  = c.execute("SELECT COUNT(*) AS n FROM devices").fetchone()["n"]
        online_count  = c.execute("SELECT COUNT(*) AS n FROM devices WHERE status='online'").fetchone()["n"]
        child_count   = c.execute("SELECT COUNT(*) AS n FROM children").fetchone()["n"]
        policy_count  = c.execute("SELECT COUNT(*) AS n FROM policies WHERE enabled=1").fetchone()["n"]
        recent_devices = c.execute("SELECT * FROM devices ORDER BY last_seen DESC LIMIT 10").fetchall()
        c.close()
        return render_template(
            "dashboard.html",
            device_count=device_count,
            online_count=online_count,
            child_count=child_count,
            policy_count=policy_count,
            recent_devices=recent_devices,
            now=datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%S"),
        )

    @app.route("/healthz")
    def healthz():
        return jsonify(ok=True, app=config.APP_NAME, version=config.APP_VERSION)

    # ────────────────────────────────────────────────────
    #  Register blueprints
    # ────────────────────────────────────────────────────
    for modname in ("routes_admin_pages", "routes_device", "routes_device_extras",
                    "routes_builder", "routes_api", "routes_ws",
                    "routes_stubs"):
        try:
            mod = __import__(f"server.{modname}", fromlist=["register"])
            if hasattr(mod, "register"):
                mod.register(app)
                print(f"[GawdZilla] loaded {modname}", flush=True)
        except Exception as e:
            print(f"[GawdZilla] skipped {modname}: {e}", flush=True)

    # ────────────────────────────────────────────────────
    #  CSRF exempts AFTER all routes exist
    # ────────────────────────────────────────────────────
    for ep in DEVICE_ENDPOINTS:
        view = app.view_functions.get(ep)
        if view is None:
            print(f"[GawdZilla] csrf: no such endpoint {ep}", flush=True)
            continue
        try:
            csrf.exempt(view)
        except Exception as e:
            print(f"[GawdZilla] csrf exempt failed for {ep}: {e}", flush=True)

    print(f"[GawdZilla] CSRF exemptions applied: {len(csrf._exempt_views)}", flush=True)

    return app


def bootstrap():
    db.init()
    from core import backups as _bk, events as _ev
    _bk.start_scheduler()
    _ev.start_sweeper()
    c = db.conn()
    n = c.execute("SELECT COUNT(*) AS n FROM parents").fetchone()["n"]
    if n == 0:
        c.execute("INSERT INTO parents (username, pw_hash, role) VALUES (?,?,?)",
                  (config.DEFAULT_ADMIN_USER,
                   auth.hash_password(config.DEFAULT_ADMIN_PASS),
                   "admin"))
        c.commit()
        print(f"\n[GawdZilla] Default admin created: "
              f"{config.DEFAULT_ADMIN_USER} / {config.DEFAULT_ADMIN_PASS}\n", flush=True)
    c.close()


def run():
    bootstrap()
    app = create_app()
    print(f"[GawdZilla] Serving on http://{config.HOST}:{config.PORT}", flush=True)
    app.run(host=config.HOST, port=config.PORT,
            debug=False, threaded=True, use_reloader=False)


if __name__ == "__main__":
    run()
