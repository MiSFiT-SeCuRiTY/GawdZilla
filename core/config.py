"""
GawdZilla — Global configuration
Created by MiSFiT SeCuRiTY
"""

import os
from pathlib import Path

# ──────────────────────────────────────────────────────────────
#  Paths
# ──────────────────────────────────────────────────────────────
ROOT_DIR   = Path(__file__).resolve().parent.parent
DATA_DIR   = ROOT_DIR / "data"
LOG_DIR    = DATA_DIR / "logs"
BUILD_DIR  = DATA_DIR / "builds"
BACKUP_DIR = DATA_DIR / "backups"
UPLOAD_DIR = DATA_DIR / "uploads"
CERT_DIR   = DATA_DIR / "certs"

for _p in (DATA_DIR, LOG_DIR, BUILD_DIR, BACKUP_DIR, UPLOAD_DIR, CERT_DIR):
    _p.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "gawdzilla.db"

# ──────────────────────────────────────────────────────────────
#  Server
# ──────────────────────────────────────────────────────────────
HOST = "0.0.0.0"
PORT = int(os.environ.get("GZ_PORT", "7777"))
DEBUG = os.environ.get("GZ_DEBUG", "0") == "1"
PUBLIC = os.environ.get("GZ_PUBLIC", "0") == "1"

# ──────────────────────────────────────────────────────────────
#  Auth
# ──────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get("GZ_SECRET", "gawdzilla-dev-secret-change-me")
SESSION_LIFETIME_DAYS = 7

DEFAULT_ADMIN_USER = "admin"
DEFAULT_ADMIN_PASS = "admin"

# ──────────────────────────────────────────────────────────────
#  Meta
# ──────────────────────────────────────────────────────────────
APP_NAME    = "GawdZilla"
APP_VERSION = "1.0.0"
APP_AUTHOR  = "MiSFiT SeCuRiTY"

# ──────────────────────────────────────────────────────────────
#  Backup settings
# ──────────────────────────────────────────────────────────────
BACKUP_AUTO_INTERVAL_HOURS = 6      # how often the scheduler fires
BACKUP_RETAIN_AUTO          = 30     # how many auto backups to keep
BACKUP_RETAIN_MANUAL        = 50     # how many manual backups to keep
