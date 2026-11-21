import pytest
from app.config import settings
from app.authentication.security import hash_password, verify_password, create_access_token, decode_access_token


def test_argon2_password_hash_is_not_plaintext():
    password="correct-horse-battery"
    hashed=hash_password(password)
    assert hashed != password
    assert verify_password(password,hashed)
    assert not verify_password("wrong-password",hashed)

def test_jwt_round_trip_uses_user_id(monkeypatch):
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", "test-secret-key-with-at-least-32-characters")
    monkeypatch.setattr(settings, "JWT_SECRET", "")
    token=create_access_token("test-user-id")
    assert decode_access_token(token)=="test-user-id"
    assert decode_access_token(token+"broken") is None


def test_short_jwt_secret_is_rejected(monkeypatch):
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", "too-short")
    monkeypatch.setattr(settings, "JWT_SECRET", "")
    with pytest.raises(RuntimeError, match="at least 32 characters"):
        create_access_token("test-user-id")
