# Claude Code Project Contract

## Purpose and status

This repository is the source of truth for the Hybrid Streaming RAG reference
implementation. The IoT modernization programme described below is a planned
product evolution; a milestone is **not implemented** until its code,
deployment artifacts, tests, and documentation are present in this repository
and its acceptance gate has passed.

Read `README.md`, `ARD.md`, and the four consolidated documents under `docs/`
before making a change. Do not create additional architecture, C4, TOGAF, or
API documentation files: update the appropriate existing document instead.

## Non-negotiable engineering rules

- Preserve tenant isolation and bounded-context ownership. Do not introduce a
  shared cross-domain database.
- APISIX is the north-south HTTP/gRPC/WebSocket gateway; MQTT brokers carry
  device traffic; Kafka carries internal events; ThingsBoard CE is a
  compatibility rules component, not the platform source of truth.
- Do not put secrets, raw PII, payment data, private keys, device credentials,
  or production exports in source code, Git, event payloads, logs, metrics,
  prompts, or test fixtures. Store a submitted secret directly in the
  configured vault and persist only a secret reference and non-sensitive
  validation metadata.
- Use server-issued correlation IDs and preserve causation/idempotency data.
  Event contracts are versioned, additive by default, and tested for
  compatibility.
- Firmware artifacts are signed, verified by the device, compatible with the
  target hardware, and delivered by HTTPS/object storage or the supported
  device transport. WebSockets report rollout progress; they do not carry the
  firmware binary.
- Never run a destructive command, apply infrastructure, deploy, rotate a
  production secret, or bypass a test/policy gate without explicit human
  approval. Do not claim cloud, compliance, DR, or migration completion based
  solely on local tests.

## Claude Code working method

For every task, first inspect the affected code, tests, API contract, and
architecture document. State the bounded context, non-goals, acceptance
criteria, data classification, and rollback impact before editing. Make the
smallest coherent change, add or update tests in the same change, run the full
applicable gate, and report exact commands and results.

Use this prompt frame for implementation tasks. Replace every bracketed item;
do not silently expand the scope.

```text
<role>
You are the implementation engineer for the Omni Stream modernization.
</role>
<stage>[MILESTONE ID AND NAME]</stage>
<scope>[bounded context, files, and user outcome]</scope>
<non_goals>[what must not change]</non_goals>
<security>
No raw PII, secrets, private keys, device credentials, or production data in
source, events, logs, tests, or assistant output. Use vault references and
server-issued correlation IDs.
</security>
<acceptance_criteria>[observable behaviour and contracts]</acceptance_criteria>
<tests>[stage-specific tests plus the full gate below]</tests>
<deliverables>[code, tests, manifests, API/doc/ADR updates]</deliverables>
<completion_rule>
Do not mark the task complete until every applicable test passes. If a test
cannot run, report the exact blocker and do not claim the milestone passed.
</completion_rule>
```

For a review task, replace `<role>` with `independent reviewer`; require a
finding with file/line evidence for every defect, and require verification that
the implementation did not bypass tenant, vault, event, or rollout controls.

## Product milestones and required test gates

All stages are sequential unless an ADR explicitly documents a safe parallel
workstream. A full regression gate is mandatory after every implementation
stage, even when the stage-specific tests pass.

| Milestone | Product outcome | Stage-specific acceptance and tests |
| --- | --- | --- |
| M0 — Foundation | Governed repository and deployable development baseline. | Architecture boundaries, API/event conventions, vault-reference interface, CI policy, synthetic fixtures, and an explicit local profile exist. Test auth/error handling, secret non-persistence, lint, manifests, and full regression. |
| M1 — Migration Studio foundation | Operators can register a legacy source, save a vault reference, inventory data/rules/reports, and preview mappings without importing production records. | Test RBAC, vault-reference-only persistence, source fingerprinting, dry-run/approval workflow, audit facts, and failed connection handling. |
| M2 — IoT domain core | Tenant, customer, device, asset/tank, location, device profile, and lifecycle APIs/read models exist. | Test tenant boundary denial, entity hierarchy, validation, API compatibility, lifecycle transitions, and projection rebuild from synthetic events. |
| M3 — Ingestion, eventing, and rules migration | Legacy Mosquitto mirroring and PostgreSQL backfill flow through a canonical outbox/Kafka contract; ThingsBoard receives telemetry and emits rule outcomes for shadow comparison. | Test duplicate/out-of-order data, reconnect/replay, idempotency, schema compatibility, outbox recovery, legacy/new rule parity, and command-side-effect suppression in shadow mode. |
| M4 — Operator experience and reports | APISIX-protected APIs, SSR UI/BFF, tenant-filtered WebSocket updates, and report import/rebuild/approval are available. | Test authorization on REST/WSS, reconnect/slow-client isolation, SSR access control, report formula reconciliation, scheduling approval, and no raw telemetry leakage to browsers. |
| M5 — Firmware management | Signed artifact catalogue, compatibility policy, staged rollout, device progress, pause, rollback, and immutable release evidence are available. | Test rejected unsigned/incompatible/rollback firmware, canary failure pause, resume behaviour, device state transitions, artifact access expiry, and audit completeness. |
| M6 — Resilience, evidence, and recovery | WORM evidence archive, SLOs, dashboards, backup/restore, and bounded failure handling are operational. | Test archive retention configuration, restore into isolation, broker/Kafka/database outage handling, replay, correlation propagation, chaos scenarios, and RTO/RPO evidence. |
| M7 — Optional monetization | Metering, entitlement, rating, invoice/credit lifecycle, and product feature limits are available as an independently deployable module. | Test billing-disabled core operation, duplicate metering, effective-dated price rules, period close/reversal, tenant isolation, entitlement cache failure, and provider-token-only payment handling. |
| M8 — Deployment Studio | Approved operators can generate and approve portable on-prem/AWS/Azure/GCP deployment plans; a restricted runner and GitOps reconcile them. | Test plan-only versus apply authorization, policy denials, profile rendering, vault reference injection, least-privilege runner access, drift detection, rollback, and smoke tests in the selected profile. |

## Full regression gate after every milestone

Run every applicable command below after each stage. Existing commands must
pass now; a future stage must add its missing stage-specific command to CI
before it can be marked complete.

```bash
python -m pytest -q --junitxml=test-results/pytest.xml
python -m pytest -v tests/chaos
python -m ops.smoke_test
docker build --tag local/hybrid-rag:stage-test .
```

The pull-request CI gate is also mandatory: Python 3.12 and 3.13 tests,
optional adapter-import check, Helm render/lint, Ansible/YAML syntax and lint,
Terraform format/validate, Kubernetes schema/server dry-run validation,
container smoke test, and HIGH/CRITICAL image and IaC scans. For a stage that
introduces a new provider, transport, bounded context, or data store, extend
this gate rather than treating the existing suite as sufficient.

Before promotion, attach test output, versioned migration/report mapping,
deployment plan, rollback procedure, and immutable audit evidence. A failed,
skipped, or unavailable required test blocks milestone completion.
