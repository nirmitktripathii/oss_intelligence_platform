"""Lemon Squeezy API client & checkout session initiator."""

import logging
import uuid
from typing import Optional, Tuple
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

LEMON_VARIANT_MAPPING = {
    "pro_monthly": "112233",
    "pro_yearly": "112234",
    "team_monthly": "112235",
    "team_yearly": "112236",
}


class LemonSqueezyClient:
    """Async API Client for Lemon Squeezy Hosted Checkouts."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        store_id: Optional[str] = None,
    ):
        self.api_key = api_key or settings.LEMON_SQUEEZY_API_KEY
        self.store_id = store_id or settings.LEMON_SQUEEZY_STORE_ID
        self.base_url = "https://api.lemonsqueezy.com/v1"

    async def create_checkout_session(
        self,
        plan_id: str,
        customer_email: str,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Creates a Lemon Squeezy hosted checkout URL.
        Returns: (session_id, checkout_url)
        """
        session_id = f"ls_sess_{uuid.uuid4().hex[:16]}"
        s_url = success_url or f"{settings.FRONTEND_URL}/dashboard?checkout=success&session_id={session_id}"
        variant_id = LEMON_VARIANT_MAPPING.get(plan_id, "112233")

        if not self.api_key or not self.store_id:
            # Fallback direct checkout link
            mock_url = f"https://gitscout.lemonsqueezy.com/checkout/buy/{variant_id}?checkout[email]={customer_email}&checkout[custom][session_id]={session_id}"
            return session_id, mock_url

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/vnd.api+json",
            "Content-Type": "application/vnd.api+json",
        }

        body = {
            "data": {
                "type": "checkouts",
                "attributes": {
                    "checkout_data": {
                        "email": customer_email,
                        "custom": {"session_id": session_id, "plan_id": plan_id},
                    },
                    "product_options": {
                        "redirect_url": s_url,
                    },
                },
                "relationships": {
                    "store": {"data": {"type": "stores", "id": str(self.store_id)}},
                    "variant": {"data": {"type": "variants", "id": str(variant_id)}},
                },
            }
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(f"{self.base_url}/checkouts", json=body, headers=headers)
                if res.status_code in (200, 201):
                    data = res.json()
                    checkout_url = data.get("data", {}).get("attributes", {}).get("url")
                    return session_id, checkout_url or s_url
                logger.warning(f"Lemon Squeezy returned {res.status_code}: {res.text}")
        except Exception as exc:
            logger.error(f"Error initiating Lemon Squeezy checkout: {exc}")

        return session_id, f"https://gitscout.lemonsqueezy.com/checkout/buy/{variant_id}?checkout[email]={customer_email}"
