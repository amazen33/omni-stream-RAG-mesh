# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
See [RELEASING.md](RELEASING.md) for the release streams.

## [Unreleased]

### Added

- Release streams (Dev, Candidate, Stable): `RELEASING.md`, this changelog, the `VERSION`
  file (next release: 0.2.0), the `release-checks` and `release` workflows, and the rulesets
  in `.github/rulesets/`.

### Changed

- WO-44 O0 (Amendments 1–4): refresh and hash runtime/dev/controller locks;
  split shipped main from local-only Chroma lab image; pin the Python base and
  CI actions; replace Trivy with pinned Syft/Grype/OSV gates; publish the scanned
  main OCI artifact by digest with signed provenance. Push deployment requires
  the explicit repository variable and stable-tag dispatch; Twinfra is Argo CD only.
- Add the single-replica ephemeral Twinfra chart profile, gateway selectors,
  mesh-aware network rules, Secret-provider Debezium references and v2 Spark topics.
  Production defaults reject missing/default token keys, disable API docs, and
  log safe error fields. Add the main/lab dependency and model licence register.
- Amendment 4 intentionally disables Chroma in the legacy lab Helm profile;
  its full local Compose lab continues using the separate lab image.
- `Publish and deploy` publishes images only for stable tags (`vX.Y.Z`); pre-release tags
  no longer publish. The deploy job runs only when dispatched on a stable tag.

## [0.1.0] - 2026-09-22

- Hybrid Streaming RAG (back-filled from the tag `v0.1.0` and its GitHub release title).
