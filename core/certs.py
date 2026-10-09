"""
GawdZilla — Self-signed TLS certificate generator for LAN HTTPS.
Created by MiSFiT SeCuRiTY
"""

import datetime
from pathlib import Path

from core import config


def generate_self_signed(host: str = None, days: int = 825):
    """
    Creates a self-signed cert + key at data/certs/.
    Returns (cert_path, key_path).
    """
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    import ipaddress

    certs_dir = config.CERT_DIR
    certs_dir.mkdir(parents=True, exist_ok=True)

    cert_file = certs_dir / "gawdzilla.crt"
    key_file  = certs_dir / "gawdzilla.key"

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "IN"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "MiSFiT SeCuRiTY"),
        x509.NameAttribute(NameOID.COMMON_NAME, host or "gawdzilla.local"),
    ])

    alt_names = [x509.DNSName("gawdzilla.local"), x509.DNSName("localhost")]
    try:
        alt_names.append(x509.IPAddress(ipaddress.ip_address("127.0.0.1")))
        if host:
            alt_names.append(x509.IPAddress(ipaddress.ip_address(host)))
    except Exception:
        pass

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow() - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=days))
        .add_extension(x509.SubjectAlternativeName(alt_names), critical=False)
        .sign(key, hashes.SHA256())
    )

    key_file.write_bytes(key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ))
    cert_file.write_bytes(cert.public_bytes(serialization.Encoding.PEM))

    return cert_file, key_file


if __name__ == "__main__":
    import sys
    host = sys.argv[1] if len(sys.argv) > 1 else None
    c, k = generate_self_signed(host)
    print(f"cert: {c}")
    print(f"key:  {k}")
