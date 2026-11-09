from __future__ import annotations

import base64
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from lsia.config import settings


class SchoolIdentity:
    def __init__(self, school_id: str, public_key_b64: str, private_key: Ed25519PrivateKey) -> None:
        self.school_id = school_id
        self.public_key_b64 = public_key_b64
        self._private_key = private_key

    def sign(self, message: bytes) -> str:
        return base64.b64encode(self._private_key.sign(message)).decode("ascii")


def verify_signature(public_key_b64: str, signature_b64: str, message: bytes) -> bool:
    try:
        pub_bytes = base64.b64decode(public_key_b64)
        sig_bytes = base64.b64decode(signature_b64)
        public_key = Ed25519PublicKey.from_public_bytes(pub_bytes)
        public_key.verify(sig_bytes, message)
        return True
    except (ValueError, InvalidSignature, Exception):
        return False


def _write_private(path: Path, key: Ed25519PrivateKey) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    try:
        path.chmod(0o600)
    except OSError:
        pass


def load_or_create_identity() -> SchoolIdentity:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    key_path = settings.keys_dir / "school_ed25519.pem"
    if key_path.exists():
        private_key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
        if not isinstance(private_key, Ed25519PrivateKey):
            raise RuntimeError("School key file is not Ed25519")
    else:
        private_key = Ed25519PrivateKey.generate()
        _write_private(key_path, private_key)

    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return SchoolIdentity(
        school_id=settings.school_id,
        public_key_b64=base64.b64encode(public_bytes).decode("ascii"),
        private_key=private_key,
    )
