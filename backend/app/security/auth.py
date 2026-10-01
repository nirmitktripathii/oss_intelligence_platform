"""
Sign-in for the agent endpoints.

Anyone may use the read-only tools. Tools that change things (clone, edit, commit, pull
request, email) need a signed-in user whose GitHub login is on ``AUTH_ALLOWED_LOGINS``
(``*`` = any signed-in GitHub user).

Identity comes from GitHub OAuth (see ``app/api/v1/auth.py``). After sign-in the API hands the
browser a short-lived signed token, sent back as ``Authorization: Bearer <token>``. Tokens are
stateless HMAC-SHA256 envelopes, so there is no user table and nothing to revoke except by
changing ``AUTH_SECRET``. The OAuth ``state`` value uses the same envelope with a different
``kind`` so one can never be replayed as the other.
"""

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, Optional

from fastapi import Header, HTTPException

from app.config import settings

KIND_SESSION = "session"
KIND_STATE = "state"
MIN_SECRET_CHARS = 32


class AuthNotConfigured(Exception):
    """Sign-in was used but AUTH_SECRET (and the GitHub OAuth app) are not set."""


@dataclass(frozen=True)
class AuthUser:
    login: str


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _secret() -> bytes:
    secret = (settings.AUTH_SECRET or "").strip()
    if len(secret) < MIN_SECRET_CHARS:
        raise AuthNotConfigured(f"AUTH_SECRET must be set to at least {MIN_SECRET_CHARS} characters.")
    return secret.encode("utf-8")


def _sign(body: str) -> str:
    return _b64(hmac.new(_secret(), body.encode("ascii"), hashlib.sha256).digest())


def issue_token(kind: str, ttl_seconds: int, **claims: Any) -> str:
    payload = {"k": kind, "exp": int(time.time()) + int(ttl_seconds), **claims}
    body = _b64(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    return f"{body}.{_sign(body)}"


def verify_token(token: Optional[str], kind: str) -> Optional[Dict[str, Any]]:
    """The token's claims, or ``None`` if it is missing, forged, expired, or of another kind."""
    if not token or token.count(".") != 1:
        return None
    try:
        body, signature = token.split(".")
        if not hmac.compare_digest(signature, _sign(body)):
            return None
        payload = json.loads(_unb64(body))
    except (AuthNotConfigured, ValueError, UnicodeError):
        return None
    if not isinstance(payload, dict) or payload.get("k") != kind:
        return None
    if int(payload.get("exp", 0)) < time.time():
        return None
    return payload


def allowed_logins() -> FrozenSet[str]:
    return frozenset(
        part.strip().lower() for part in (settings.AUTH_ALLOWED_LOGINS or "").split(",") if part.strip()
    )


def github_oauth_configured() -> bool:
    return bool(
        settings.AUTH_GITHUB_CLIENT_ID
        and settings.AUTH_GITHUB_CLIENT_SECRET
        and settings.AUTH_GITHUB_CALLBACK_URL
        and len((settings.AUTH_SECRET or "").strip()) >= MIN_SECRET_CHARS
    )


def user_from_authorization(authorization: Optional[str]) -> Optional[AuthUser]:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    claims = verify_token(authorization[7:].strip(), KIND_SESSION)
    login = (claims or {}).get("sub")
    return AuthUser(login=login) if isinstance(login, str) and login else None


async def optional_user(authorization: Optional[str] = Header(None)) -> Optional[AuthUser]:
    """FastAPI dependency: the signed-in user, or ``None`` for an anonymous caller."""
    return user_from_authorization(authorization)


def may_write(user: Optional[AuthUser]) -> bool:
    """Whether this caller may run tools that change things."""
    if settings.AGENT_ALLOW_ANONYMOUS_WRITES:
        return True
    if user is None:
        return False
    allowed = allowed_logins()
    # "*" opens it to every signed-in GitHub user. Safe only while the tools that change things are
    # pinned to a throwaway repo (the hosted Git/CI server is); the caller must still sign in.
    return "*" in allowed or user.login.lower() in allowed


def require_user(user: Optional[AuthUser]) -> AuthUser:
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to do this.", headers={"WWW-Authenticate": "Bearer"})
    return user
