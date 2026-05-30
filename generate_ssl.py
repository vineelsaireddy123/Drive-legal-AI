"""
Generate self-signed SSL certificate for drivelegal.ai
and install it to Windows Trusted Root Certificate store.
"""
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import datetime, os, ipaddress

CERT_DIR = os.path.dirname(os.path.abspath(__file__))
KEY_FILE = os.path.join(CERT_DIR, "ssl", "drivelegal.key")
CERT_FILE = os.path.join(CERT_DIR, "ssl", "drivelegal.crt")

os.makedirs(os.path.join(CERT_DIR, "ssl"), exist_ok=True)

# Generate RSA private key
key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

# Build certificate
subject = issuer = x509.Name([
    x509.NameAttribute(NameOID.COUNTRY_NAME, "IN"),
    x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "India"),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME, "DriveLegal.ai"),
    x509.NameAttribute(NameOID.COMMON_NAME, "drivelegal.ai"),
])

cert = (
    x509.CertificateBuilder()
    .subject_name(subject)
    .issuer_name(issuer)
    .public_key(key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
    .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365))
    .add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName("drivelegal.ai"),
            x509.DNSName("localhost"),
            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
        ]),
        critical=False,
    )
    .add_extension(
        x509.BasicConstraints(ca=True, path_length=None),
        critical=True,
    )
    .add_extension(
        x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
        critical=False,
    )
    .sign(key, hashes.SHA256())
)

# Write private key
with open(KEY_FILE, "wb") as f:
    f.write(key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ))

# Write certificate
with open(CERT_FILE, "wb") as f:
    f.write(cert.public_bytes(serialization.Encoding.PEM))

print(f"[OK] Private key: {KEY_FILE}")
print(f"[OK] Certificate: {CERT_FILE}")
print(f"[OK] Valid for: drivelegal.ai, localhost, 127.0.0.1")
print(f"[OK] Expires: {cert.not_valid_after_utc.strftime('%Y-%m-%d')}")
