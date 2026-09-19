# Architecture assessment and acceptance plan

Assessment date: 2026-09-19. This is a reference application with optional
integration blueprints, not a validated production payment platform or a PCI
attestation. The bounded contexts currently share one FastAPI process, thread
pool, audit sink, publisher, and deployment. They are logical modules, not
independently deployed microservices.

## Packages and runnable baseline

Python 3.12 was used for local verification. The full requirements installed;
the original kafka-python 2.0.2 failed to import because its vendored six is
incompatible with Python 3.12. It is now pinned to 2.2.20. Adapter import tests
guard against optional integrations silently disabling themselves. Python 3.13
remains in the CI matrix but was not executed locally. Requirements pin direct
dependencies only; transitive versions are not locked. A successful pip check
does not establish absence of vulnerabilities. Image and IaC security scans
must pass separately; no security exceptions were introduced.

Run the standalone demo with `docker compose -f docker-compose.local.yaml up
--build`, or use a Python 3.12 virtual environment and `python -m uvicorn
app.main:app --host 127.0.0.1 --port 8000`. All external adapters default off.
Storage and audit records are then ephemeral and are not compliance evidence.
`python -m ops.smoke_test` starts a temporary API, exercises real HTTP endpoints,
and terminates it afterward.

The full `docker-compose.yaml` remains an integration blueprint: MirrorMaker
references a missing `streaming/mirror-maker.properties`; Tempo lacks its mounted
configuration; Spark needs Kafka/S3 connector jars, S3 endpoint configuration,
and provisioned buckets; Debezium needs a registered connector. Several services
expose unauthenticated development ports or use development credentials. Do not
expose this profile to a production network. The Prometheus mount filename and
Dockerfile shell syntax have been corrected. Helm now requires a published API
image tag instead of attempting to boot the application from a bare Python 3.11
image. Docker, Helm, Terraform, and a cluster were unavailable locally.

## Requirements mapped to implementation

| Area | Present evidence | Remaining acceptance work |
| --- | --- | --- |
| Cloud and Zero Trust | Reformatted AWS/Azure audit/search Terraform starters with configured CI `fmt`/`init`/`validate` gates, provider-neutral Ansible SPIRE hardened-stack installation, SPIFFE CSI mount, selected ClusterSPIFFEID, sidecar-mode STRICT Istio policy, default-deny NetworkPolicy, and gateway-only WAF contract | No live EKS/AKS/K3s execution, complete VPC/VNet/PrivateLink design, provider WAF module, production CA subject/JWT issuer, or end-to-end certificate evidence is supplied. Test authentication, authorization, denied ingress/egress, WAF rules, SVID rotation, certificate rotation, and plaintext rejection. |
| Fintech streams | Payment event contracts, Avro schema examples, Kafka/KRaft, Registry, MirrorMaker and Debezium manifests | Publisher sends JSON, not Registry-validated Avro. No durable outbox, consumer idempotency, confirmed delivery, CDC registration, replay/lag benchmark or regional replication evidence. Validate ordering by transaction, duplicates, schema incompatibility, poison events and broker loss. |
| AI fraud models | Amount-based deterministic baseline and injectable anomaly detector; optional Ollama retrieval | The payment route does not invoke the anomaly adapter. No trained predictive fraud model, LLM fraud evaluation, model governance or measured throughput is demonstrated. Test fail-closed review behavior, precision/recall, drift, prompt injection and human review. |
| Governance and PCI | TOGAF ADM and C4 documents, redaction, object-lock write options, external-secret hooks | No deployed OPA/Kyverno policies or Vault attestation/rotation tests. Establish CDE inventory and ownership, approved data flows, segmentation evidence, retention approvals, access reviews and independent compliance assessment. |
| Agentic DevSecOps | Argo CD and Rollouts examples, GitHub image build/scan/publish workflow | No agent-driven rollback analysis or log summarizer is implemented. No measured MTTR improvement. Define approval scope, canary analysis thresholds and replayable rollback drills before enabling automation. |
| Observability and DR | Health endpoints, custom Prometheus metrics, LGTM service examples, verifier | Transitive OpenTelemetry packages do not prove application instrumentation. No complete collector pipeline, predictive alarm model, Velero deployment or tested multi-region failover. Establish RTO/RPO, encrypted backups, restore drills and observed alert delivery. |

## Identity and compliance decisions

Istio's current [sidecar-to-Ambient migration documentation](https://istio.io/latest/docs/ambient/migrate/)
states that Ambient does not support SPIRE integration. This repository therefore
uses sidecar mode: the hardened SPIRE chart registers the selected workload and
the CSI driver mounts its application SVID, while Istio independently enforces
Envoy mTLS. Do not claim that SPIRE replaces istiod or that this design works in
Ambient merely because both use SPIFFE identities. Define the target trust
domain, attestation source, authorization policy, ingress termination and every
non-mesh transport boundary explicitly.

Use the [PCI SSC document library](https://www.pcisecuritystandards.org/document_library/)
and [PCI DSS 4.0.1 publication](https://blog.pcisecuritystandards.org/just-published-pci-dss-v4-0-1)
for the current 4.x baseline. Redaction and a tokenized flag do not automatically
remove a system from CDE scope. The current API accepts arbitrary free-text and
identifier fields; classification, authentication and CDE segmentation require
additional controls and evidence. TOGAF/C4 describe governance; they do not
themselves enforce or certify PCI compliance.

## Domain isolation: guarantees and limits

Retrieval and model policies now persist across requests and have separate
budgets. Timed-out workers retain their bulkhead slots until they actually exit,
preventing repeated timeouts from creating unlimited downstream worker threads.
Ordinary adapter exceptions return the safe retrieval fallback and event metadata
contains error classes rather than raw downstream messages. Payment risk and
anomaly policy objects also persist across calls.

Failure-injection tests cover retained slots after timeout, separate domain
budgets, persistent rate limits, and continued payment/liveness responses after
retrieval connection/runtime/value errors. These establish bounded application
behavior for those failures; they do not establish process or regional isolation.
Python cannot forcibly cancel an uncooperative worker: configure transport-level
timeouts as well, and use separate processes/deployments for hard isolation.

Remaining risks include synchronous store writes and audit calls without these
bulkheads, startup adapter I/O, audit exceptions inside compensation handlers,
shared API worker capacity, unbounded in-memory record histories, and best-effort
Kafka sends without durable delivery or asynchronous acknowledgement handling.
Compensation events record failures; they do not undo indexed data. Payment
success is not evidence of durable event publication. These require explicit
failure contracts and durable storage before production payment acceptance.

## Test and delivery acceptance

| Check | Evidence / command | Status |
| --- | --- | --- |
| Dependency installation and consistency | Python 3.12; `python -m pip check` | Executed locally |
| Unit/API/redaction/payment/health and chaos suites | `python -m pytest -q --junitxml=test-results/pytest.xml` | Executed locally; final count in delivery summary |
| Adapter imports | `tests/test_adapter_imports.py` | Included in local suite and CI |
| Real HTTP startup and request flow | `python -m ops.smoke_test` | Executed locally |
| Python 3.13 | GitHub matrix | Pending remote execution |
| Container startup and image/IaC security | CI smoke step and Trivy HIGH/CRITICAL gates | Pending Docker/GitHub execution |
| Cloud/mesh/policy/streaming/DR integration and load tests | Acceptance work in table above | Not executed; infrastructure and credentials required |

CI now fails on security findings instead of reporting success via exit-code 0,
retains JUnit artifacts, runs real HTTP and adapter checks, and bounds job runtime.
Publish/deploy depends on the reusable CI workflow, so release tags cannot bypass
the test/build/security checks. The scheduled chaos workflow still provides an
independent recurring check; all chaos tests also run in ordinary CI.

The latest inspected [GitHub resilience run](https://github.com/amazen33/omni-stream-RAG-mesh/actions/runs/35323398765)
failed before steps ran. GitHub's check annotation says: "The job was not started
because your account is locked due to a billing issue." The repository owner
must resolve that account issue, publish these reviewed changes, and rerun CI.
No remote success, image build, cloud deployment, throughput target, MTTR reduction
or PCI readiness is claimed by this local assessment.
