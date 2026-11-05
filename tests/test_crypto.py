import base64
import os

import pytest

from app import crypto

URL = "https://calendar.google.com/calendar/ical/x/private-abc/basic.ics"


def test_round_trip():
    token = crypto.encrypt(URL)
    assert token.startswith("v1:") and "private-abc" not in token
    assert crypto.decrypt(token) == URL


def test_two_encryptions_differ():
    assert crypto.encrypt("a") != crypto.encrypt("a")


def test_wrong_key_fails(tmp_path, monkeypatch):
    token = crypto.encrypt("a")
    other = tmp_path / "k"
    other.write_text(base64.b64encode(os.urandom(32)).decode())
    monkeypatch.setenv("ENC_KEY_FILE", str(other))
    with pytest.raises(crypto.CannotDecrypt):
        crypto.decrypt(token)


def test_garbage_token_fails():
    with pytest.raises(crypto.CannotDecrypt):
        crypto.decrypt("v1:bm9wZQ==")


@pytest.mark.parametrize("content", [None, "", "dG9vIHNob3J0", "not base64 at all!"])
def test_missing_or_short_key(tmp_path, monkeypatch, content):
    path = tmp_path / "enc_key"
    if content is not None:
        path.write_text(content)
    monkeypatch.setenv("ENC_KEY_FILE", str(path))
    with pytest.raises(crypto.KeyMissing) as error:
        crypto.load_key()
    assert str(path) in str(error.value)


def test_key_file_with_trailing_newline(tmp_path, monkeypatch):
    path = tmp_path / "enc_key"
    path.write_text(base64.b64encode(os.urandom(32)).decode() + "\n")
    monkeypatch.setenv("ENC_KEY_FILE", str(path))
    assert len(crypto.load_key()) == 32
