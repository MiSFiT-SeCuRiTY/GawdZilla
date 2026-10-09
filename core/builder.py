"""
GawdZilla — Builder
Generates Android enrollment packages.
Created by MiSFiT SeCuRiTY
"""

import json
import uuid
import hashlib
import zipfile
import datetime
from pathlib import Path

from core import config, auth


BUILD_DIR = config.BUILD_DIR
BUILD_DIR.mkdir(parents=True, exist_ok=True)


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ──────────────────────────────────────────────────────────────
#  Options (Android only)
# ──────────────────────────────────────────────────────────────
def platform_os_options():
    return {
        "android": [
            "Android 8.0 (API 26)",
            "Android 9 (API 28)",
            "Android 10 (API 29)",
            "Android 11 (API 30)",
            "Android 12 (API 31)",
            "Android 13 (API 33)",
            "Android 14 (API 34)",
            "Android 15 (API 35)",
        ]
    }


def platform_arch_options():
    return {
        "android": ["arm64-v8a", "armeabi-v7a", "x86_64"]
    }


def capability_options():
    """Every capability the parent can request. Shown to the child on consent."""
    return [
        ("sysinfo",       "Device health (CPU / RAM / storage / battery)"),
        ("screen_time",   "Screen-time limits and schedules"),
        ("app_control",   "App allow / block list (via DevicePolicyManager)"),
        ("web_filter",    "Website filter and SafeSearch"),
        ("location",      "Location and geofences"),
        ("notifications", "Notification mirroring"),
        ("camera",        "Camera capture (permission-gated, on-device indicator)"),
        ("microphone",    "Microphone capture (permission-gated, on-device indicator)"),
        ("sms",           "SMS read / receive"),
        ("contacts",      "Contacts list"),
        ("call_log",      "Call history"),
        ("files",         "File sync (upload / download)"),
        ("clipboard",     "Clipboard sync"),
        ("remote_cmds",   "Remote commands (lock / settings / launch app)"),
        ("device_owner",  "Device Owner mode (uninstall protection)"),
    ]


def generate_enroll_token() -> str:
    return auth.new_enroll_token()


# ──────────────────────────────────────────────────────────────
#  Build
# ──────────────────────────────────────────────────────────────
def build_package(platform: str,
                  os_version: str,
                  arch: str,
                  child_id,
                  capabilities,
                  server_url: str,
                  app_name: str = "GawdZilla Agent",
                  notes: str = "") -> dict:
    build_id = uuid.uuid4().hex[:12]
    token = generate_enroll_token()
    created = auth.iso()

    manifest = {
        "build_id":      build_id,
        "product":       config.APP_NAME,
        "version":       config.APP_VERSION,
        "author":        config.APP_AUTHOR,
        "created_at":    created,
        "platform":      "android",
        "os_version":    os_version,
        "arch":          arch,
        "child_id":      child_id,
        "app_name":      app_name,
        "server_url":    server_url.rstrip("/"),
        "enroll_token":  token,
        "capabilities":  capabilities,
        "notes":         notes,
        "disclosure": (
            "This agent is a parental-control tool. It shows a persistent "
            "notification on Android while active. It logs all actions locally. "
            "It never hides itself."
        ),
    }

    consent_lines = [
        f"{config.APP_NAME} — Capabilities requested for this device",
        "=" * 56,
        "",
        "By installing this agent, the following information will be",
        "shared with the parent who built this package:",
        "",
    ]
    cap_map = dict(capability_options())
    for c in capabilities:
        consent_lines.append(f"  • {cap_map.get(c, c)}")
    consent_lines += [
        "",
        "A persistent notification will always show while the agent runs.",
        "Camera and microphone use will show the OS indicator on this device.",
        "You may ask your parent to disable any capability at any time.",
        "",
        f"Built by: {config.APP_AUTHOR}",
        f"Build ID: {build_id}",
        f"Created:  {created}",
    ]

    readme_lines = [
        f"{config.APP_NAME} Child Agent — Enrollment Package",
        "=" * 56,
        "",
        "Platform:  Android",
        f"OS:        {os_version}",
        f"Arch:      {arch}",
        f"Build ID:  {build_id}",
        "",
        "INSTALL STEPS",
        "-------------",
        "1. Install the GawdZilla Agent APK on the child's Android device.",
        "2. Open the app, enter the server URL and enrollment token below.",
        "3. Tap 'Open consent screen' -> 'I agree'.",
        "4. Grant permissions when prompted.",
        "5. Tap 'Enable device admin' for full policy control.",
        "",
        f"Server URL: {manifest['server_url']}",
        f"Enroll URL: {manifest['server_url']}/device/enroll",
        f"Token:      {token}",
        "",
        f"Created by {config.APP_AUTHOR}",
    ]

    filename = f"gawdzilla-android-{arch}-{build_id}.zip"
    out_path = BUILD_DIR / filename

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(manifest, indent=2))
        z.writestr("consent.txt", "\n".join(consent_lines))
        z.writestr("README.txt", "\n".join(readme_lines))
        z.writestr("server.txt", manifest["server_url"] + "\n")
        z.writestr("enroll_url.txt", f"{manifest['server_url']}/device/enroll\n")
        z.writestr("token.txt", token + "\n")

    sha = sha256_of_file(out_path)
    size = out_path.stat().st_size

    (out_path.with_suffix(".zip.sha256")).write_text(f"{sha}  {filename}\n")

    return {
        "build_id":    build_id,
        "filename":    filename,
        "path":        str(out_path),
        "sha256":      sha,
        "size_bytes":  size,
        "token":       token,
        "created_at":  created,
        "manifest":    manifest,
    }


def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"
