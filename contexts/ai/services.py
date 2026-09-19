from __future__ import annotations
from dataclasses import dataclass, field
import os
from domain.events import TransactionCompensated, TransactionProcessed
from .resilience import CallTimedOut, ResiliencePolicy, ResilienceError


@dataclass
class RetrievalService:
    store: object
    llm: object | None = None
    publisher: object | None = None
    resilience: ResiliencePolicy | None = None
    llm_resilience: ResiliencePolicy = field(default_factory=lambda: ResiliencePolicy(boundary="llm_inference", operation="invoke"))

    def __post_init__(self):
        if self.resilience is None:
            self.resilience = ResiliencePolicy(boundary="retrieval_store", operation="query")
        else:
            self.llm_resilience = ResiliencePolicy(
                max_concurrency=self.resilience.max_concurrency,
                rate_per_second=self.resilience.rate_per_second,
                timeout_seconds=self.resilience.timeout_seconds,
                boundary="llm_inference", operation="invoke",
            )

    def ask(
        self, question: str, top_k: int, request_id: str, correlation_id: str | None = None, traceparent: str | None = None
    ) -> tuple[str, list[dict]]:
        output, retrieved, _ = self.ask_with_outcome(question, top_k, request_id, correlation_id, traceparent)
        return output, retrieved

    def ask_with_outcome(
        self, question: str, top_k: int, request_id: str, correlation_id: str | None = None, traceparent: str | None = None
    ) -> tuple[str, list[dict], list[TransactionCompensated]]:
        """Return a safe answer plus any failure events that require audit.

        ``ask`` retains its original two-value return contract for existing
        callers; the API route uses this detailed form to persist the matching
        state transition and immutable compensation record.
        """
        cid = correlation_id or request_id
        store_policy = self.resilience
        llm_policy = self.llm_resilience

        retrieved = []
        retrieval_error = None
        try:
            retrieved = store_policy.call(lambda: self.store.query(question, top_k))
        except Exception as exc:
            retrieval_error = type(exc).__name__
            retrieved = []

        prompt = f"Answer using retrieved evidence only.\nQuestion: {question}\nEvidence: {retrieved}"
        output = os.getenv("RAG_FALLBACK_MESSAGE", "No indexed evidence is available.")
        llm_error = None
        if retrieved and self.llm:
            try:
                output = llm_policy.call(lambda: self.llm.invoke(prompt))
            except Exception as exc:
                llm_error = type(exc).__name__
                output = os.getenv("RAG_FALLBACK_MESSAGE", "No indexed evidence is available.")

        event = TransactionProcessed(
            request_id=request_id,
            correlation_id=cid,
            traceparent=traceparent or "",
            transaction_id=request_id,
            status="compensated" if (retrieval_error or llm_error) else "processed",
            metadata={
                "retrieved_count": len(retrieved),
                "model": type(self.llm).__name__ if self.llm else "fallback",
                "retrieval_error": retrieval_error,
                "llm_error": llm_error,
            },
        )
        if self.publisher:
            self.publisher.publish(event, traceparent=traceparent)

        compensations: list[TransactionCompensated] = []
        for boundary, error in (("retrieval_store", retrieval_error), ("llm_inference", llm_error)):
            if error:
                compensation = TransactionCompensated(
                    correlation_id=cid,
                    causation_id=event.event_id,
                    traceparent=traceparent or "",
                    request_id=request_id,
                    transaction_id=request_id,
                    reason="DOWNSTREAM_FAILURE_FAIL_SAFE",
                    original_event_type=type(event).__name__,
                    error_detail=f"{boundary}:{error}",
                )
                compensations.append(compensation)
                if self.publisher:
                    self.publisher.publish(compensation, traceparent=traceparent)
        return output, retrieved, compensations
