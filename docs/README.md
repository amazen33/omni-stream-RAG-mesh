# omni-RAG-mesh architecture

This documentation describes the implementation in this repository: a
platform-agnostic streaming RAG reference stack for regulated workloads. It
is intentionally explicit about what is enabled by default and what is an
environment-driven integration.

## Documentation map

- [System context and components](system-context.md)
- [Domain model and event contracts](domain-events.md)
- [Data flows](data-flows.md)
- [Deployment and infrastructure topology](deployment-topology.md)
- [Security and trust boundaries](security.md)
- [Delivery and operations](delivery-operations.md)
- [TOGAF Architecture Definition](TOGAF_Architecture_Definition.md)

## C4 model

- [Level 1: System context](c4-model/level-1-system-context.md)
- [Level 2: Container](c4-model/level-2-container.md)
- [Level 3: Component](c4-model/level-3-component.md)
- [Level 4: Code and dynamic flow](c4-model/level-4-code-dynamic.md)

## Source of truth

The executable configuration is in the repository root and its subdirectories:
`app/`, `contexts/`, `domain/`, `streaming/`, `docker-compose.yml`, `k8s/`,
`terraform/`, `ansible/`, `deploy/`, and `Jenkinsfile`. These pages document
those files; they do not imply that optional integrations are active in every
deployment.

For bootstrap and troubleshooting procedures, see the root
[README](../README.md), [architecture decisions](../ARD.md), and
[operations runbook](../LAB_OPERATIONS.md).
