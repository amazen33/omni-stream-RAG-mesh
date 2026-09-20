from __future__ import annotations
import uuid
from dataclasses import dataclass
from domain.events import TelemetryIngested
from domain.entities import DocumentChunk


@dataclass
class IngestionService:
    """Coordinates safe chunk creation and emits a telemetry event."""

    redactor: object
    publisher: object | None = None

    def ingest(
        self, text: str, source: str, request_id: str, correlation_id: str | None = None, traceparent: str | None = None
    ) -> tuple[list[DocumentChunk], dict[str, int]]:
        safe, counts = self.redactor.redact(text)
        # Tokenize source metadata here as well as at the HTTP ingress.  The
        # service is also invoked by batch jobs, so it cannot rely on callers
        # to keep raw labels out of vector metadata and telemetry.
        source_token = self.redactor.sanitize_for_boundary(source, "source")
        cid = correlation_id or str(uuid.uuid4())
        chunks = [
            DocumentChunk(f"{request_id}-{i}-{uuid.uuid4().hex[:8]}", chunk, source_token)
            for i, chunk in enumerate(self._split(safe))
        ]
        event = TelemetryIngested(
            request_id=request_id,
            correlation_id=cid,
            traceparent=traceparent or "",
            source_token=source_token,
            chunk_count=len(chunks),
            pii_counts=counts,
        )
        if self.publisher:
            self.publisher.publish(event, traceparent=traceparent)
        return chunks, counts

    @staticmethod
    def _split(text: str, size: int = 800, overlap: int = 120) -> list[str]:
        try:
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            return RecursiveCharacterTextSplitter(chunk_size=size, chunk_overlap=overlap).split_text(text)
        except ImportError:
            return [text[i:i + size] for i in range(0, len(text), max(1, size - overlap))]
