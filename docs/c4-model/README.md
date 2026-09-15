<<<<<<< HEAD
# C4 Architecture Model: Omni-Stream RAG Mesh

This directory documents the software architecture of the Omni-Stream RAG Mesh platform using the **C4 Model** (Context, Containers, Components, and Deployment).

```
Level 1: System Context  ──> Who uses the system and how does it fit into the world?
    │
    ▼
Level 2: Container       ──> What are the high-level deployable units (FastAPI, Kafka, MinIO, Chroma, Ollama)?
    │
    ▼
Level 3: Component       ──> How is the FastAPI Gateway structured internally (Bulkhead, Circuit Breaker, Audit)?
    │
    ▼
Level 4: Deployment      ──> How are containers mapped onto the Hyper-V VMs and K3s cluster nodes?
```

## Diagram Index

1. [Level 1: System Context Diagram](01-system-context.md)
2. [Level 2: Container Diagram](02-container.md)
3. [Level 3: Component Diagram (FastAPI RAG Gateway)](03-component.md)
4. [Level 4: Deployment Diagram (Hyper-V & K3s)](04-deployment.md)
=======
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
>>>>>>> 326eae92028aa5e56d0e35de134f27355dcba79d
