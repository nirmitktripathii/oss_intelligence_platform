"""Dodo Payments async client & checkout session generator."""

import logging
import uuid
from typing import Optional, Tuple
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

PLAN_PRODUCT_MAPPING = {
    "pro_monthly": "p_prod_gitscout_pro_monthly",
    "pro_yearly": "p_prod_gitscout_pro_yearly",
    "team_monthly": "p_prod_gitscout_team_monthly",
    "team_yearly": "p_prod_gitscout_team_yearly",
}


class DodoPaymentsClient:
    """Async API Client for Dodo Payments Checkout & Subscriptions."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        environment: Optional[str] = None,
    ):
        self.api_key = api_key or settings.DODO_PAYMENTS_API_KEY
        self.environment = environment or settings.DODO_ENVIRONMENT
        self.base_url = (
            "https://test.dodopayments.com"
            if self.environment == "test_mode"
            else "https://live.dodopayments.com"
        )

    async def create_checkout_session(
        self,
        plan_id: str,
        customer_email: str,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Creates a hosted checkout session URL.
        Returns: (session_id, checkout_url)
        """
        session_id = f"dodo_sess_{uuid.uuid4().hex[:16]}"
        s_url = success_url or f"{settings.FRONTEND_URL}/dashboard?checkout=success&session_id={session_id}"
        c_url = cancel_url or f"{settings.FRONTEND_URL}/pricing?checkout=cancelled"

        product_id = PLAN_PRODUCT_MAPPING.get(plan_id, "p_prod_gitscout_pro_monthly")

        if not self.api_key:
            # Generate deterministic test URL for zero-cost / dev setups
            mock_url = f"{self.base_url}/buy/{product_id}?session_id={session_id}&email={customer_email}&redirect={s_url}"
            return session_id, mock_url

        # Real API request
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "product_cart": [{"product_id": product_id, "quantity": 1}],
            "billing": {"email": customer_email},
            "return_url": s_url,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(f"{self.base_url}/checkouts", json=body, headers=headers)
                if res.status_code in (200, 201):
                    data = res.json()
                    return data.get("session_id", session_id), data.get("checkout_url", s_url)
                logger.warning(f"Dodo Payments returned status {res.status_code}: {res.text}")
        except Exception as exc:
            logger.error(f"Error calling Dodo Payments API: {exc}")

        return session_id, f"{self.base_url}/buy/{product_id}?session_id={session_id}&email={customer_email}"
