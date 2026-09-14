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
from domain.events import AuditRecordLogged
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
async def pii_boundary(request: Request, call_next):
    """Mark the request as crossing the PII boundary; routes sanitize before adapters."""
    request.state.pii_sanitized = request.method in {"GET", "HEAD", "OPTIONS"}
    return await call_next(request)

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
def ingest(req: IngestRequest, x_request_id: str | None = Header(default=None)) -> dict[str, Any]:
    rid = request_id(x_request_id)
    chunks, counts = ingestion.ingest(req.text, req.source, rid)
    store.add([chunk.chunk_id for chunk in chunks], [chunk.text for chunk in chunks])
    # Integrations are optional at startup and can be enabled by deployment profile.
    payload = {"event": "ingest", "source": req.source, "pii_counts": counts,
               "chunk_count": len(chunks), "chunks": [{"index": i, "text": c.text} for i, c in enumerate(chunks)]}
    try:
        key = audit.write(rid, payload)
    except Exception as exc:
        log.exception("audit_write_failed request_id=%s", rid)
        raise HTTPException(503, "audit sink unavailable") from exc
    publisher.publish(AuditRecordLogged(request_id=rid, object_key=key, record_type="ingest"))
    return {"request_id": rid, "chunks": len(chunks), "audit_key": key}

@app.post("/payments/transactions")
def ingest_payment(req: PaymentRequest, x_request_id: str | None = Header(default=None)) -> dict[str, Any]:
    """Accept only a tokenized payment envelope, never raw cardholder data."""
    rid = request_id(x_request_id)
    event = payment_ingestion.ingest(req.model_dump())
    score = risk_scoring.score(event)
    return {"request_id": rid, "transaction_id": event.transaction_id,
            "risk_score": score.risk_score, "decision": score.decision,
            "model_version": score.model_version}

@app.post("/ask")
def ask(req: AskRequest, x_request_id: str | None = Header(default=None)) -> dict[str, Any]:
    rid = request_id(x_request_id)
    safe_question, _ = redactor.redact(req.question)
    llm = None
    if os.getenv("ENABLE_OLLAMA_INFERENCE", "false").lower() == "true":
        from langchain_ollama import OllamaLLM
        llm = OllamaLLM(
            model=os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"),
        )
    retrieval.llm = llm
    output, retrieved = retrieval.ask(safe_question, req.top_k, rid)
    prompt = f"Answer using retrieved evidence only.\nQuestion: {safe_question}\nEvidence: {retrieved}"
    payload = {"event": "ask", "question": safe_question, "retrieved_chunks": retrieved,
               "prompt": prompt, "output": output}
    try:
        key = audit.write(rid, payload)
    except Exception as exc:
        log.exception("audit_write_failed request_id=%s", rid)
        raise HTTPException(503, "audit sink unavailable") from exc
    publisher.publish(AuditRecordLogged(request_id=rid, object_key=key, record_type="ask"))
    return {"request_id": rid, "answer": output, "retrieved": retrieved, "audit_key": key}
