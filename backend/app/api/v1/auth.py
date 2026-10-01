"""
Sign-in endpoints (GitHub OAuth).

    GET /auth/github/login      send the browser to GitHub
    GET /auth/github/callback   GitHub sends it back here; we redirect to the frontend with a token
    GET /auth/me                who am I, and may I run tools that change things

The signed token travels back in the URL *fragment* (``/alexa#token=...``), which browsers never
send to a server or put in a Referer header. The OAuth ``state`` is signed, short-lived and also
bound to the browser by a cookie, so a forged callback cannot sign someone in as someone else.
"""

import logging
import secrets
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.config import settings
from app.security.auth import (
    KIND_SESSION,
    KIND_STATE,
    AuthUser,
    github_oauth_configured,
    issue_token,
    may_write,
    optional_user,
    verify_token,
)
from app.security.rate_limiter import limiter

logger = logging.getLogger("gitscout.auth")

router = APIRouter(prefix="/auth", tags=["Sign-in"])

GITHUB_AUTHORIZE = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
STATE_COOKIE = "gs_oauth_state"
STATE_TTL_SECONDS = 600


def _frontend_target(**params: str) -> str:
    base = settings.FRONTEND_URL.rstrip("/") + "/alexa"
    if "token" in params:
        return f"{base}#token={params['token']}"
    return f"{base}?{urlencode(params)}" if params else base


def _fail(code: str) -> RedirectResponse:
    response = RedirectResponse(_frontend_target(auth_error=code), status_code=302)
    response.delete_cookie(STATE_COOKIE)
    return response


@router.get("/me", summary="Who Am I")
async def me(user: Optional[AuthUser] = Depends(optional_user)):
    """The caller's sign-in state, and whether they may run tools that change things."""
    return {
        "signed_in": user is not None,
        "login": user.login if user else None,
        "can_write": may_write(user),
        "sign_in_available": github_oauth_configured(),
    }


@router.get("/github/login", summary="Sign In With GitHub")
@limiter.limit("20/minute")
async def github_login(request: Request):
    if not github_oauth_configured():
        raise HTTPException(status_code=503, detail="Sign-in is not configured on this server.")
    nonce = secrets.token_urlsafe(16)
    state = issue_token(KIND_STATE, STATE_TTL_SECONDS, n=nonce)
    query = urlencode({
        "client_id": settings.AUTH_GITHUB_CLIENT_ID,
        "redirect_uri": settings.AUTH_GITHUB_CALLBACK_URL,
        "state": state,
        "scope": "",  # public profile only: we need the login name and nothing else
        "allow_signup": "false",
    })
    response = RedirectResponse(f"{GITHUB_AUTHORIZE}?{query}", status_code=302)
    response.set_cookie(
        STATE_COOKIE, nonce, max_age=STATE_TTL_SECONDS, httponly=True, samesite="lax",
        secure=settings.AUTH_GITHUB_CALLBACK_URL.startswith("https://"),
    )
    return response


@router.get("/github/callback", summary="GitHub Sign-In Callback")
@limiter.limit("20/minute")
async def github_callback(request: Request, code: str = "", state: str = ""):
    if not github_oauth_configured():
        raise HTTPException(status_code=503, detail="Sign-in is not configured on this server.")
    claims = verify_token(state, KIND_STATE)
    cookie = request.cookies.get(STATE_COOKIE) or ""
    if not code or claims is None or not secrets.compare_digest(str(claims.get("n", "")), cookie):
        return _fail("state")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            exchanged = await client.post(
                GITHUB_TOKEN_URL,
                data={
                    "client_id": settings.AUTH_GITHUB_CLIENT_ID,
                    "client_secret": settings.AUTH_GITHUB_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": settings.AUTH_GITHUB_CALLBACK_URL,
                },
                headers={"Accept": "application/json"},
            )
            access_token = exchanged.json().get("access_token") if exchanged.status_code == 200 else None
            if not access_token:
                return _fail("exchange")
            profile = await client.get(
                GITHUB_USER_URL,
                headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
            )
            login = profile.json().get("login") if profile.status_code == 200 else None
    except (httpx.HTTPError, ValueError):
        logger.warning("[AUTH] GitHub sign-in failed talking to GitHub", exc_info=True)
        return _fail("github")
    if not isinstance(login, str) or not login:
        return _fail("profile")

    token = issue_token(KIND_SESSION, settings.AUTH_TOKEN_TTL_SECONDS, sub=login)
    logger.info("[AUTH] %s signed in", login)
    response = RedirectResponse(_frontend_target(token=token), status_code=302)
    response.delete_cookie(STATE_COOKIE)
    return response
