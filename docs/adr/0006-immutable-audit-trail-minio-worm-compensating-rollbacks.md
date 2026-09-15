# ADR-0006: Immutable Audit Trail via MinIO WORM Object Lock & Compensating Rollbacks

## Status
**Accepted**

## Context
When downstream failures occur mid-transaction (e.g. vector ingested but LLM generation fails), state inconsistency arises across storage engines. In compliance-focused and enterprise environments, every state transition must be verifiably immutable and non-repudiable, and failures must trigger compensating rollback events rather than silent drops.

## Decision
We implemented an immutable audit and compensating rollback system:
1. **Explicit State Machine**:
   - Every transaction transitions through deterministic states:
     `TRANSACTION_INITIATED` $\rightarrow$ `DOC_INGESTED` $\rightarrow$ `VECTOR_INDEXED` $\rightarrow$ `INFERENCE_REQUESTED` $\rightarrow$ `INFERENCE_FAILED` (on boundary error) $\rightarrow$ `COMPENSATING_ROLLBACK_TRIGGERED` $\rightarrow$ `COMPENSATED_FINAL`.
2. **MinIO Object Lock / WORM Storage**:
   - Helm post-install Job initializes the `rag-audit-trail` bucket with `mc mb --with-lock` and enables compliance retention (`mc retention set --default COMPLIANCE 30d`).
   - Audit records stored under `audit/{correlation_id}/{sequence_id}_{state}.json` cannot be modified or deleted by any user or API token until the retention period expires.
3. **Cryptographic Checksum Verification**:
   - Each audit payload computes a canonical SHA-256 integrity hash stored in `sha256_checksum`.
4. **Compensating Rollback Triggers**:
   - On boundary failure (timeout or 5xx), a compensating event is dispatched to Kafka topic `rag.events.compensating` carrying binary correlation headers.
   - Downstream consumers (e.g. ChromaDB cleaner, notification service) ingest the compensating event to purge uncommitted embeddings and reconcile cluster state.

## Consequences
### Positive
- Guarantees non-repudiable audit logs compliant with enterprise data governance standards.
- Compensating events prevent orphaned embeddings in ChromaDB when inference fails.
- Cryptographic hashing enables continuous automated integrity audits.

### Negative / Tradeoffs
- Object-locked objects cannot be deleted even by root administrators during local test teardown until retention expires (can use governance mode or dedicated test buckets for dev environments).
