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
| 3   | [smplx-corrections](pass-3-smplx-corrections/v1.md) | v1 | executed | Build SMPL-X body from A2B SVR-clipped β; programmatically correct hip (inflate) and waist (compress) via Gaussian-weighted radial deformation; render 8 views. Hip residual −0.45 cm, waist +1.66 cm (both within ±2 cm tolerance). Side-view hip artifact from post-pose delta hack noted. |
| 4   | [photo-measurements](pass-4-photo-measurements/v1.md) | v1 + [report](pass-4-photo-measurements/report.md) | executed | Re-derive measurements from reference photos using MediaPipe + Ramanujan ellipse perimeter. Old `target_measurements.json` was width × π; new values give W/H 0.62 instead of 0.52. Hip 138.7 → 117.9. |
| 5   | [mhr-migration](pass-5-mhr-migration/v1.md) | v1 + [report](pass-5-mhr-migration/report.md) | executed | Migrate from SMPL-X to Meta's MHR. Stage 1: install + default-body render ✓. Stage 2: identity exploration ✓ — confirmed shape space spans athletic-male → curvy-female smoothly at ±1 coefficients. Stage 3 (SMPL-X conversion) deferred. Pass 6 needs measurement-driven identity fitting. |
| 6   | [end-to-end-fitting](pass-6-end-to-end-fitting/v2.md) | v2 + [report](pass-6-end-to-end-fitting/report.md) | executed | MHR autograd fit + pyrender PBR. Worked but produced a soft/average body — Meta's known limit (issue #25). Superseded by pass 7. |
| 7   | [charmorph-migration](pass-7-charmorph-migration/v1.md) | v1 + [report](pass-7-charmorph-migration/report.md) | **executed** | Migrate body source from MHR to CharMorph (MB-Lab successor, FOSS GPL-3.0). 60+ named morphs (Torso_BreastTone, Pelvis_GluteusMass, Abdomen_Tone, etc.) replace MHR's 45 anonymous PCA components. 30+ body archetype presets. One-shot Blender extraction → pure Python runtime (no Blender at runtime). MHR code archived to `legacy/mhr/`. **Resolves the saggy/soft body problem — visible muscle tone, perky bust, defined abs.** |

## Status legend

- **draft** — pass created, awaiting feedback
- **approved** — user has signed off; ready to execute
- **executed** — implementation complete on this branch
- **superseded** — replaced by a later pass; kept for history
