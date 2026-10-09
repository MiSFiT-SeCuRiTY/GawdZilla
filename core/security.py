"""
GawdZilla — Security helpers
CSRF tokens, rate limiting, password policy, HTTPS cert generation.
Created by MiSFiT SeCuRiTY
"""

import os
import time
import hmac
import base64
import hashlib
import secrets
import datetime
from pathlib import Path
from collections import defaultdict

from core import config


# ──────────────────────────────────────────────────────────────
#  CSRF
# ──────────────────────────────────────────────────────────────
def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def csrf_sign(session_id: str, token: str) -> str:
    key = (config.SECRET_KEY or "gz").encode()
    msg = f"{session_id}:{token}".encode()
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def csrf_verify(session_id: str, token: str, signature: str) -> bool:
    if not token or not signature:
        return False
    expected = csrf_sign(session_id, token)
    return hmac.compare_digest(expected, signature)


# ──────────────────────────────────────────────────────────────
#  Rate limiter (in-memory, per key)
# ──────────────────────────────────────────────────────────────
class RateLimiter:
    def __init__(self, max_attempts: int = 5, window_seconds: int = 300):
        self.max = max_attempts
        self.window = window_seconds
        self._hits = defaultdict(list)

    def hit(self, key: str) -> bool:
        """Return True if allowed, False if rate-limited."""
        now = time.time()
        self._hits[key] = [t for t in self._hits[key] if now - t < self.window]
        if len(self._hits[key]) >= self.max:
            return False
        self._hits[key].append(now)
        return True

    def remaining(self, key: str) -> int:
        now = time.time()
        self._hits[key] = [t for t in self._hits[key] if now - t < self.window]
        return max(0, self.max - len(self._hits[key]))


login_limiter = RateLimiter(max_attempts=5, window_seconds=300)
enroll_limiter = RateLimiter(max_attempts=20, window_seconds=60)


# ──────────────────────────────────────────────────────────────
#  Password policy
# ──────────────────────────────────────────────────────────────
def password_strength(pw: str) -> tuple:
    """Returns (ok: bool, reason: str)."""
    if not pw or len(pw) < 8:
        return False, "Password must be at least 8 characters."
    if pw.lower() in {"admin", "password", "changeme", "12345678", "qwertyui"}:
        return False, "Too common. Pick something else."
    has_upper = any(c.isupper() for c in pw)
    has_lower = any(c.islower() for c in pw)
    has_digit = any(c.isdigit() for c in pw)
    score = sum([has_upper, has_lower, has_digit])
    if score < 2:
        return False, "Use upper, lower, and digits."
    return True, "OK"


# ──────────────────────────────────────────────────────────────
#  Self-signed HTTPS certificate
# ──────────────────────────────────────────────────────────────
def ensure_self_signed_cert(host: str = "gawdzilla.local") -> tuple:
    """Generate a self-signed cert if missing. Returns (cert_path, key_path)."""
    cert_dir = config.DATA_DIR / "certs"
    cert_dir.mkdir(parents=True, exist_ok=True)
    cert_path = cert_dir / "server.crt"
    key_path  = cert_dir / "server.key"

    if cert_path.exists() and key_path.exists():
        return cert_path, key_path

    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        import ipaddress

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "IN"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "MiSFiT SeCuRiTY"),
            x509.NameAttribute(NameOID.COMMON_NAME, host),
        ])

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1))
            .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=3650))
            .add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName(host),
                    x509.DNSName("localhost"),
                    x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                    x509.IPAddress(ipaddress.IPv4Address("0.0.0.0")),
                ]),
                critical=False,
            )
            .sign(key, hashes.SHA256())
        )

        with open(key_path, "wb") as f:
            f.write(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            ))

        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        return cert_path, key_path
    except Exception as e:
        return None, str(e)
