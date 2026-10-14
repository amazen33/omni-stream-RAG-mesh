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

- `Publish and deploy` publishes images only for stable tags (`vX.Y.Z`); pre-release tags
  no longer publish. The deploy job runs only when dispatched on a stable tag.

## [0.1.0] - 2026-09-22

- Hybrid Streaming RAG (back-filled from the tag `v0.1.0` and its GitHub release title).
