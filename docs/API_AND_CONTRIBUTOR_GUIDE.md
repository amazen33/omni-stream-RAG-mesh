# API and contributor guide

## Purpose and audience

This is the shareable API contract for clients and the contribution standard
for anyone adding an HTTP entrypoint. The executable source of truth is
`app/main.py`; FastAPI generates the same contract at runtime:

| Resource | Local URL |
| --- | --- |
| Interactive Swagger UI | `http://localhost:8000/docs` |
| ReDoc | `http://localhost:8000/redoc` |
| OpenAPI 3 JSON | `http://localhost:8000/openapi.json` |

In a deployed environment, replace `localhost:8000` with the approved external
API hostname. The WAF and private Istio gateway are the only supported
production ingress path. Do not expose the application service, Swagger UI, or
metrics endpoint directly to the Internet.

The application does **not** implement end-user authentication or authorization
itself. A production platform must enforce those controls at the identity-aware
edge and apply its approved authorization policy before forwarding a request.

## Common protocol contract

All business endpoints consume JSON and return JSON. Send
`Content-Type: application/json` for request bodies.

### Request correlation and tracing

The middleware ignores any caller-supplied tracing headers and issues all three
authoritative server values on every response:

| Header | Meaning | When omitted |
| --- | --- | --- |
| `X-Request-ID` | Ignored if supplied | A new server UUID is issued |
| `X-Correlation-ID` | Ignored if supplied | A new server UUID is issued |
| `traceparent` | Ignored if supplied | A new server W3C trace is issued |

Clients do not control or continue server correlation through headers. The
service creates a new UUID request ID and correlation ID plus a new W3C trace
for each request, and stores only those server-issued values in audit and event
records. Treat returned values as authoritative for logs, support tickets, and
downstream calls. Do not put customer data, credentials, tenant names, or other
sensitive values in headers.

The service adds `correlation_id` and `request_id` to successful business
responses. Internal domain events also carry immutable `event_id`,
`correlation_id`, `causation_id`, and `traceparent`; Kafka headers mirror the
safe correlation fields when Kafka is enabled.

### Validation and failures

FastAPI returns `422 Unprocessable Entity` for a malformed JSON body or a value
outside the documented input limits. The standard body contains a `detail`
array. Clients must not retry a `422` unchanged.

The application intentionally reports only safe error detail. Typical failures
are:

| Status | Meaning | Client action |
| --- | --- | --- |
| `500` | Unexpected ingestion failure | Preserve correlation headers; retry only through an approved idempotency/replay process |
| `502` | A required processing dependency failed | Retry with bounded backoff after investigating the downstream dependency |
| `503` | Audit or readiness dependency is unavailable | Treat as temporarily unavailable; retry with bounded backoff |

No HTTP endpoint currently accepts an idempotency key. A caller that retries a
write must account for possible duplicate ingestion/event delivery; contributors
must not claim exactly-once behavior without a durable idempotency design.

## Business API

### `POST /ingest-sample`

Redacts a document, chunks the sanitized content, indexes it in the configured
retrieval store, and writes a sanitized audit record. It may publish a
`TelemetryIngested` event when Kafka is enabled.

| Field | Type and constraints | Required | Description |
| --- | --- | --- | --- |
| `text` | string, 1–200,000 characters | Yes | Source text. Recognised PII becomes canonicalized 128-bit HMAC tokens before downstream processing. |
| `source` | string | No; default `sample` | Raw only at ingress; HMAC-tokenized before vector metadata, telemetry, events, or audit. |

```bash
curl --fail-with-body -X POST http://localhost:8000/ingest-sample \
  -H 'Content-Type: application/json' \
  -d '{"text":"Revenue was $42.00.","source":"demo"}'
```

Successful response (`200`):

```json
{
  "request_id": "b735c2ae-84c8-4cf9-b362-7cbe6a9f3dc1",
  "correlation_id": "7c22d5e9-ecae-4c55-9f1e-719ac9ac24d7",
  "chunks": 1,
  "audit_key": "audit/2026/09/20/b735c2ae-84c8-4cf9-b362-7cbe6a9f3dc1.json"
}
```

`502` means the vector store write failed; `503` means the audit write failed.
The success response is issued only after both operations succeed.

### `POST /ask`

Redacts the question, retrieves sanitized evidence, optionally invokes the
configured Ollama model, and writes an audit record. Retrieval/model failures
use a safe fallback result when the resilience policy can compensate; an audit
write failure returns `503`.

| Field | Type and constraints | Required | Description |
| --- | --- | --- | --- |
| `question` | string, 1–10,000 characters | Yes | Question to answer from indexed evidence. |
| `top_k` | integer, 1–20 | No; default `4` | Maximum number of retrieved chunks. |

```bash
curl --fail-with-body -X POST http://localhost:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"What revenue was reported?","top_k":4}'
```

Successful response (`200`):

```json
{
  "request_id": "b735c2ae-84c8-4cf9-b362-7cbe6a9f3dc1",
  "correlation_id": "7c22d5e9-ecae-4c55-9f1e-719ac9ac24d7",
  "answer": "...",
  "retrieved": ["..."],
  "audit_key": "audit/2026/09/20/b735c2ae-84c8-4cf9-b362-7cbe6a9f3dc1.json"
}
```

Answers are not a system-of-record decision or a compliance finding. Callers
must assess retrieved evidence and add their own authorization, review, and
retention controls.

### `POST /payments/transactions`

Accepts an identifier envelope at the designated RAG ingress, HMAC-tokenizes
the transaction and merchant identifiers before an event/audit/downstream
boundary, and returns the current deterministic risk decision. Never send a
PAN, CVV, PIN, authentication secret, or raw cardholder data to this endpoint.

| Field | Type and constraints | Required | Description |
| --- | --- | --- | --- |
| `transaction_id` | string, 1–128 characters | Yes | Caller reference; converted to `transaction_token` before it leaves the RAG ingress layer. |
| `merchant_id` | string, 1–128 characters | Yes | Caller reference; HMAC-tokenized before event/audit/downstream use. |
| `amount_minor` | integer, minimum `0` | Yes | Amount in the currency's minor unit. |
| `currency` | string, exactly 3 characters | Yes | ISO-style currency code. |
| `payment_network` | string, maximum 32 characters | No; default `unknown` | Network classification. |

```bash
curl --fail-with-body -X POST http://localhost:8000/payments/transactions \
  -H 'Content-Type: application/json' \
  -d '{"transaction_id":"txn-token-123","merchant_id":"merchant-9","amount_minor":4200,"currency":"USD"}'
```

Successful response (`200`):

```json
{
  "request_id": "b735c2ae-84c8-4cf9-b362-7cbe6a9f3dc1",
  "correlation_id": "7c22d5e9-ecae-4c55-9f1e-719ac9ac24d7",
  "transaction_token": "<PII_PAYMENT_TRANSACTION_V1_...>",
  "risk_score": 0.12,
  "decision": "allow",
  "model_version": "baseline-v1"
}
```

The current scoring implementation is a deterministic baseline, not a trained
fraud model or a payment authorization system. A scoring failure is designed to
fail closed to review where supported; `502` indicates unavailable processing.

## Operational endpoints

| Endpoint | Intended audience | Semantics |
| --- | --- | --- |
| `GET /health/live` and `GET /healthz` | Orchestrator liveness probe | Process-only check; it must not call dependencies. |
| `GET /health/ready`, `GET /readyz` | Orchestrator readiness probe | Dependency-aware report; returns `503` when not ready. |
| `GET /health/startup` | Orchestrator startup probe | Startup dependency report; returns `503` when not ready. |
| `GET /metrics` | Authenticated/internal Prometheus scraper | Prometheus text exposition with bounded-cardinality resilience metrics. |

These endpoints are not a public business API. Restrict them with the platform
network policy and monitoring authorization model.

## Adding or changing an API entrypoint

1. Start from the public contract: choose a resource-oriented path, HTTP method,
   Pydantic request model, success response, errors, ownership, and backward
   compatibility plan before implementation.
2. Keep user-provided material behind the redaction boundary. Deterministically
   HMAC-tokenize any identifier used for retrieval before it reaches a vector
   store, event, audit record, or external adapter. Do not log or publish raw
   PII, secrets, prompts containing PII, stack traces, or data in metric labels.
3. Return the standard **server-issued** correlation headers. Use `request_context`,
   record the `INITIALIZED → PROCESSING → COMPLETED` or `COMPENSATED` lifecycle,
   and publish a compensating event if a side effect can fail after partial work.
4. Define downstream timeouts, bulkhead/rate limits, safe fallback behavior,
   and retry/idempotency semantics. A compensation record describes a failure;
   it does not reverse an already completed external side effect.
5. Add route summaries, descriptions, field constraints, and safe examples so
   `/openapi.json` remains useful for generated clients. Add API tests for
   validation, success, safe failure, and returned tracing headers.
6. Preserve existing response fields and meanings. Additive fields are usually
   compatible; renamed/removed fields, changed meanings, or Kafka topic changes
   require a versioned migration agreed with consumers.
7. Update this guide and the architecture/operations guide in the same change,
   then run `python -m pytest -q`.

Do not add an endpoint that bypasses the edge gateway, the default-deny network
policy, audit requirements, or the selected SPIFFE/Istio workload identity.
