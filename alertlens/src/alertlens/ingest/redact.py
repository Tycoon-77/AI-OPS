"""Redaction — mask hostnames, IPs, customer IDs, UUIDs, emails with stable tokens."""
import hashlib
import hmac
import re

# Patterns ordered: most-specific first
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("uuid",  re.compile(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
        re.IGNORECASE,
    )),
    ("email", re.compile(
        r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b"
    )),
    ("ip",    re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
    # service-region-nn hostnames e.g. cart-ap1-03
    ("host",  re.compile(r"\b[a-z][a-z0-9\-]+-[a-z]{2}\d-\d{2,3}\b")),
    ("cust",  re.compile(r"\bcust-\d+\b")),
]


def _token(prefix: str, value: str, salt: str) -> str:
    """Return a stable 4-hex token for the given value."""
    digest = hmac.new(salt.encode(), value.encode(), hashlib.sha256).hexdigest()[:4]
    return f"{prefix}-{digest}"


def redact(text: str, salt: str) -> str:
    """Replace sensitive tokens in *text* with stable pseudonyms."""
    for prefix, pattern in _PATTERNS:
        text = pattern.sub(lambda m, p=prefix: _token(p, m.group(), salt), text)
    return text
