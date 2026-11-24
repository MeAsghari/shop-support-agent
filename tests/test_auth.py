import time

import jwt
import pytest

from third_agent.auth import (
    ALGORITHM,
    create_token,
    hash_password,
    read_token,
    verify_password,
)

# Long fake secrets, only for tests (never our real .env value)
TEST_SECRET = "unit-test-secret-" + "x" * 32
OTHER_SECRET = "another-secret-" + "y" * 32


@pytest.fixture(autouse=True)
def jwt_secret(monkeypatch):
    # Runs before every test in this file: set a fixed secret,
    # so the tests never depend on the real .env file
    monkeypatch.setenv("JWT_SECRET", TEST_SECRET)


def make_token(secret, seconds_valid=3600, algorithm=ALGORITHM):
    """Build a token by hand, so we can make fake and expired ones."""
    payload = {"sub": "ali@example.com", "exp": int(time.time()) + seconds_valid}
    return jwt.encode(payload, secret, algorithm=algorithm)


# ---------- passwords ----------


def test_correct_password_is_accepted():
    stored = hash_password("my-password-123")
    assert verify_password("my-password-123", stored)


def test_wrong_password_is_rejected():
    stored = hash_password("my-password-123")
    assert not verify_password("another-password", stored)


def test_same_password_gets_different_hashes():
    # The random salt makes every hash different
    assert hash_password("same-password") != hash_password("same-password")


def test_broken_stored_value_is_rejected():
    assert not verify_password("anything", "this-is-not-a-hash")


# ---------- tokens ----------


def test_token_round_trip():
    token = create_token("ali@example.com")
    assert read_token(token) == "ali@example.com"


def test_forged_identity_is_rejected():
    # Take Ali's header and signature, but put Sara's identity in the middle
    ali_header, _, ali_signature = create_token("ali@example.com").split(".")
    _, sara_payload, _ = create_token("sara@example.com").split(".")
    forged = ".".join([ali_header, sara_payload, ali_signature])

    assert read_token(forged) is None


def test_expired_token_is_rejected():
    assert read_token(make_token(TEST_SECRET, seconds_valid=-10)) is None


def test_token_signed_with_another_secret_is_rejected():
    assert read_token(make_token(OTHER_SECRET)) is None


def test_unsigned_token_is_rejected():
    # The classic attack: a token that says "no signature needed"
    assert read_token(make_token(None, algorithm="none")) is None


def test_garbage_is_rejected():
    assert read_token("this.is.garbage") is None
    assert read_token("") is None


def test_missing_secret_stops_the_app(monkeypatch):
    monkeypatch.delenv("JWT_SECRET")
    with pytest.raises(RuntimeError):
        create_token("ali@example.com")