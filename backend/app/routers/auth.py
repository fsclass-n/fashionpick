import secrets
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db, utcnow
from ..models import User
from ..schemas import LoginIn, RegisterIn, TestLoginIn, TokenOut, UserOut
from ..security import create_access_token, create_token, decode_token, get_current_user, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

OAUTH = {
    "google": {
        "authorize": "https://accounts.google.com/o/oauth2/v2/auth",
        "token": "https://oauth2.googleapis.com/token",
        "profile": "https://openidconnect.googleapis.com/v1/userinfo",
        "scope": "openid email profile",
    },
    "naver": {
        "authorize": "https://nid.naver.com/oauth2.0/authorize",
        "token": "https://nid.naver.com/oauth2.0/token",
        "profile": "https://openapi.naver.com/v1/nid/me",
        "scope": "",
    },
    "kakao": {
        "authorize": "https://kauth.kakao.com/oauth/authorize",
        "token": "https://kauth.kakao.com/oauth/token",
        "profile": "https://kapi.kakao.com/v2/user/me",
        "scope": "profile_nickname account_email",
    },
}


def _issue(db: Session, user: User) -> TokenOut:
    user.last_login_at = utcnow()
    db.commit()
    return TokenOut(access_token=create_access_token(user), user=UserOut.model_validate(user))


@router.get("/providers")
def providers() -> dict:
    return {"oauth": {p: bool(c["client_id"] and c["client_secret"]) for p, c in settings.oauth.items()},
            "test_login": settings.enable_test_login,
            "test_accounts": {"user": settings.test_user_email, "admin": settings.test_admin_email}
            if settings.enable_test_login else {}}


@router.post("/register", response_model=TokenOut, status_code=201)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == data.email.lower())):
        raise HTTPException(409, "이미 가입된 이메일입니다.")
    user = User(email=data.email.lower(), name=data.name, password_hash=hash_password(data.password))
    db.add(user)
    db.commit()
    return _issue(db, user)


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if not user or not user.is_active or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "이메일 또는 비밀번호가 올바르지 않습니다.")
    return _issue(db, user)


@router.post("/test-login", response_model=TokenOut)
def test_login(data: TestLoginIn, db: Session = Depends(get_db)):
    """포트폴리오 시연용 간편 로그인. 운영 환경에서는 ENABLE_TEST_LOGIN=false 로 차단."""
    if not settings.enable_test_login:
        raise HTTPException(403, "테스트 로그인이 비활성화되어 있습니다.")
    email = settings.test_admin_email if data.role == "admin" else settings.test_user_email
    user = db.scalar(select(User).where(User.email == email))
    if not user:
        raise HTTPException(404, "테스트 계정이 없습니다. 서버 초기화를 확인하세요.")
    user.role = data.role
    return _issue(db, user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


# ---------- OAuth (Google / Naver / Kakao) ----------
def _redirect_uri(provider: str) -> str:
    return f"{settings.backend_public_url}/api/auth/oauth/{provider}/callback"


def _safe_frontend(url: str | None) -> str:
    url = (url or "").rstrip("/")
    return url if url in settings.cors_origins else settings.frontend_url


def _provider(provider: str) -> tuple[dict, dict]:
    if provider not in OAUTH:
        raise HTTPException(404, "지원하지 않는 로그인 방식입니다.")
    creds = settings.oauth[provider]
    if not (creds["client_id"] and creds["client_secret"]):
        raise HTTPException(503, f"{provider} 로그인이 아직 설정되지 않았습니다.")
    return OAUTH[provider], creds


@router.get("/oauth/{provider}/login")
def oauth_login(provider: str, redirect: str | None = Query(default=None)):
    conf, creds = _provider(provider)
    state = create_token({"type": "oauth_state", "provider": provider, "redirect": _safe_frontend(redirect),
                          "nonce": secrets.token_urlsafe(8)}, expires_minutes=10)
    params = {"client_id": creds["client_id"], "redirect_uri": _redirect_uri(provider), "response_type": "code", "state": state}
    if conf["scope"]:
        params["scope"] = conf["scope"]
    return RedirectResponse(f"{conf['authorize']}?{urlencode(params)}")


def _profile(provider: str, data: dict) -> tuple[str, str, str, bool]:
    """(provider_id, email, name, email_verified)"""
    if provider == "google":
        return data["sub"], data.get("email", ""), data.get("name") or data.get("email", ""), bool(data.get("email_verified"))
    if provider == "naver":
        r = data["response"]
        return r["id"], r.get("email", ""), r.get("name") or r.get("nickname") or "네이버 회원", bool(r.get("email"))
    account = data.get("kakao_account", {})
    return (str(data["id"]), account.get("email", ""), account.get("profile", {}).get("nickname") or "카카오 회원",
            bool(account.get("is_email_verified")))


@router.get("/oauth/{provider}/callback")
def oauth_callback(provider: str, code: str | None = None, state: str | None = None, error: str | None = None,
                   db: Session = Depends(get_db)):
    try:
        payload = decode_token(state or "")
        if payload.get("type") != "oauth_state" or payload.get("provider") != provider:
            raise jwt.InvalidTokenError("state mismatch")
    except jwt.PyJWTError:
        return RedirectResponse(f"{settings.frontend_url}/oauth/callback#error=invalid_state")
    front = _safe_frontend(payload.get("redirect"))
    if error or not code:
        return RedirectResponse(f"{front}/oauth/callback#error={error or 'cancelled'}")

    conf, creds = _provider(provider)
    try:
        token_res = httpx.post(conf["token"], timeout=15, headers={"Accept": "application/json"}, data={
            "grant_type": "authorization_code", "code": code, "state": state, "redirect_uri": _redirect_uri(provider),
            "client_id": creds["client_id"], "client_secret": creds["client_secret"],
        })
        token_res.raise_for_status()
        access = token_res.json()["access_token"]
        prof_res = httpx.get(conf["profile"], timeout=15, headers={"Authorization": f"Bearer {access}"})
        prof_res.raise_for_status()
        provider_id, email, name, verified = _profile(provider, prof_res.json())
    except (httpx.HTTPError, KeyError):
        return RedirectResponse(f"{front}/oauth/callback#error=provider_error")

    user = db.scalar(select(User).where(User.provider == provider, User.provider_id == provider_id))
    if not user and email and verified:
        user = db.scalar(select(User).where(User.email == email.lower()))
    if not user:
        taken = bool(email) and db.scalar(select(User).where(User.email == email.lower())) is not None
        fallback = f"{provider}_{provider_id}@oauth.fashionpick"
        user = User(email=(fallback if not email or taken else email).lower(), name=name[:100],
                    provider=provider, provider_id=provider_id)
        db.add(user)
    elif not user.provider_id:
        user.provider, user.provider_id = provider, provider_id
    db.commit()
    token = _issue(db, user).access_token
    return RedirectResponse(f"{front}/oauth/callback#token={token}")
