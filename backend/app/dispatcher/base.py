"""Base Notifier Interface and Unified Alert Payload."""

from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel, Field


class AlertPayload(BaseModel):
    """Uniform data structure dispatched across notification channels."""

    issue_id: str
    title: str
    repo: str
    html_url: str
    domain: str = "Web"
    tech_stack: List[str] = Field(default_factory=list)
    difficulty: str = "Medium"
    estimated_hours: float = 2.0
    bounty_usd: Optional[float] = None
    hourly_roi: Optional[float] = None
    summary: str = ""
    suggested_files: List[str] = Field(default_factory=list)

    @property
    def formatted_bounty(self) -> str:
        if self.bounty_usd and self.bounty_usd > 0:
            roi_str = f" (${self.hourly_roi:.0f}/hr)" if self.hourly_roi else ""
            return f"💵 **${self.bounty_usd:,.0f} USD**{roi_str}"
        return "⚡ Unfunded / Open"


class BaseNotifier(ABC):
    """Abstract interface for all notification channel adapters."""

    @abstractmethod
    async def send_alert(self, destination: str, payload: AlertPayload) -> bool:
        """Send an issue/bounty alert to destination."""
        pass

    @abstractmethod
    async def send_test_message(self, destination: str, message: str) -> bool:
        """Send a test verification message to destination."""
        pass
