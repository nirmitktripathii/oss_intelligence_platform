"""
SMTP rules shared by everything here that sends mail.

Render's free tier blocks outbound SMTP on ports 25, 465 and 587 (since September 2025): a
connection there is silently dropped and ends in a connect timeout. On a free instance, use the
provider's alternate port instead, such as 2525 (Brevo, Mailjet) or 2587 (Resend, Amazon SES).
Gmail has no alternate port, so Gmail SMTP only works from a paid instance.
"""

import aiosmtplib

# Ports that speak TLS from the first byte. Every other port starts in plain text and must upgrade
# with STARTTLS before the password is sent; start_tls=True makes that a requirement, not a hope.
IMPLICIT_TLS_PORTS = frozenset({465, 2465})

RENDER_FREE_BLOCKED_PORTS = frozenset({25, 465, 587})


def tls_options(port: int) -> dict:
    implicit = port in IMPLICIT_TLS_PORTS
    return {"use_tls": implicit, "start_tls": not implicit}


def failure_hint(port: int, exc: Exception) -> str:
    """Extra words for the log when a connection to a port Render's free tier blocks got no answer."""
    if port in RENDER_FREE_BLOCKED_PORTS and isinstance(exc, aiosmtplib.SMTPConnectTimeoutError):
        return f" (port {port} is blocked on Render's free tier; use the provider's alternate port)"
    return ""
