from __future__ import annotations
from dataclasses import dataclass
import os
from domain.events import TransactionProcessed


@dataclass
class RetrievalService:
    store: object
    llm: object | None = None
    publisher: object | None = None

    def ask(self, question: str, top_k: int, request_id: str) -> tuple[str, list[dict]]:
        retrieved = self.store.query(question, top_k)
        prompt = f"Answer using retrieved evidence only.\nQuestion: {question}\nEvidence: {retrieved}"
        output = os.getenv("RAG_FALLBACK_MESSAGE", "No indexed evidence is available.")
        if retrieved and self.llm:
            output = self.llm.invoke(prompt)
        event = TransactionProcessed(
            request_id=request_id, transaction_id=request_id,
            metadata={"retrieved_count": len(retrieved), "model": type(self.llm).__name__ if self.llm else "fallback"},
        )
        if self.publisher:
            self.publisher.publish(event)
        return output, retrieved
