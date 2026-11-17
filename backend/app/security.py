import base64
import hashlib
import hmac
import re
import secrets
from datetime import timedelta

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db, utcnow
from .models import User

ALGORITHM = "HS256"
PBKDF2_ITERATIONS = 310_000
PASSWORD_RULE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9\s]).{8,64}$")
PASSWORD_RULE_MESSAGE = "비밀번호는 영문 대문자·소문자, 숫자, 특수문자를 모두 포함해 8자 이상이어야 합니다."

bearer = HTTPBearer(auto_error=False)


def validate_password(password: str) -> None:
    if not PASSWORD_RULE.match(password):
        raise ValueError(PASSWORD_RULE_MESSAGE)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        _, iterations, salt, digest = password_hash.split("$")
        expected = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.b64decode(salt), int(iterations))
        return hmac.compare_digest(expected, base64.b64decode(digest))
    except ValueError:
        return False


def create_token(data: dict, expires_minutes: int | None = None) -> str:
    payload = {**data, "exp": utcnow() + timedelta(minutes=expires_minutes or settings.access_token_expire_minutes)}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])


def create_access_token(user: User) -> str:
    return create_token({"sub": str(user.id), "role": user.role, "type": "access"})


def user_from_token(db: Session, token: str | None) -> User | None:
    if not token:
        return None
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        return None
    if payload.get("type") != "access":
        return None
    user = db.get(User, int(payload["sub"]))
    return user if user and user.is_active else None


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)
) -> User:
    user = user_from_token(db, credentials.credentials if credentials else None)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "로그인이 필요합니다.")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "관리자 권한이 필요합니다.")
    return user
