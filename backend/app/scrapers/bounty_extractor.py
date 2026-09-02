"""Real-time regex & label parser extracting bounty amounts, sources, and payout URLs."""

import re
from typing import Any, Dict, List, Optional, Tuple


# Regex patterns for identifying bounty amounts
BOUNTY_REGEX_PATTERNS = [
    # Explicit $ amount: $100, $ 250, $1,500, $50.00
    re.compile(r"\$\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{1,2})?|[0-9]+(?:\.[0-9]{1,2})?)"),
    # Amount followed by USD/dollar: 500 USD, 250 dollars
    re.compile(r"([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{1,2})?|[0-9]+)\s*(?:USD|dollars|usd)", re.IGNORECASE),
    # Bot syntax: /bounty $500 or /bounty 500
    re.compile(r"/bounty\s+\$?([0-9]+(?:\.[0-9]{1,2})?)", re.IGNORECASE),
    # Funding on Polar syntax: Funding on Polar: $250
    re.compile(r"Funding on Polar:\s*\$?([0-9]+(?:\.[0-9]{1,2})?)", re.IGNORECASE),
    # Emoji cash: 💵 $250 or 💰 $500
    re.compile(r"[💵💰🪙]\s*\$?([0-9]+(?:\.[0-9]{1,2})?)"),
    # Algora/Polar keyword prefixes: bounty: $250
    re.compile(r"(?:bounty|reward|funded|prize):\s*\$?([0-9]+(?:\.[0-9]{1,2})?)", re.IGNORECASE),
]

# URL extraction patterns
POLAR_URL_PATTERN = re.compile(r"https?://(?:www\.)?polar\.sh/[^\s/]+/[^\s/]+/issues/\d+", re.IGNORECASE)
ALGORA_URL_PATTERN = re.compile(r"https?://(?:console\.)?algora\.io/[^\s]+", re.IGNORECASE)
GENERIC_BOUNTY_URL_PATTERN = re.compile(r"https?://(?:www\.)?(?:polar\.sh|algora\.io|gitcoin\.co|opire\.dev|github\.com/sponsors)/[^\s\)\"\'>]+", re.IGNORECASE)


class BountyExtractor:
    """Extracts monetary bounty values, platforms, and claim links from issue text and labels."""

    @classmethod
    def extract_bounty_from_labels(cls, labels: List[Dict[str, Any]]) -> Optional[Tuple[float, str]]:
        """Check labels for bounty definitions like 'bounty: $100' or 'funded: $250'."""
        for label_obj in labels:
            name = label_obj.get("name", "") if isinstance(label_obj, dict) else str(label_obj)
            name_lower = name.lower()

            # Check if label itself indicates a bounty
            if "bounty" in name_lower or "funded" in name_lower or "algora" in name_lower or "polar" in name_lower:
                # Look for numbers inside label name
                for pattern in BOUNTY_REGEX_PATTERNS:
                    match = pattern.search(name)
                    if match:
                        raw_val = match.group(1).replace(",", "")
                        try:
                            val = float(raw_val)
                            if 5.0 <= val <= 50000.0:  # Reasonable bounty range
                                source = cls.detect_source(name, "")
                                return val, source
                        except ValueError:
                            pass
        return None

    @classmethod
    def extract_bounty_from_text(cls, text: str) -> Optional[Tuple[float, str, Optional[str]]]:
        """Parse title, body, and comments for bounty disclosures."""
        if not text:
            return None

        detected_amount: Optional[float] = None
        detected_source: str = "Unknown"
        detected_url: Optional[str] = None

        # Check for URLs first
        url_match = GENERIC_BOUNTY_URL_PATTERN.search(text)
        if url_match:
            detected_url = url_match.group(0)

        # Match regex patterns
        for pattern in BOUNTY_REGEX_PATTERNS:
            for match in pattern.finditer(text):
                raw_val = match.group(1).replace(",", "")
                try:
                    val = float(raw_val)
                    # Filter out common false positives (e.g. $0, $1, $404 HTTP status, $8080 port)
                    if val in (404.0, 500.0, 8000.0, 8080.0, 3000.0, 200.0) and "http" in text.lower():
                        # Verify if this is really a bounty context
                        start = max(0, match.start() - 20)
                        end = min(len(text), match.end() + 20)
                        surrounding = text[start:end].lower()
                        if not any(k in surrounding for k in ["bounty", "reward", "polar", "algora", "funded", "💵", "💰"]):
                            continue

                    if 10.0 <= val <= 25000.0:
                        detected_amount = val
                        detected_source = cls.detect_source(text, detected_url or "")
                        break
                except ValueError:
                    continue
            if detected_amount is not None:
                break

        if detected_amount is not None:
            return detected_amount, detected_source, detected_url
        return None

    @classmethod
    def detect_source(cls, text: str, url: str) -> str:
        """Determine the funding platform."""
        combined = (text + " " + url).lower()
        if "polar.sh" in combined or "polar" in combined:
            return "Polar"
        elif "algora.io" in combined or "algora" in combined or "/bounty" in combined:
            return "Algora"
        elif "github.com/sponsors" in combined or "sponsor" in combined:
            return "GitHub Sponsors"
        elif "opire" in combined:
            return "Opire"
        elif "gitcoin" in combined:
            return "Gitcoin"
        return "Unknown"

    @classmethod
    def parse_issue(
        cls,
        title: str,
        body: Optional[str],
        labels: List[Dict[str, Any]],
        html_url: str,
    ) -> Tuple[bool, Optional[float], Optional[str], Optional[str]]:
        """
        Unified extraction returning: (has_bounty, amount_usd, source, bounty_url).
        """
        body_text = body or ""
        combined_text = f"{title}\n{body_text}"

        # 1. Label check
        label_res = cls.extract_bounty_from_labels(labels)
        if label_res:
            amount, source = label_res
            # Look for specific bounty URL or fallback to issue URL
            url_match = GENERIC_BOUNTY_URL_PATTERN.search(combined_text)
            bounty_url = url_match.group(0) if url_match else html_url
            return True, amount, source, bounty_url

        # 2. Text check
        text_res = cls.extract_bounty_from_text(combined_text)
        if text_res:
            amount, source, b_url = text_res
            return True, amount, source, b_url or html_url

        # 3. Bounty label present but no amount could be parsed from labels or text.
        # The label is a real signal that a bounty exists, but we must NOT invent a
        # dollar figure. Return has_bounty=True with amount=None (undisclosed). Rows
        # with a NULL amount are excluded from the ROI-ranked /bounties board
        # (bounty_amount_usd >= 0 filters out NULL) and never contribute a fabricated
        # ROI — they only surface as bounty-labeled on the general issues list.
        for label_obj in labels:
            name = label_obj.get("name", "") if isinstance(label_obj, dict) else str(label_obj)
            name_l = name.lower()
            if any(k in name_l for k in ["bounty", "funded", "reward", "💵", "algora", "polar"]):
                source = cls.detect_source(name_l + " " + combined_text, "")
                return True, None, source, html_url

        return False, None, None, None
