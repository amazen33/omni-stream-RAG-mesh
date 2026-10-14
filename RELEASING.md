# Releasing

This project follows three release streams: **Dev → Candidate → Stable**.

## Streams

| Stream | What it is | Image and deployment |
| --- | --- | --- |
| **Dev** | Every merge to `main` | CI builds and tests the image; nothing is published |
| **Candidate** | Tag `vX.Y.Z-rc.N` on `main`. A GitHub **pre-release** | **No image is published** for pre-release tags |
| **Stable** | Tag `vX.Y.Z` on the **same commit** as the accepted candidate. The release workflow creates a **draft**, and the owner publishes it | `Publish and deploy` publishes the scanned image to GHCR. A deployment runs only when the owner dispatches it **on the stable tag** with `deploy: true` |

## Version source

`VERSION` holds the **next release's base version**, `X.Y.Z`. Versions follow [Semantic Versioning](https://semver.org).

## Cutting a release

1. **Prepare.** Open a PR titled `release: X.Y.Z`. In `CHANGELOG.md`, move `## [Unreleased]` into `## [X.Y.Z]`, and leave an empty `## [Unreleased]` above it. Merge it.
2. **Candidate.** Tag the merge commit `vX.Y.Z-rc.1` and push the tag. The `release` workflow validates it and creates a pre-release.
3. **Accept.** Review it. Fix on `main` and cut `-rc.2` if needed.
4. **Stable.** Tag the **same commit** `vX.Y.Z` and push it.
   - `release` creates a draft, which the owner publishes.
   - `Publish and deploy` runs CI, builds, scans and publishes the image.
5. **Deploy (optional).** Actions → Publish and deploy → Run workflow → pick the **stable tag** → `deploy: true`. Runs on a branch or a pre-release tag skip the deploy job.
6. **Next.** Open a PR that bumps `VERSION` to the next base version.

## Rules

- **Tags are immutable.** A `v*` tag is never moved or deleted.
- **Every change goes through a PR.** `main` requires `release-checks`, `test (3.12)` and `test (3.13)`.
- **Every PR updates `CHANGELOG.md` under `[Unreleased]`**, or carries the label `changelog:skip` with a reason.
- **Fixes land on `main`.** A `release/X.Y` branch is created only if an older version needs a patch.

The rulesets are in `.github/rulesets/`.
