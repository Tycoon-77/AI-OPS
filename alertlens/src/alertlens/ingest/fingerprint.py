"""Fingerprinting — normalise a redacted message into a stable template string."""
import hashlib
import re

# Replace numeric literals (integers and decimals)
_NUM = re.compile(r"\b\d+(?:\.\d+)?\b")
# Replace already-redacted tokens
_HOST = re.compile(r"\bhost-[0-9a-f]{4}\b")
_IP   = re.compile(r"\bip-[0-9a-f]{4}\b")
_CUST = re.compile(r"\bcust-[0-9a-f]{4}\b")
_UUID = re.compile(r"\buuid-[0-9a-f]{4}\b")
_EMAIL= re.compile(r"\bemail-[0-9a-f]{4}\b")
# Percentage symbol that might remain
_PCT  = re.compile(r"\bpct\b")


def make_template(redacted_msg: str) -> str:
    """Convert a redacted alert message into a normalised fingerprint template."""
    t = _HOST.sub("<HOST>", redacted_msg)
    t = _IP.sub("<IP>", t)
    t = _CUST.sub("<CUST>", t)
    t = _UUID.sub("<UUID>", t)
    t = _EMAIL.sub("<EMAIL>", t)
    t = _NUM.sub("<NUM>", t)
    t = t.lower()
    t = " ".join(t.split())  # collapse whitespace
    return t


def fingerprint_id(source: str, template: str) -> str:
    """SHA-1 of ``source|template``, first 12 hex chars."""
    raw = f"{source}|{template}"
    return hashlib.sha1(raw.encode()).hexdigest()[:12]
