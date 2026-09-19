from __future__ import annotations
import logging, os, uuid
from typing import Any, List
from fastapi import FastAPI, Header, HTTPException, Request, Response
from pydantic import BaseModel, Field
from .redaction import redact
from .audit import AuditSink
from .storage import RetrievalStore
from .redaction import PIIRedactor
from contexts.ingestion import IngestionService
from contexts.ai import RetrievalService
from contexts.governance import EventPublisher, NullPublisher
from contexts.payments import PaymentIngestionService, RiskScoringService
from domain.events import (
    AuditRecordLogged,
    IngestionCompensated,
    StateTransitionLogged,
    TransactionCompensated,
)
from .health import HealthService
from .metrics import exposition

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(message)s")
log = logging.getLogger("rag")
app = FastAPI(title="Hybrid Cloud Streaming RAG", version="1.0.0")
audit = AuditSink()
store = RetrievalStore()
publisher = EventPublisher() if os.getenv("ENABLE_KAFKA", "false").lower() == "true" else NullPublisher()
redactor = PIIRedactor(os.getenv("PII_TOKEN_SALT", "change-me"))
ingestion = IngestionService(redactor, publisher)
retrieval = RetrievalService(store, publisher=publisher)
payment_ingestion = PaymentIngestionService(publisher=publisher)
risk_scoring = RiskScoringService(publisher=publisher)
health = HealthService()


@app.middleware("http")
async def request_boundary(request: Request, call_next):
    """Establish immutable request tracing before data enters a route."""
    request.state.pii_sanitized = request.method in {"GET", "HEAD", "OPTIONS"}
    request.state.request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.correlation_id = request.headers.get("x-correlation-id") or str(
        uuid.uuid5(uuid.NAMESPACE_URL, f"omni-stream-rag:{request.state.request_id}")
    )
    request.state.traceparent = request.headers.get("traceparent") or (
        f"00-{uuid.uuid4().hex}-{uuid.uuid4().hex[:16]}-01"
    )
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Correlation-ID"] = request.state.correlation_id
    response.headers["traceparent"] = request.state.traceparent
    return response

class IngestRequest(BaseModel):
    text: str = Field(min_length=1, max_length=200000)
    source: str = "sample"

class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=10000)
    top_k: int = Field(default=4, ge=1, le=20)

class PaymentRequest(BaseModel):
    transaction_id: str = Field(min_length=1, max_length=128)
    merchant_id: str = Field(min_length=1, max_length=128)
    amount_minor: int = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    payment_network: str = Field(default="unknown", max_length=32)

def request_id(value: str | None) -> str:
    return value or str(uuid.uuid4())

def correlation_id(value: str | None, rid: str) -> str:
    return value or str(uuid.uuid5(uuid.NAMESPACE_URL, f"omni-stream-rag:{rid}"))


def request_context(
    request: Request, x_request_id: str | None, x_correlation_id: str | None, traceparent: str | None
) -> tuple[str, str, str]:
    """Prefer explicit headers while retaining the middleware's one-request context."""
    rid = request_id(x_request_id or getattr(request.state, "request_id", None))
    cid = correlation_id(x_correlation_id or getattr(request.state, "correlation_id", None), rid)
    trace = traceparent or getattr(request.state, "traceparent", "")
    return rid, cid, trace


def record_transition(
    correlation: str,
    request: str,
    state_from: str,
    state_to: str,
    reason: str,
    traceparent: str,
    payload: dict[str, Any] | None = None,
) -> None:
    """Persist and publish a transition without hiding the primary failure."""
    try:
        audit.write_state_transition(correlation, state_from, state_to, reason, payload)
    except Exception:
        log.exception("state_transition_audit_failed correlation_id=%s", correlation)
    publisher.publish(
        StateTransitionLogged(
            correlation_id=correlation,
            traceparent=traceparent,
            request_id=request,
            entity_id=request,
            state_from=state_from,
            state_to=state_to,
            reason=reason,
            payload=payload or {},
        ),
        traceparent=traceparent,
    )


def record_compensation(correlation: str, record: dict[str, Any]) -> None:
    try:
        audit.write_compensation(correlation, record)
    except Exception:
        log.exception("compensation_audit_failed correlation_id=%s", correlation)

def _chunks(text: str, size: int = 800, overlap: int = 120) -> List[str]:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(chunk_size=size, chunk_overlap=overlap)
    return splitter.split_text(text)

def _health_response(phase: str, response: Response) -> dict[str, object]:
    report = health.report(phase)
    if report["status"] != "ok":
        response.status_code = 503
    return report


@app.get("/health/live")
def health_live() -> dict[str, object]:
    # Liveness must never perform network or dependency work.
    return health.report("live")


@app.get("/health/ready")
def health_ready(response: Response) -> dict[str, object]:
    return _health_response("ready", response)


@app.get("/health/startup")
def health_startup(response: Response) -> dict[str, object]:
    return _health_response("startup", response)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    # Keep the original lightweight compatibility contract for existing clients.
    return {"status": "ok"}

@app.get("/readyz")
def readyz(response: Response) -> dict[str, object]:
    return _health_response("ready", response)


@app.get("/metrics")
def metrics() -> Response:
    return Response(exposition(), media_type="text/plain; version=0.0.4")

@app.post("/ingest-sample")
def ingest(
    req: IngestRequest,
    request: Request,
    x_request_id: str | None = Header(default=None),
    x_correlation_id: str | None = Header(default=None),
    traceparent: str | None = Header(default=None),
) -> dict[str, Any]:
    rid, cid, trace = request_context(request, x_request_id, x_correlation_id, traceparent)
    record_transition(cid, rid, "INITIALIZED", "PROCESSING", "Received document for ingestion", trace, {"source": req.source})
    try:
        chunks, counts = ingestion.ingest(req.text, req.source, rid, correlation_id=cid, traceparent=trace)
        try:
            store.add([chunk.chunk_id for chunk in chunks], [chunk.text for chunk in chunks])
        except Exception as exc:
            log.exception("store_add_failed request_id=%s correlation_id=%s", rid, cid)
            error = type(exc).__name__
            record_transition(cid, rid, "PROCESSING", "COMPENSATED", "Vector store write failed", trace)
            record_compensation(cid, {"boundary": "retrieval_store", "reason": "STORE_ADD_FAILED", "request_id": rid, "error": error})
            publisher.publish(
                IngestionCompensated(correlation_id=cid, traceparent=trace, request_id=rid, source=req.source,
                                     reason="STORE_ADD_FAILED", error_detail=error), traceparent=trace,
            )
            raise HTTPException(502, "vector store indexing failed") from exc

        payload = {"event": "ingest", "source": req.source, "pii_counts": counts,
                   "chunk_count": len(chunks), "chunks": [{"index": i, "text": c.text} for i, c in enumerate(chunks)]}
        try:
            key = audit.write(rid, {**payload, "traceparent": trace}, correlation_id=cid)
        except Exception as exc:
            log.exception("audit_write_failed request_id=%s correlation_id=%s", rid, cid)
            record_transition(cid, rid, "PROCESSING", "COMPENSATED", "Audit persistence failed", trace)
            record_compensation(cid, {"boundary": "audit_sink", "reason": "AUDIT_WRITE_FAILED", "request_id": rid, "error": type(exc).__name__})
            publisher.publish(
                IngestionCompensated(correlation_id=cid, traceparent=trace, request_id=rid, source=req.source,
                                     reason="AUDIT_WRITE_FAILED", error_detail="audit sink unavailable"), traceparent=trace,
            )
            raise HTTPException(503, "audit sink unavailable") from exc

        record_transition(cid, rid, "PROCESSING", "COMPLETED", "Ingestion completed successfully", trace, {"audit_key": key})
        publisher.publish(AuditRecordLogged(request_id=rid, correlation_id=cid, traceparent=trace, object_key=key, record_type="ingest"), traceparent=trace)
        return {"request_id": rid, "correlation_id": cid, "chunks": len(chunks), "audit_key": key}
    except HTTPException:
        raise
    except Exception as exc:
        error = type(exc).__name__
        record_transition(cid, rid, "PROCESSING", "COMPENSATED", "Unhandled ingestion failure", trace)
        record_compensation(cid, {"boundary": "ingestion", "reason": "UNHANDLED_FAILURE", "request_id": rid, "error": error})
        publisher.publish(
            IngestionCompensated(correlation_id=cid, traceparent=trace, request_id=rid, source=req.source,
                                 reason="UNHANDLED_FAILURE", error_detail=error), traceparent=trace,
        )
        raise HTTPException(500, "internal ingestion failure") from exc

@app.post("/payments/transactions")
def ingest_payment(
    req: PaymentRequest,
    request: Request,
    x_request_id: str | None = Header(default=None),
    x_correlation_id: str | None = Header(default=None),
    traceparent: str | None = Header(default=None),
) -> dict[str, Any]:
    """Accept only a tokenized payment envelope, never raw cardholder data."""
    rid, cid, trace = request_context(request, x_request_id, x_correlation_id, traceparent)
    record_transition(cid, rid, "INITIALIZED", "PROCESSING", "Payment transaction received", trace, {"merchant_id": req.merchant_id})
    try:
        event = payment_ingestion.ingest(req.model_dump(), correlation_id=cid, traceparent=trace)
        score = risk_scoring.score(event, traceparent=trace)
    except Exception as exc:
        error = type(exc).__name__
        record_transition(cid, rid, "PROCESSING", "COMPENSATED", "Payment ingestion failed", trace)
        record_compensation(cid, {"boundary": "payment_ingestion", "reason": "UNHANDLED_FAILURE", "request_id": rid, "error": error})
        raise HTTPException(502, "payment processing unavailable") from exc

    if score.failure_reason:
        record_transition(cid, rid, "PROCESSING", "COMPENSATED", "Risk scoring failed closed", trace)
        record_compensation(cid, {"boundary": "payment_risk_scoring", "reason": score.failure_reason, "request_id": rid, "transaction_id": event.transaction_id})
    else:
        record_transition(cid, rid, "PROCESSING", "COMPLETED", f"Decision: {score.decision}", trace, {"risk_score": score.risk_score, "decision": score.decision})
    return {"request_id": rid, "correlation_id": cid, "transaction_id": event.transaction_id,
            "risk_score": score.risk_score, "decision": score.decision,
            "model_version": score.model_version}

@app.post("/ask")
def ask(
    req: AskRequest,
    request: Request,
    x_request_id: str | None = Header(default=None),
    x_correlation_id: str | None = Header(default=None),
    traceparent: str | None = Header(default=None),
) -> dict[str, Any]:
    rid, cid, trace = request_context(request, x_request_id, x_correlation_id, traceparent)
    record_transition(cid, rid, "INITIALIZED", "PROCESSING", "Question received for retrieval", trace)
    safe_question, _ = redactor.redact(req.question)
    llm = None
    if os.getenv("ENABLE_OLLAMA_INFERENCE", "false").lower() == "true":
        from langchain_ollama import OllamaLLM
        llm = OllamaLLM(
            model=os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"),
        )
    retrieval.llm = llm
    output, retrieved, compensations = retrieval.ask_with_outcome(
        safe_question, req.top_k, rid, correlation_id=cid, traceparent=trace
    )
    prompt = f"Answer using retrieved evidence only.\nQuestion: {safe_question}\nEvidence: {retrieved}"
    payload = {"event": "ask", "question": safe_question, "retrieved_chunks": retrieved,
               "prompt": prompt, "output": output, "traceparent": trace,
               "compensations": [event.to_dict() for event in compensations]}
    for event in compensations:
        record_compensation(cid, {"boundary": event.error_detail.split(":", 1)[0], "reason": event.reason,
                                  "request_id": rid, "event": event.to_dict()})
    try:
        key = audit.write(rid, payload, correlation_id=cid)
    except Exception as exc:
        log.exception("audit_write_failed request_id=%s correlation_id=%s", rid, cid)
        record_transition(cid, rid, "PROCESSING", "COMPENSATED", "Audit persistence failed", trace)
        record_compensation(cid, {"boundary": "audit_sink", "reason": "AUDIT_WRITE_FAILED", "request_id": rid, "error": type(exc).__name__})
        publisher.publish(
            TransactionCompensated(correlation_id=cid, traceparent=trace, request_id=rid, transaction_id=rid,
                                   reason="AUDIT_WRITE_FAILED", error_detail="audit sink unavailable"), traceparent=trace,
        )
        raise HTTPException(503, "audit sink unavailable") from exc
    if compensations:
        record_transition(cid, rid, "PROCESSING", "COMPENSATED", "Retrieval returned a safe fallback", trace, {"audit_key": key})
    else:
        record_transition(cid, rid, "PROCESSING", "COMPLETED", "Retrieval and inference completed", trace, {"audit_key": key})
    publisher.publish(AuditRecordLogged(request_id=rid, correlation_id=cid, traceparent=trace, object_key=key, record_type="ask"), traceparent=trace)
    return {"request_id": rid, "correlation_id": cid, "answer": output, "retrieved": retrieved, "audit_key": key}
