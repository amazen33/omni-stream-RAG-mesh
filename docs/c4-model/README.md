# C4 model notation guide

The four C4 pages describe the same implementation at progressively finer
granularity. Each page contains a Mermaid diagram for GitHub-native rendering,
a PlantUML diagram for PlantUML tooling, and an ArchiMate block where the view
maps naturally to architecture-layer concepts.

| Level | Document | Mermaid | PlantUML | ArchiMate |
| --- | --- | ---: | ---: | ---: |
| 1 — System context | [level-1-system-context.md](level-1-system-context.md) | Yes | Yes | Yes |
| 2 — Container | [level-2-container.md](level-2-container.md) | Yes | Yes | Yes |
| 3 — Component | [level-3-component.md](level-3-component.md) | Yes | Yes | Yes |
| 4 — Code/dynamic | [level-4-code-dynamic.md](level-4-code-dynamic.md) | Yes | Yes | Yes |

Mermaid fences use the `mermaid` language and render directly in GitHub
Markdown. PlantUML fences use `plantuml`; render them with PlantUML 1.2023+
or a compatible server. ArchiMate fences use `archimate` and follow the
ArchiMate textual conventions supported by Archi, ArchiMate tooling, or a
text-to-model pipeline. GitHub does not execute PlantUML or ArchiMate blocks,
so the blocks intentionally remain source diagrams.

The diagrams are descriptive views of repository components, not additional
runtime dependencies. Optional adapters remain controlled by environment flags
such as `ENABLE_KAFKA`, `ENABLE_VECTOR_STORE`, `ENABLE_SEARCH_STORE`,
`ENABLE_METADATA_INDEX`, and `ENABLE_OLLAMA_INFERENCE`.

The resilience revision adds correlation/causation and W3C trace context to
every view. EventStoreDB, TimescaleDB, the OpenTelemetry Collector, Istio,
SPIRE, and Velero are deployment components. The provider-neutral mesh play
installs the Istio and hardened SPIRE controllers (including the CSI driver)
for a prepared Kubernetes target; the target environment still supplies the
approved trust domain, CA subject, JWT issuer, storage, WAF/DNS, credentials,
and recovery evidence. The source root for these C4 views is
`D:\project\Rag-Mesh\omni-stream-RAG-mesh`.
