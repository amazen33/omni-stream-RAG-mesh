# Hybrid Streaming RAG

Reference implementation, with hosting on Twinfra dev planned under WO-44.
O0 prepares dependencies, images and the chart; O1 hosting and its acceptance
receipt are pending. This is not a production-readiness claim. GitHub currently
lists the repository as public; the owner authorized proceeding with that
visibility on 2026-10-19. The source licence is unchosen, so no LICENSE file is
added. Public visibility does not grant a source licence. See
[THIRD-PARTY.md](THIRD-PARTY.md) for dependency and model licences.

Kubeadm and managed AWS/Azure/GKE profiles remain reference deployment
blueprints. K3s is a legacy resource-constrained lab/edge workflow.

## Downstream-failure resilience

Every API request receives server-issued immutable `request_id`,
`correlation_id`, and W3C `traceparent` values. Caller-supplied tracing headers
are discarded; they never become audit, event, or downstream identifiers. The
server values are returned in HTTP headers, carried in domain-event payloads,
and published as Kafka headers. If a downstream
vector store, inference/risk scorer, Kafka broker, or audit sink fails, the
application records an `INITIALIZED → PROCESSING → COMPLETED` or
`INITIALIZED → PROCESSING → COMPENSATED` lifecycle and publishes the matching
compensating event. The audit sink uses S3/MinIO Object Lock, Azure Blob locked
immutability, or GCS Bucket Lock with an approved retention period when
enabled; bounded in-memory diagnostics remain available only for local
development and tests.
This is a bounded compensating-transaction design, not a complete durable
event-sourcing rollback system: production event sourcing needs an append-only
event store, transactional outbox, replay projectors, and restore evidence.

`/metrics` includes bounded-cardinality Prometheus metrics for bulkhead activity
and rejections, rate-limit rejections, boundary duration, downstream failures,
and compensating events. `docker-compose.yaml` supplies the local LGTM
(Prometheus, Grafana, Loki, Tempo) topology together with an OpenTelemetry
Collector, TimescaleDB, and EventStoreDB. Those stateful services are optional
deployment extensions, not mandatory core-Python dependencies.

## Measuring QoS

`/metrics` exposes HTTP requests (`rag_http_requests_total`), duration
(`rag_http_request_duration_seconds`, including 30/60/120-second buckets), and
`rag_http_requests_in_flight`. Labels use matched route templates, including
health/metrics routes; missing routes and router redirects use `unmatched`.
Methods outside the standard HTTP verbs use `OTHER`. Status classes are `2xx`,
`3xx`, `4xx`, `5xx`, or `other` (architect decision, 2026-10-19); every request
updates both the counter and histogram. Exceptions and disconnects release the
in-flight gauge. Linux scrapes also read RSS bytes, user+system CPU seconds and
open descriptors from `/proc/self`; other operating systems omit these families.

`python -m ops.synthetic_corpus --seed 44 --count 1` prints reproducible synthetic
ingest documents (1/10/100 KiB), questions and payment payloads as JSON. No real
PII or card numbers are generated. Locust is a hashed MIT dev dependency; the
owner writes the scenarios and measures B0 in Part B of OMNI-WO-00.

The local harness is `deploy/load/docker-compose.baseline.yaml`. `OMNI_IMAGE`
accepts exactly two forms, with 64 lowercase hex characters after `sha256:`:

- `ghcr.io/amazen33/omni-stream-rag-mesh@sha256:<64 hex>`: a published main
  image manifest digest, required for B1/B2 (also allowed for B0).
- `sha256:<64 hex>`: a local main-image ID from
  `docker image inspect --format "{{.Id}}"`, allowed for B0 only, before publishing.

Tags and lab images are rejected before uvicorn starts. Set `BASELINE_PHASE`
to `B0` (default), `B1` or `B2`; the receipt records the phase, full reference
and form (`local-main-image-id` or `ghcr-manifest-digest`). After building main,
prepare a B0 run in PowerShell without printing the random token key:

```powershell
$env:OMNI_IMAGE = docker image inspect --format "{{.Id}}" local/omni-wo00:main
$baselineKeyBytes = New-Object byte[] 32
$baselineKeyRng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
try {
    $baselineKeyRng.GetBytes($baselineKeyBytes)
    $env:BASELINE_TOKEN_KEY = [Convert]::ToBase64String($baselineKeyBytes)
} finally {
    $baselineKeyRng.Dispose()
    [Array]::Clear($baselineKeyBytes, 0, $baselineKeyBytes.Length)
}
docker compose -f deploy/load/docker-compose.baseline.yaml up
```

Do not print the key, save it in the receipt or commit it. Remove the session
environment variable after the run. The API keeps `RUNTIME_PROFILE: production`,
2 CPUs/2 GiB, ephemeral stores, a read-only root and the production uvicorn
command. Part A publishes no image and claims no baseline result.

Inference stays off by default. For optional `--profile llm`, the owner selects
`BASELINE_MODEL=phi4-mini:3.8b` (MIT, owner D-O13) or an explicitly approved
`granite3.<variant>:<tag>` (Apache-2.0),
sets `BASELINE_MODEL_SHA256` to its approved manifest SHA256 and
`BASELINE_OLLAMA_MODELS` to an existing absolute Ollama model-cache directory,
then sets `BASELINE_INFERENCE=true`. The digest-pinned Ollama service verifies
the cached model manifest before serving; its cache is mounted read-only and
the harness never pulls weights. Record the image/model digests with the run.
`BASELINE_MODEL` remains an explicit owner input; other model families are rejected.

## Quick start
1. Run `docker compose -f docker-compose.local.yaml up --build` for the standalone demonstration.
2. This profile uses ephemeral memory storage and disables external integrations. For the full integration blueprint, copy `.env.example` to `.env`, replace secrets, provision the missing integration configuration described in the assessment, and create an object-lock audit bucket before enabling audit storage.
3. `curl -H 'Content-Type: application/json' -d '{"text":"sample"}' http://localhost:8000/ingest-sample`.

The RAG ingress boundary replaces recognised PII with versioned, canonicalized
128-bit HMAC tokens before chunking, indexing, model inference, events, or
audit writes. Source and payment identifiers are HMAC-tokenized before their
metadata/events leave that boundary; immutable audit records contain only
tokens, server-issued correlation identifiers, and operational metadata.
Chroma, Ollama, and OpenSearch adapters are deployment extension points; all
endpoints are environment variables. Never commit `.env`, keys, certificates,
or state.

## Documentation

The `docs/` directory has four focused documents:

1. [API and contributor guide](docs/API_AND_CONTRIBUTOR_GUIDE.md) — HTTP
   contract, examples, tracing, errors, and endpoint-design rules.
2. [Architecture and operations guide](docs/ARCHITECTURE_AND_OPERATIONS.md) —
   implementation architecture, security, platform profiles, delivery, and
   recovery.
3. [TOGAF Architecture Definition](docs/TOGAF_Architecture_Definition.md) —
   ADM governance plan, diagrams, migration, and implementation traceability.
4. [C4 model](docs/c4-model/C4_MODEL.md) — combined Level 1–4 structural and dynamic
   views plus the process for maintaining them.

The root [architecture decision record (ADR)](ARD.md) captures durable technical
decisions. [LAB_OPERATIONS.md](LAB_OPERATIONS.md) is the concise operational
entry point.

CI configuration lives in `.github/workflows/`: pull requests run tests,
Helm and infrastructure validation, main/lab image builds, Syft SBOM generation,
Grype image scans and OSV lock-file scans under the ADR-0049 rules. Every external
action is pinned by commit SHA. See the
[architecture and operations guide](docs/ARCHITECTURE_AND_OPERATIONS.md). `docker compose
exec rag-api sh` is the supported local debugging shell; the image does not
include or run an SSH daemon.

For Windows local development, use Python 3.12 (preferred) or 3.13. Python
3.14 is not supported for the pinned native dependencies. The local-only PowerShell
launcher accepts `-PythonPath` to select an installed supported interpreter.
The same Python 3.12/3.13 policy applies to Ubuntu/Linux, GitHub Actions,
Docker, and Kubernetes; changing the host OS does not make Python 3.14
compatible.

To run directly with Python 3.12: `python -m venv .venv`, activate the
environment, run `python -m pip install --require-hashes -r requirements-dev.txt`,
then explicitly set `RUNTIME_PROFILE=local` before running
`python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`.
An unset profile means production and requires a non-default `PII_TOKEN_SALT`.
Swagger, ReDoc and OpenAPI URLs return 404 unless `ENABLE_API_DOCS=true` in a
local, test or development profile. Errors log only safe identifiers and
exception types; development tracebacks require `LOG_INCLUDE_TRACEBACKS=true`.
Run `python -m pytest -q` for all tests, including deterministic failure injection.
Run `python -m pytest -v tests/chaos/test_lifecycle_downstream_failure.py` to
verify correlation propagation, metrics, audit transitions, and fail-closed
compensation.
See the [architecture and operations guide](docs/ARCHITECTURE_AND_OPERATIONS.md)
for verified behavior, production gaps, and acceptance work.

## Domain layout
`contexts/ingestion`, `contexts/ai`, and `contexts/governance` are bounded contexts.
The immutable integration events `TelemetryIngested`, `TransactionProcessed`, and
`AuditRecordLogged` map to the Kafka topics `telemetry.ingested`,
`transaction.processed`, and `audit.record.logged`. Kafka, Ollama, Chroma,
OpenSearch and object-storage adapters are opt-in through environment
variables, so health checks remain usable during dependency outages.

## Images and Twinfra delivery

`docker build --build-arg PROFILE=main -t local/omni-o0:main .` builds the shipped
image from the hashed `requirements.txt`. It excludes Chroma and its native
dependency tree, including NumPy and ONNX Runtime. `PROFILE=lab` selects
`requirements-lab.txt` for local development only, never shipped or released.
The full `docker-compose.yaml` builds this lab image; the standalone
`docker-compose.local.yaml` uses main. Main reports a clear failed readiness
check if `ENABLE_VECTOR_STORE=true`; OpenSearch is the planned Twinfra store.

Twinfra uses `deploy/values-twinfra.yaml`: one ephemeral replica, no PDB, no
mesh, no ServiceAccount API token and no external integrations. In-memory
retrieval and audit state are lost on restart and cannot be shared across pods.
The gateway namespace is `platform-services`, with the APISIX pod selector from
Twinfra's `module-2/manifests/apisix-dependency.yaml`. Without a mesh, metrics
ingress uses port 8000 and no istiod egress is rendered.

Twinfra deploys only through Argo CD. No Twinfra cluster credential may be
stored in GitHub. The legacy push-deploy job is off unless the owner explicitly
sets `ENABLE_PUSH_DEPLOY=true` and dispatches it on a stable tag for a separate
non-Twinfra target. Stable publishing builds main once, scans the OCI artifact,
pushes that artifact to GHCR by digest using `GITHUB_TOKEN`, and signs provenance
for that digest. GHCR digest and attestation evidence are available only after
the owner runs that workflow after merge; local image IDs are separate evidence.
Prereleases do not publish. No lab image is referenced by the chart.

Owner decision D-O13 selects `phi4-mini:3.8b` as the default AI model (MIT;
[official Ollama tag](https://ollama.com/library/phi4-mini:3.8b),
[Microsoft model card](https://huggingface.co/microsoft/Phi-4-mini-instruct)).
Its recorded manifest digest is
`sha256:78fad5d182a7c33065e153a5f8ba210754207ba9d91973f57dffa7f487363753`;
see the register for manifest provenance. `nomic-embed-text` remains the embedding model.
No model weights are in either API image. Optional MinIO, Grafana, Loki, Tempo,
EventStoreDB, TimescaleDB and Confluent Schema Registry are not used on Twinfra.

## Infrastructure and recovery

The Kubernetes deployment labels `rag-api` consistently for Istio/SPIRE and
mounts the SPIFFE Workload API socket directory using the CSI driver; readiness
opens that local socket and never reads certificate/key files. Its scoped default-deny
NetworkPolicies permit only the Istio gateway, Prometheus metrics, required
workload dependencies, Istio control plane, and DNS; cloud overlays additionally
allow their storage and workload-identity endpoints. The
provider-neutral mesh task installs SPIRE (CRDs, server, agent, controller
manager, CSI driver) and Istio before rendering the workload registration and
STRICT mTLS policy. The primary on-prem target is upstream Kubernetes installed
with kubeadm/containerd and Calico; cloud targets are managed EKS, AKS, or GKE. The
legacy K3s lab routes Traefik/Coraza through the Istio gateway; primary on-prem
and cloud WAFs use the same private gateway contract. See the
[architecture and operations guide](docs/ARCHITECTURE_AND_OPERATIONS.md) for
prerequisites and commands.
`k8s/velero-backup.yaml`
defines a daily, encrypted MinIO/S3-targeted Velero backup schedule with volume
snapshots. The recovery procedure is in the
[architecture and operations guide](docs/ARCHITECTURE_AND_OPERATIONS.md).

## Source location

The source currently being updated is located at
`D:\project\Rag-Mesh\omni-stream-RAG-mesh`. The repository root is the source
of truth for application code, tests, manifests, and these documents.
