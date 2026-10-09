"""
GawdZilla — Authentication helpers
Password hashing, TOTP 2FA, token generation, session helpers.
Created by MiSFiT SeCuRiTY
"""

import os
import base64
import secrets
import datetime

import bcrypt
import pyotp


# ──────────────────────────────────────────────────────────────
#  Passwords
# ──────────────────────────────────────────────────────────────
def hash_password(plain: str) -> str:
    """Return a bcrypt hash of the plaintext password."""
    if not isinstance(plain, str) or not plain:
        raise ValueError("password must be a non-empty string")
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Check a plaintext password against a bcrypt hash."""
    if not plain or not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ──────────────────────────────────────────────────────────────
#  TOTP (2FA)
# ──────────────────────────────────────────────────────────────
def new_totp_secret() -> str:
    return pyotp.random_base32()


def totp_uri(secret: str, username: str, issuer: str = "GawdZilla") -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=username, issuer_name=issuer)


def verify_totp(secret: str, code: str) -> bool:
    """Return True if TOTP is disabled (no secret) or the code is valid."""
    if not secret:
        return True
    if not code:
        return False
    try:
        return pyotp.TOTP(secret).verify(code.strip(), valid_window=1)
    except Exception:
        return False


# ──────────────────────────────────────────────────────────────
#  Tokens
# ──────────────────────────────────────────────────────────────
def new_token(nbytes: int = 32) -> str:
    """URL-safe random token for device enrollment / API keys."""
    return secrets.token_urlsafe(nbytes)


def new_enroll_token() -> str:
    """Short human-friendly enrollment token, e.g. GZ-3F9K-2A7B-5C1D."""
    raw = base64.b32encode(secrets.token_bytes(8)).decode("ascii").rstrip("=")
    grouped = "-".join(raw[i:i+4] for i in range(0, 12, 4))
    return f"GZ-{grouped}"


# ──────────────────────────────────────────────────────────────
#  Time helpers
# ──────────────────────────────────────────────────────────────
def utcnow():
    return datetime.datetime.utcnow()


def iso(dt: datetime.datetime = None) -> str:
    return (dt or utcnow()).isoformat(timespec="seconds")


def token_expiry(days: int = 7) -> str:
    return iso(utcnow() + datetime.timedelta(days=days))


# ──────────────────────────────────────────────────────────────
#  CLI test
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("[GawdZilla] auth self-test")
    pw = "admin"
    h = hash_password(pw)
    print(f"  hash_password('{pw}') -> {h[:20]}...")
    print(f"  verify_password ok  -> {verify_password(pw, h)}")
    print(f"  verify_password bad -> {verify_password('wrong', h)}")

    sec = new_totp_secret()
    print(f"  new_totp_secret     -> {sec}")
    code = pyotp.TOTP(sec).now()
    print(f"  current TOTP code   -> {code}")
    print(f"  verify_totp ok      -> {verify_totp(sec, code)}")
    print(f"  verify_totp bad     -> {verify_totp(sec, '000000')}")
    print(f"  verify_totp no secret (should be True) -> {verify_totp('', '')}")

    print(f"  new_token()         -> {new_token()[:20]}...")
    print(f"  new_enroll_token()  -> {new_enroll_token()}")
    print(f"  token_expiry(7d)    -> {token_expiry(7)}")
