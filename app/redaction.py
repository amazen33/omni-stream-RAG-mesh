"""Deterministic PII redaction/tokenization helpers."""
from __future__ import annotations
import hashlib
import re
from typing import Dict, Tuple

class PIIRedactor:
    """Application-facing redactor; keeps the salt in configuration, never payloads."""
    def __init__(self, salt: str) -> None:
        self.salt = salt

    def redact(self, text: str) -> Tuple[str, Dict[str, int]]:
        return redact(text, self.salt)

PATTERNS = {
    "email": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    "phone": re.compile(r"(?<!\w)(?:\+?\d[\d ()-]{7,}\d)(?!\w)"),
    "card": re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)"),
    "ssn": re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)"),
}

def token_for(kind: str, value: str, salt: str) -> str:
    digest = hashlib.sha256(f"{salt}:{kind}:{value}".encode()).hexdigest()[:16]
    return f"<PII_{kind.upper()}_{digest}>"

def redact(text: str, salt: str = "change-me") -> Tuple[str, Dict[str, int]]:
    counts: Dict[str, int] = {}
    result = text
    # Order prevents a phone/card pattern from consuming a SSN.
    for kind in ("ssn", "card", "email", "phone"):
        def replace(match: re.Match[str]) -> str:
            counts[kind] = counts.get(kind, 0) + 1
            return token_for(kind, match.group(0), salt)
        result = PATTERNS[kind].sub(replace, result)
    return result, counts
