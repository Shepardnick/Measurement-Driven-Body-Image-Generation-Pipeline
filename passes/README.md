# Passes

Sequential planning documents for this project. Each pass is a versioned
design doc for a chunk of work, created and revised through the workflow
defined in `CLAUDE.md` (see *Pass-based planning workflow*).

Each pass lives in its own subfolder: `pass-<N>-<slug>/`. Versions accumulate
as `v1.md`, `v2.md`, `v3.md`, … and earlier versions are never overwritten —
the diff between versions is part of the project's reasoning record.

## Index

| #   | Slug | Latest | Status | Summary |
| --- | ---- | ------ | ------ | ------- |
| 1   | [primitive-render-scaffold](pass-1-primitive-render-scaffold/v1.md) | v1 | executed | End-to-end `measurements → primitive humanoid mesh → 8-view PNG renders` scaffold using ellipsoids and capsules in place of SMPL-X. Matplotlib renderer (pyrender's PyOpenGL build broke on this env). |
| 2   | [external-adapters](pass-2-external-adapters/v1.md) | v1 + [report](pass-2-external-adapters/report.md) | executed | Cloned A2B and SMPL-Anthropometry. A2B adapter works end-to-end (β values returned, magnitudes [-18, +17] confirm extreme-distribution warning). SMPL-Anthropometry adapter validated end-to-end after SMPL-X weights landed. Confirmed SMPL-X 10-β space can't reach target hip (138.7 cm) — ceiling ~128 cm. |
| 3   | [smplx-corrections](pass-3-smplx-corrections/v1.md) | v1 | draft | Build SMPL-X body from A2B SVR-clipped β; programmatically correct hip (inflate) and waist (compress) via Gaussian-weighted radial deformation; render 8 views. |

## Status legend

- **draft** — pass created, awaiting feedback
- **approved** — user has signed off; ready to execute
- **executed** — implementation complete on this branch
- **superseded** — replaced by a later pass; kept for history
