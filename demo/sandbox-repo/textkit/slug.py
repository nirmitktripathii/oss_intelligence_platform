"""Turn a title into a URL-safe slug."""

import re


def slugify(text: str) -> str:
    """Lower-case the text and join its words with single hyphens."""
    return re.sub(r"\s+", "-", text.strip().lower())
