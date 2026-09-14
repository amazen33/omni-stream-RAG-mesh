"""Small immutable domain entities (no infrastructure imports)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentChunk:
    chunk_id: str
    text: str
    source: str


@dataclass(frozen=True)
class Transaction:
    transaction_id: str
    payload: dict


@dataclass(frozen=True)
class AuditRecord:
    request_id: str
    payload: dict
