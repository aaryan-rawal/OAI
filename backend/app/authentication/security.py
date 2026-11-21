"""Password hashing and JWT helpers."""
from datetime import datetime, timedelta, timezone
import jwt
from jwt import InvalidTokenError
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from app.config import settings

_ALGORITHM = "HS256"
_hasher = PasswordHasher()

def hash_password(password: str) -> str:
    return _hasher.hash(password)

def verify_password(password: str, encoded: str) -> bool:
    try:
        return _hasher.verify(encoded, password)
    except (VerifyMismatchError, VerificationError, ValueError):
        return False

def create_access_token(user_id: str) -> str:
    secret = settings.effective_jwt_secret
    if len(secret) < 32:
        raise RuntimeError("JWT signing secret must be at least 32 characters. Update JWT_SECRET_KEY in the root .env; the application will not rewrite it automatically.")
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": user_id, "exp": expires}, secret, algorithm=_ALGORITHM)

def decode_access_token(token: str) -> str | None:
    secret = settings.effective_jwt_secret
    if len(secret) < 32:
        return None
    try:
        payload = jwt.decode(token, secret, algorithms=[_ALGORITHM])
        subject = payload.get("sub")
        return subject if isinstance(subject, str) else None
    except InvalidTokenError:
        return None
