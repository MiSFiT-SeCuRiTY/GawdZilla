"""
GawdZilla — Device endpoints (enrollment, heartbeat, commands, location, usage, notify, clip, policy)
Created by MiSFiT SeCuRiTY
"""

import datetime
from flask import request, jsonify, render_template

from core import db, auth, events


def _log(tag, data):
    try:
        print(f"[gz:{tag}] {data}", flush=True)
    except Exception:
        pass


def _haversine_m(lat1, lon1, lat2, lon2):
    import math
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))


def register(app):

    # ─────────────────────────────────────────────────────────
    #  Public
    # ─────────────────────────────────────────────────────────
    @app.route("/device", methods=["GET"])
    def device_landing():
        return render_template("enroll.html", token=request.args.get("token", ""))

    @app.route("/enroll", methods=["GET"])
    def enroll_page():
        return render_template("enroll.html", token=request.args.get("token", ""))

    # ─────────────────────────────────────────────────────────
    #  Enroll
    # ─────────────────────────────────────────────────────────
    @app.route("/device/enroll", methods=["POST"])
    def device_enroll():
        data = request.get_json(silent=True) or {}
        _log("enroll", {"ctype": request.content_type, "body": data, "args": dict(request.args)})

        token = data.get("token") or request.args.get("token")
        if not token:
            return jsonify(ok=False, error="missing token"), 400

        c = db.conn()
        row = c.execute("SELECT * FROM enroll_tokens WHERE token=?", (token,)).fetchone()
        if not row:
            c.close()
            return jsonify(ok=False, error="unknown token"), 403

        if row["used"]:
            c.close()
            return jsonify(ok=False, error="token already used"), 403

        if row["expires_at"]:
            try:
                exp = datetime.datetime.fromisoformat(row["expires_at"])
                if exp < datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None):
                    c.close()
                    return jsonify(ok=False, error="token expired"), 403
            except Exception:
                pass

        existing = c.execute("SELECT id FROM devices WHERE enroll_token=?", (token,)).fetchone()

        if existing:
            c.execute(
                """UPDATE devices SET child_id=?, name=?, platform=?, os_version=?, arch=?,
                   agent_version=?, hw_id=?, last_seen=?, status='online' WHERE id=?""",
                (row["child_id"],
                 data.get("name") or "Android Device",
                 data.get("platform") or "android",
                 data.get("os_version") or "unknown",
                 data.get("arch") or "unknown",
                 data.get("agent_version") or "1.0.0",
                 data.get("hw_id") or "",
                 auth.iso(), existing["id"])
            )
            device_id = existing["id"]
        else:
            cur = c.execute(
                """INSERT INTO devices
                   (child_id, name, platform, os_version, arch, agent_version,
                    enroll_token, hw_id, last_seen, status)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (row["child_id"],
                 data.get("name") or "Android Device",
                 data.get("platform") or "android",
                 data.get("os_version") or "unknown",
                 data.get("arch") or "unknown",
                 data.get("agent_version") or "1.0.0",
                 token,
                 data.get("hw_id") or "",
                 auth.iso(), "online")
            )
            device_id = cur.lastrowid

        c.execute("UPDATE enroll_tokens SET used=1 WHERE id=?", (row["id"],))
        c.commit()
        c.close()

        db.audit("device", "enroll", data.get("name", "unknown"), token[:10])
        events.publish("enroll", {"name": data.get("name"), "platform": data.get("platform")}, device_id)
        _log("enroll-ok", {"device_id": device_id, "name": data.get("name")})
        return jsonify(ok=True, message="enrolled", device_id=device_id)

    # ─────────────────────────────────────────────────────────
    #  Heartbeat
    # ─────────────────────────────────────────────────────────
    @app.route("/device/heartbeat", methods=["POST"])
    def device_heartbeat():
        data = request.get_json(silent=True) or {}
        token = data.get("token")
        if not token:
            _log("heartbeat-400", {"body": data})
            return jsonify(ok=False, error="missing token"), 400

        c = db.conn()
        row = c.execute("SELECT id, name FROM devices WHERE enroll_token=?", (token,)).fetchone()
        if not row:
            c.close()
            _log("heartbeat-403", {"token": token})
            return jsonify(ok=False, error="unknown token"), 403

        c.execute("UPDATE devices SET last_seen=?, status='online' WHERE id=?",
                  (auth.iso(), row["id"]))
        c.commit()
        c.close()

        info = data.get("sysinfo") or {}
        events.publish("heartbeat",
                       {"name": row["name"],
                        "cpu": info.get("cpu_percent"),
                        "ram": info.get("ram_percent"),
                        "disk": info.get("disk_percent"),
                        "battery": info.get("battery_percent")},
                       row["id"])
        events.record_metrics(row["id"], info)

        try:
            bp = info.get("battery_percent")
            if bp is not None and bp < 15:
                events.raise_alert(row["id"], "warn",
                                   f"{row['name']} battery low", f"{int(bp)}%")
        except Exception:
            pass

        return jsonify(ok=True, ts=auth.iso())

    # ─────────────────────────────────────────────────────────
    #  Commands
    # ─────────────────────────────────────────────────────────
    @app.route("/device/command", methods=["GET"])
    def device_command():
        token = request.args.get("token")
        if not token:
            return jsonify(ok=False, error="missing token"), 400

        c = db.conn()
        dev = c.execute("SELECT id FROM devices WHERE enroll_token=?", (token,)).fetchone()
        if not dev:
            c.close()
            _log("command-403", {"token": token})
            return jsonify(ok=False, error="unknown token"), 403

        rows = c.execute(
            "SELECT id, cmd, payload FROM commands WHERE device_id=? AND status='queued' ORDER BY id ASC LIMIT 10",
            (dev["id"],)).fetchall()
        for r in rows:
            c.execute("UPDATE commands SET status='sent', updated_at=? WHERE id=?",
                      (auth.iso(), r["id"]))
        c.commit()
        c.close()
        return jsonify(ok=True, commands=[dict(r) for r in rows])

    @app.route("/device/command/result", methods=["POST"])
    def device_command_result():
        data = request.get_json(silent=True) or {}
        token  = data.get("token")
        cid    = data.get("id")
        ok     = bool(data.get("ok"))
        result = (data.get("result") or "")[:2000]

        if not token or cid is None:
            return jsonify(ok=False, error="missing token or id"), 400

        c = db.conn()
        dev = c.execute("SELECT id FROM devices WHERE enroll_token=?", (token,)).fetchone()
        if not dev:
            c.close()
            return jsonify(ok=False, error="unknown token"), 403

        c.execute("UPDATE commands SET status=?, result=?, updated_at=? WHERE id=? AND device_id=?",
                  ("done" if ok else "failed", result, auth.iso(), cid, dev["id"]))
        c.commit()
        c.close()
        events.publish("command_result", {"id": cid, "ok": ok, "result": result[:120]}, dev["id"])
        return jsonify(ok=True)

    # ─────────────────────────────────────────────────────────
    #  Location
    # ─────────────────────────────────────────────────────────
    @app.route("/device/location", methods=["POST"])
    def device_location():
        data = request.get_json(silent=True) or {}
        token = data.get("token")
        if not token:
            return jsonify(ok=False, error="missing token"), 400

        try:
            lat = float(data.get("lat"))
            lon = float(data.get("lon"))
        except (TypeError, ValueError):
            return jsonify(ok=False, error="missing lat/lon"), 400

        c = db.conn()
        dev = c.execute("SELECT id FROM devices WHERE enroll_token=?", (token,)).fetchone()
        if not dev:
            c.close()
            return jsonify(ok=False, error="unknown token"), 403

        c.execute("INSERT INTO locations (device_id, lat, lon, accuracy_m, speed_mps) VALUES (?,?,?,?,?)",
                  (dev["id"], lat, lon, data.get("accuracy_m"), data.get("speed_mps")))

        triggered = []
        for f in c.execute("SELECT * FROM geofences").fetchall():
            dist = _haversine_m(lat, lon, f["lat"], f["lon"])
            inside = dist <= f["radius_m"]
            last = c.execute(
                "SELECT event FROM geofence_events WHERE geofence_id=? AND device_id=? ORDER BY id DESC LIMIT 1",
                (f["id"], dev["id"])).fetchone()
            prev = last["event"] if last else None
            if inside and prev != "enter":
                c.execute("INSERT INTO geofence_events (geofence_id, device_id, event) VALUES (?,?,?)",
                          (f["id"], dev["id"], "enter"))
                triggered.append({"fence": f["name"], "event": "enter"})
            elif (not inside) and prev == "enter":
                c.execute("INSERT INTO geofence_events (geofence_id, device_id, event) VALUES (?,?,?)",
                          (f["id"], dev["id"], "exit"))
                triggered.append({"fence": f["name"], "event": "exit"})

        c.commit()
        c.close()
        events.publish("location", {"lat": lat, "lon": lon, "accuracy": data.get("accuracy_m")}, dev["id"])
        for t in triggered:
            events.publish("geofence", t, dev["id"])
        return jsonify(ok=True)

    # ─────────────────────────────────────────────────────────
    #  Usage
    # ─────────────────────────────────────────────────────────
    @app.route("/device/usage", methods=["POST"])
    def device_usage():
        data = request.get_json(silent=True) or {}
        token = data.get("token")
        if not token:
            return jsonify(ok=False, error="missing token"), 400

        c = db.conn()
        dev = c.execute("SELECT id FROM devices WHERE enroll_token=?", (token,)).fetchone()
        if not dev:
            c.close()
            return jsonify(ok=False, error="unknown token"), 403

        for a in (data.get("apps") or [])[:200]:
            pkg = a.get("package")
            if not pkg:
                continue
            c.execute("INSERT INTO events (device_id, kind, payload) VALUES (?,?,?)",
                      (dev["id"], "usage", f"{pkg}:{a.get('seconds', 0)}s"))
        c.commit()
        c.close()
        return jsonify(ok=True)

    # ─────────────────────────────────────────────────────────
    #  Notifications + clipboard
    # ─────────────────────────────────────────────────────────
    @app.route("/device/notify", methods=["POST"])
    def device_notify():
        data = request.get_json(silent=True) or {}
        token = data.get("token")
        if not token:
            return jsonify(ok=False, error="missing token"), 400

        c = db.conn()
        dev = c.execute("SELECT id FROM devices WHERE enroll_token=?", (token,)).fetchone()
        if not dev:
            c.close()
            return jsonify(ok=False, error="unknown token"), 403

        c.execute("INSERT INTO notifications (device_id, pkg, title, body) VALUES (?,?,?,?)",
                  (dev["id"], data.get("pkg", ""), data.get("title", ""), data.get("body", "")))
        c.commit()
        c.close()
        events.publish("notify", {"pkg": data.get("pkg"), "title": data.get("title")}, dev["id"])
        return jsonify(ok=True)

    @app.route("/device/clip", methods=["POST"])
    def device_clip():
        data = request.get_json(silent=True) or {}
        token = data.get("token")
        if not token:
            return jsonify(ok=False, error="missing token"), 400

        c = db.conn()
        dev = c.execute("SELECT id FROM devices WHERE enroll_token=?", (token,)).fetchone()
        if not dev:
            c.close()
            return jsonify(ok=False, error="unknown token"), 403

        c.execute("INSERT INTO clips (device_id, direction, content) VALUES (?,?,?)",
                  (dev["id"], data.get("direction", "up"), data.get("content", "")))
        c.commit()
        c.close()
        events.publish("clip", {"content": (data.get("content") or "")[:120]}, dev["id"])
        return jsonify(ok=True)

    # ─────────────────────────────────────────────────────────
    #  Policy pull
    # ─────────────────────────────────────────────────────────
    @app.route("/device/policy", methods=["GET"])
    def device_policy():
        token = request.args.get("token")
        if not token:
            return jsonify(ok=False, error="missing token"), 400

        c = db.conn()
        dev = c.execute("SELECT id, child_id FROM devices WHERE enroll_token=?", (token,)).fetchone()
        if not dev:
            c.close()
            return jsonify(ok=False, error="unknown token"), 403

        policies = c.execute(
            """SELECT * FROM policies WHERE enabled=1 AND (
                 scope='family' OR (scope='device' AND scope_id=?) OR (scope='child' AND scope_id=?)
               )""",
            (dev["id"], dev["child_id"] or 0)).fetchall()

        app_rules = c.execute(
            "SELECT package, action FROM app_rules WHERE device_id=? OR child_id=? OR (device_id IS NULL AND child_id IS NULL)",
            (dev["id"], dev["child_id"] or 0)).fetchall()

        web_rules = c.execute(
            "SELECT domain, action FROM web_rules WHERE device_id=? OR child_id=? OR (device_id IS NULL AND child_id IS NULL)",
            (dev["id"], dev["child_id"] or 0)).fetchall()

        geofences = c.execute("SELECT id, name, lat, lon, radius_m FROM geofences").fetchall()
        c.close()

        import json as _json
        return jsonify(
            ok=True,
            policies=[{**dict(p), "config": _json.loads(p["config_json"] or "{}")} for p in policies],
            app_rules=[dict(r) for r in app_rules],
            web_rules=[dict(r) for r in web_rules],
            geofences=[dict(g) for g in geofences],
            server_ts=auth.iso(),
        )
