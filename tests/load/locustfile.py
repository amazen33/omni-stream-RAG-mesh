"""Omni B0 load scenarios (OMNI-WO-00 Part B, step B2).

Every response is classified into the five outcome classes of
omni/QOS-CHARTER.md section 2.1. Run from the repository root:
    python -m locust -f tests/load/locustfile.py --host http://127.0.0.1:8000
"""
from __future__ import annotations

import logging
import os
import random      
import time
from enum import Enum
from itertools import count
from typing import Any

from locust import HttpUser, constant_throughput, events, task
from locust.env import Environment
from locust.exception import StopTest

import requests

from ops.synthetic_corpus import generate_corpus

SEED = int(os.environ.get("QOS_SEED", "20261101"))
CORPUS_COUNT = int(os.environ.get("QOS_CORPUS_COUNT", "50"))
if not 1 <= CORPUS_COUNT <= 50:
    raise ValueError("QOS_CORPUS_COUNT must be between 1 and 50 to avoid memory-store eviction")
CORPUS = generate_corpus(SEED, count=CORPUS_COUNT)



J2_RNG = random.Random(SEED + 2)

    
J2_USED_MARKERS = {
    str(item["question"]).split()[3].rstrip(",")
    for item in CORPUS["questions"]
}


def make_j2_document() -> tuple[str, dict[str, str], dict[str, object]]:
    """Return (marker, document, question) for one new J2 document."""
    while True:
        marker = "".join(J2_RNG.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(16))
        if marker not in J2_USED_MARKERS:
            J2_USED_MARKERS.add(marker)
            break

    prefix = f"Synthetic document {marker}. The sample parcel is violet. "
    vocabulary = (
        "synthetic", "sample", "parcel", "inventory",
        "orbit", "harbor", "ledger", "violet",
    )
    padding = " ".join(
        J2_RNG.choice(vocabulary) for _ in range(1024 // 4 + 1)
    )
    document = {
        "source": f"synthetic-j2-{marker}",
        "text": (prefix + padding)[:1024],
    }
    question = {
        "question": f"In synthetic document {marker}, what color is the sample parcel?",
        "top_k": 4,
    }
    return marker, document, question




log = logging.getLogger(__name__)
REQUEST_TIMEOUT_SECONDS = 30
REJECTION_STATUSES = frozenset({400, 401, 403, 404, 409, 413, 422})

SEARCH_DEADLINE_SECONDS = float(os.environ.get("QOS_J2_SEARCH_DEADLINE_SECONDS", "10"))
SEARCH_POLL_SECONDS = 0.25

class Outcome(str, Enum):
    """The five outcome classes of QOS-CHARTER section 2.1."""

    CORRECT = "1-correct-outcome"
    REJECTION = "2-correct-rejection"
    DEGRADED = "3-degraded"
    TECHNICAL_FAILURE = "4-technical-failure"
    INCORRECT = "5-incorrect-result"

    @property
    def counts_as_success(self) -> bool:
        return self in (Outcome.CORRECT, Outcome.REJECTION)


def record_outcome(environment: Environment, journey: str, outcome: Outcome, elapsed_ms: float) -> None:
    """Add one report row per journey and class, so p50/p95/p99 come out per class."""
    environment.events.request.fire(
        request_type="OUTCOME",
        name=f"{journey} {outcome.value}",
        response_time=elapsed_ms,
        response_length=0,
        response=None,
        context={},
        exception=None,
    )


def classify_status(status_code: int) -> Outcome | None:
    """Classes decided by the HTTP status alone. None means: read the body."""
    if status_code == 0 or status_code >= 500 or status_code in (408, 429):
        return Outcome.TECHNICAL_FAILURE  # 0 means a timeout or a connection failure
    if status_code in REJECTION_STATUSES:
        return Outcome.REJECTION
    if 200 <= status_code < 300:
        return None
    return Outcome.TECHNICAL_FAILURE  # any other status is unexpected for these APIs


def classify_payment(status_code: int, body: dict[str, Any] | None) -> Outcome:
    """J1: the synthetic payments are below the review threshold, so 'allow' is correct."""
    by_status = classify_status(status_code)
    if by_status is not None:
        return by_status
    decision = (body or {}).get("decision")
    if decision == "allow":
        return Outcome.CORRECT
    if decision == "review":
        return Outcome.TECHNICAL_FAILURE  # Omni could not decide (it failed closed)
    return Outcome.INCORRECT


def classify_ask_text(status_code: int, body: dict[str, Any] | None, marker: str) -> Outcome:
    """J3: the same retrieved chunk must contain the expected marker and fact."""
    by_status = classify_status(status_code)
    if by_status is not None:
        return by_status
    if not isinstance(body, dict) or not marker:
        return Outcome.INCORRECT
    retrieved = body.get("retrieved")
    if not isinstance(retrieved, list):
        return Outcome.INCORRECT
    for chunk in retrieved:
        text = chunk.get("text") if isinstance(chunk, dict) else None
        if isinstance(text, str) and marker in text and "violet" in text.lower():
            return Outcome.CORRECT
    return Outcome.INCORRECT

def classify_ingest_ack(status_code: int, body: dict[str, Any] | None) -> Outcome:
    """J2 acknowledgement: 2xx with at least one stored chunk and an audit key."""
    by_status = classify_status(status_code)
    if by_status is not None:
        return by_status
    if not isinstance(body, dict):
        return Outcome.INCORRECT
    chunks = body.get("chunks")
    if isinstance(chunks, int) and chunks >= 1 and body.get("audit_key"):
        return Outcome.CORRECT
    return Outcome.INCORRECT


@events.test_start.add_listener
def load_ask_documents(environment: Environment, **_kwargs: Any) -> None:
    """Prepare J3 once, outside request statistics; abort if any ingest fails."""
    if not any(issubclass(user_class, AskTextUser) for user_class in environment.user_classes):
        return
    documents = CORPUS["documents"]
    loaded = 0
    chunks = 0
    status_code = None
    environment.qos_setup = {"seed": SEED, "count_per_size": CORPUS_COUNT, "loaded": 0, "status": "failed"}
    try:
        if not environment.host:
            raise ValueError("J3 setup requires --host")
        with requests.Session() as session:
            for document in documents:
                status_code = None
                response = session.post(
                    environment.host.rstrip("/") + "/ingest-sample",
                    json=document,
                    timeout=REQUEST_TIMEOUT_SECONDS,
                    allow_redirects=False,
                )
                status_code = response.status_code
                if not 200 <= status_code < 300:
                    raise ValueError("Ingestion did not return 2xx")
                body = response.json()
                chunk_count = body.get("chunks") if isinstance(body, dict) else None
                if not isinstance(chunk_count, int) or chunk_count < 1 or not body.get("audit_key"):
                    raise ValueError("Ingestion acknowledgement is incomplete")
                loaded += 1
                chunks += chunk_count
                environment.qos_setup["loaded"] = loaded
    except (requests.RequestException, ValueError) as error:
        log.error(
            "J3 loading failed: seed=%s count_per_size=%s loaded=%s/%s next_document=%s status=%s error=%s",
            SEED, CORPUS_COUNT, loaded, len(documents), loaded + 1, status_code, type(error).__name__,
        )
        environment.process_exit_code = 1
        raise StopTest("J3 document loading failed; aborting before requests") from error
    environment.qos_setup.update(status="succeeded", chunks=chunks)
    log.info(
        "J3 loading succeeded: seed=%s count_per_size=%s documents=%s chunks=%s",
        SEED, CORPUS_COUNT, loaded, chunks,
    )


class PaymentDecisionUser(HttpUser):
    """J1: get a payment decision."""

    wait_time = constant_throughput(float(os.environ.get("QOS_J1_RPS_PER_USER", "1")))
    _sequence = count()

    @task
    def decide(self) -> None:
        payments = CORPUS["payments"]
        payload = payments[next(self._sequence) % len(payments)]
        started = time.perf_counter()
        with self.client.post(
            "/payments/transactions",
            json=payload,
            name="J1 POST /payments/transactions",
            timeout=REQUEST_TIMEOUT_SECONDS,
            catch_response=True,
        ) as response:
            elapsed_ms = (time.perf_counter() - started) * 1000
            try:
                body = response.json() if 200 <= response.status_code < 300 else None
            except ValueError:
                body = None
            outcome = classify_payment(response.status_code, body)
            if outcome.counts_as_success:
                response.success()
            else:
                response.failure(outcome.value)
        record_outcome(self.environment, "J1", outcome, elapsed_ms)

class AskTextUser(HttpUser):
    """J3: retrieve the known synthetic fact with inference disabled on Omni."""

    wait_time = constant_throughput(float(os.environ.get("QOS_J3_RPS_PER_USER", "1")))
    _sequence = count()

    @task
    def ask_text(self) -> None:
        questions = CORPUS["questions"]
        payload = questions[next(self._sequence) % len(questions)]
        marker = payload["question"].split()[3].rstrip(",")
        started = time.perf_counter()
        with self.client.post(
            "/ask",
            json=payload,
            name="J3 POST /ask",
            timeout=REQUEST_TIMEOUT_SECONDS,
            catch_response=True,
        ) as response:
            elapsed_ms = (time.perf_counter() - started) * 1000
            try:
                body = response.json() if 200 <= response.status_code < 300 else None
            except ValueError:
                body = None
            outcome = classify_ask_text(response.status_code, body, marker)
            if outcome.counts_as_success:
                response.success()
            else:
                response.failure(outcome.value)
        record_outcome(self.environment, "J3", outcome, elapsed_ms)

class IngestSearchUser(HttpUser):
    """J2: an ingest acknowledgement, then the time until /ask finds the new document (Q-6)."""

    wait_time = constant_throughput(float(os.environ.get("QOS_J2_RPS_PER_USER", "1")))

    @task
    def ingest_then_search(self) -> None:
        marker, document, question = make_j2_document()
        if self.ingest(document) is Outcome.CORRECT:
            self.wait_until_searchable(marker, question)

    def ingest(self, document: dict[str, str]) -> Outcome:
        started = time.perf_counter()
        with self.client.post(
            "/ingest-sample",
            json=document,
            name="J2 POST /ingest-sample",
            timeout=REQUEST_TIMEOUT_SECONDS,
            catch_response=True,
        ) as response:
            elapsed_ms = (time.perf_counter() - started) * 1000
            try:
                body = response.json() if 200 <= response.status_code < 300 else None
            except ValueError:
                body = None
            outcome = classify_ingest_ack(response.status_code, body)
            if outcome.counts_as_success:
                response.success()
            else:
                response.failure(outcome.value)
        record_outcome(self.environment, "J2-ack", outcome, elapsed_ms)
        return outcome

    def wait_until_searchable(self, marker: str, question: dict[str, object]) -> None:
        """Ask until the document is found or the deadline passes; not found in time is class 5."""
        started = time.perf_counter()
        deadline = started + SEARCH_DEADLINE_SECONDS
        while True:
            with self.client.post(
                "/ask",
                json=question,
                name="J2 POST /ask (search)",
                timeout=REQUEST_TIMEOUT_SECONDS,
                catch_response=True,
            ) as response:
                try:
                    body = response.json() if 200 <= response.status_code < 300 else None
                except ValueError:
                    body = None
                outcome = classify_ask_text(response.status_code, body, marker)
                if outcome is Outcome.TECHNICAL_FAILURE:
                    response.failure(outcome.value)
                else:
                    response.success()  # "not found yet" is normal while waiting
            if outcome is not Outcome.INCORRECT or time.perf_counter() >= deadline:
                break
            time.sleep(SEARCH_POLL_SECONDS)  # Locust patches sleep, so other users keep running
        elapsed_ms = (time.perf_counter() - started) * 1000
        record_outcome(self.environment, "J2-search", outcome, elapsed_ms)
