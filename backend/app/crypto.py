"""Calendar credentials (secret iCal addresses, iCloud app passwords) encrypted at rest with AES-256-GCM.

The key is 32 random bytes, base64, in the file ENC_KEY_FILE (a Docker secret, /run/secrets/enc_key). It is read on
every call, so tests can change it; it is never logged."""

import base64
import binascii
import os
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from . import config

PREFIX = "v1:"
NONCE_BYTES = 12


class KeyMissing(Exception):
    """No usable key: the backend refuses to start without one."""


class CannotDecrypt(Exception):
    """A stored credential doesn't open with this key (another key, or damaged)."""


def key_file() -> Path:
    return Path(config.env("ENC_KEY_FILE", "/run/secrets/enc_key"))


def load_key() -> bytes:
    path = key_file()
    hint = f"Make one with: head -c 32 /dev/urandom | base64 > {path} (see README_DOCKER.md)"
    try:
        text = path.read_text().strip()
    except OSError:
        raise KeyMissing(f"No encryption key at {path}. {hint}") from None
    try:
        key = base64.b64decode(text, validate=True)
    except (binascii.Error, ValueError):
        raise KeyMissing(f"The encryption key at {path} isn't base64. {hint}") from None
    if len(key) != 32:
        raise KeyMissing(f"The encryption key at {path} must be 32 bytes, not {len(key)}. {hint}")
    return key


def encrypt(plain: str) -> str:
    nonce = os.urandom(NONCE_BYTES)
    sealed = AESGCM(load_key()).encrypt(nonce, plain.encode(), None)
    return PREFIX + base64.b64encode(nonce + sealed).decode()


def decrypt(token: str) -> str:
    if not token.startswith(PREFIX):
        raise CannotDecrypt("unknown format")
    try:
        raw = base64.b64decode(token[len(PREFIX):], validate=True)
        return AESGCM(load_key()).decrypt(raw[:NONCE_BYTES], raw[NONCE_BYTES:], None).decode()
    except (binascii.Error, ValueError, InvalidTag):
        raise CannotDecrypt("doesn't open with this key") from None
