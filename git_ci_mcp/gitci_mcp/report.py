"""Telegram report sender: tells the owner what a mission did.

Deliberately narrow. The recipient is the one chat in TELEGRAM_CHAT_ID, never an argument, so
nothing the model (or text it read in an issue) says can aim a message anywhere else. The text is
a fixed template filled with length-capped fields, sent as plain text (no markup to inject), and
the link must be a pull request in an allowed repo. A small hourly cap bounds the damage even if
every approval were clicked.
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional

import httpx

from .config import Settings, settings as default_settings
from .sandbox import GitCiError, SandboxManager

TITLE_CHARS = 120
SUMMARY_CHARS = 1200
_PR_URL = re.compile(r"^https://github\.com/([A-Za-z0-9-]{1,39})/([A-Za-z0-9._-]{1,100})/pull/[0-9]{1,7}/?$")


def _clean(text: str, limit: int) -> str:
    """Capped, with control characters (other than newline and tab) replaced by spaces."""
    text = "".join(ch if ch in "\n\t" or ch >= " " else " " for ch in (text or "")).strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


class Reporter:
    def __init__(self, cfg: Settings = default_settings, sandboxes: Optional[SandboxManager] = None):
        self.cfg = cfg
        self._sandboxes = sandboxes or SandboxManager(cfg)
        self._sent: List[float] = []

    def _check_limit(self) -> None:
        now = time.time()
        self._sent = [t for t in self._sent if now - t < 3600]
        if len(self._sent) >= self.cfg.report_max_per_hour:
            raise GitCiError(f"Report limit reached ({self.cfg.report_max_per_hour} per hour). Try again later.")

    def render(self, title: str, summary: str, pr_url: str = "") -> str:
        lines = ["Developer Mission Control report", "", _clean(title, TITLE_CHARS) or "(no title)"]
        body = _clean(summary, SUMMARY_CHARS)
        if body:
            lines += ["", body]
        if pr_url:
            m = _PR_URL.match(pr_url.strip())
            if not m:
                raise GitCiError("pr_url must be a GitHub pull request link (https://github.com/owner/repo/pull/N).")
            self._sandboxes.check_repo(m.group(1), m.group(2))
            lines += ["", f"Draft pull request: {pr_url.strip()}"]
        return "\n".join(lines)

    async def send(self, title: str, summary: str, pr_url: str = "") -> Dict[str, Any]:
        if not (self.cfg.telegram_bot_token and self.cfg.telegram_chat_id):
            raise GitCiError("Reports are not set up on this server (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID).")
        text = self.render(title, summary, pr_url)
        self._check_limit()
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(
                    f"https://api.telegram.org/bot{self.cfg.telegram_bot_token}/sendMessage",
                    json={"chat_id": self.cfg.telegram_chat_id, "text": text, "disable_web_page_preview": True},
                )
        except httpx.HTTPError as exc:
            # The URL carries the bot token, so never let it into the message.
            raise GitCiError(f"Could not reach Telegram ({type(exc).__name__}).") from None
        if r.status_code != 200:
            raise GitCiError(f"Telegram refused the message (HTTP {r.status_code}). Check the bot token and chat id.")
        self._sent.append(time.time())
        return {"sent": True, "channel": "telegram", "characters": len(text)}
