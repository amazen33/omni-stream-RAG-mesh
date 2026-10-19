"""Validate runtime security settings before constructing any integration."""
from dataclasses import dataclass, field
import os


DEVELOPMENT_PROFILES = frozenset({"local", "test", "development"})
PROFILES = DEVELOPMENT_PROFILES | {"production"}
DEFAULT_KEYS = frozenset({"change-me", "changeme", "local-demo-only", "replace-with-random-salt"})


@dataclass(frozen=True)
class RuntimeSettings:
    profile: str
    token_key: str = field(repr=False)
    api_docs: bool = False
    include_tracebacks: bool = False

    @classmethod
    def from_environment(cls) -> "RuntimeSettings":
        profile = os.getenv("RUNTIME_PROFILE", "production").strip().lower()
        if profile not in PROFILES:
            raise RuntimeError("RUNTIME_PROFILE must be production, local, test or development")
        development = profile in DEVELOPMENT_PROFILES
        token_key = os.getenv("PII_TOKEN_SALT", "change-me" if development else "")
        if not token_key.strip() or (not development and token_key.strip() in DEFAULT_KEYS):
            raise RuntimeError("PII_TOKEN_SALT must be a non-default key outside a local/test runtime")
        return cls(profile, token_key,
                   development and os.getenv("ENABLE_API_DOCS", "false").lower() == "true",
                   development and os.getenv("LOG_INCLUDE_TRACEBACKS", "false").lower() == "true")
