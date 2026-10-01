"""Shared-secret check in front of the MCP endpoint.

The Git/CI server can clone, run tests, push and open pull requests with a GitHub token, so it
must never be callable by anyone but the agent backend, which is where the user's approval gate
and sign-in live. The backend sends ``Authorization: Bearer <GITCI_MCP_TOKEN>`` and every other
request gets a 401 before it reaches any tool.
"""

from __future__ import annotations

import hmac
import ipaddress
import json
from typing import Awaitable, Callable, Dict, MutableMapping

Scope = MutableMapping[str, object]
Receive = Callable[[], Awaitable[MutableMapping[str, object]]]
Send = Callable[[MutableMapping[str, object]], Awaitable[None]]

MIN_TOKEN_CHARS = 32


def is_loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class BearerAuthMiddleware:
    """Pure ASGI middleware: 401 unless the bearer token matches (constant-time compare)."""

    def __init__(self, app, token: str):
        self.app = app
        self._token = token.encode("utf-8")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            return await self.app(scope, receive, send)
        if scope["type"] == "http" and self._authorized(scope):
            return await self.app(scope, receive, send)
        if scope["type"] == "http":
            body = json.dumps({"error": "unauthorized"}).encode("utf-8")
            await send({
                "type": "http.response.start", "status": 401,
                "headers": [(b"content-type", b"application/json"), (b"www-authenticate", b"Bearer"),
                            (b"content-length", str(len(body)).encode("ascii"))],
            })
            await send({"type": "http.response.body", "body": body})
        else:  # websocket and anything else: refuse
            await send({"type": "websocket.close", "code": 1008})

    def _authorized(self, scope: Scope) -> bool:
        headers: Dict[bytes, bytes] = dict(scope.get("headers") or [])  # type: ignore[arg-type]
        value = headers.get(b"authorization", b"")
        scheme, _, presented = value.partition(b" ")
        return scheme.lower() == b"bearer" and hmac.compare_digest(presented.strip(), self._token)


def require_token(host: str, token: str) -> None:
    """Refuse to listen on a non-loopback address without a strong token."""
    if token and len(token) < MIN_TOKEN_CHARS:
        raise RuntimeError(f"GITCI_MCP_TOKEN must be at least {MIN_TOKEN_CHARS} characters.")
    if not token and not is_loopback(host):
        raise RuntimeError(
            "GITCI_MCP_TOKEN is required when the server listens beyond localhost: without it anyone "
            "who finds the URL could clone, push and open pull requests."
        )
