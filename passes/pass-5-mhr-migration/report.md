# Pass 5 — Execution report

## What ran

- Cloned `facebookresearch/MHR` to `external/MHR/`
- Downloaded the v1.0.0 `assets.zip` (~190 MB) and unpacked into `models/mhr/assets/`
- Trimmed unused LODs (LOD0, LOD2-6 + their FBX + TorchScript model) to free disk: kept only `lod1.fbx`, `compact_v6_1.model`, `corrective_blendshapes_lod1.npz`, `corrective_activation.npz` — 644 MB total
- Created a Python 3.12 venv at `.venv-mhr/` because `pymomentum-cpu` wheels are only built for cp312/cp313 (we're on Python 3.11 system-wide)
- Installed `pymomentum-cpu 0.1.110.post0` + `mhr` + render deps in the venv
- Built `src/mhr_body.py` exposing `build_mhr_mesh(identity_coeffs, face_expr_coeffs, lod) -> trimesh.Trimesh`
- Built `scripts/build_mhr_default.py` for stage 1 — rendered MHR default body
- Built `scripts/explore_mhr_identity.py` for stage 2 — rendered 6 bodies at varied identity coefficients

## Install rabbit holes (worth knowing for future passes)

1. **Pip `pymomentum-cpu` install failed initially.** Wheels exist on PyPI but only for cp312/cp313. System Python is 3.11, so the install said "no matching distribution." Solution: Python 3.12 is also installed on this Ubuntu (`/usr/bin/python3.12`); created a dedicated venv from it.

2. **Disk filled up** during the first venv install. Out of 22 GB free at start, 4.5 GB went to MHR assets, several more went to torch wheels. Cleaned up unused LODs (lod0 alone was 2.5 GB) and the unused TorchScript model (664 MB) to recover 3.8 GB.

3. **`MHR.from_files()` segfaults** at `character.with_blend_shape(character.blend_shape)`. Bug in pymomentum-cpu 0.1.110.post0 + Python 3.12 + PyTorch 2.8 on Ubuntu 24.04. Workaround: load the FBX directly via `pymomentum.geometry.Character.load_fbx()`, get vertices and blendshape directions, apply identity blendshapes manually with `einsum`. Pose correctives (the MLP-based blendshapes) are skipped — they're a pass-6 concern.

4. **`import pymomentum` fails with `libtorch.so` not found** if you don't `import torch` first. pymomentum's native code needs libtorch loaded with RTLD_GLOBAL. Solution: import torch before pymomentum at module load time.

5. **MHR meshes are in centimeters** by default (Y extent of default body ≈ 172.7 cm). SMPL-X was in meters and we scaled ×100 at render time. The render script now detects unit by Y extent.

## Stage 1 — default body smoke test ✓

`outputs/mhr/mesh_default.obj`:
- 18,439 vertices (vs SMPL-X's 10,475 — almost 2× density)
- 36,874 faces
- Bounds: x ∈ [-65, +65], y ∈ [0, 172.6], z ∈ [-13.9, +25.6] (cm)
- T-pose-ish with slight arm separation from torso

8 view PNGs in `outputs/mhr/renders/` at 1024×1024. Front render shows a recognizable, anatomically natural human with visible face features (much more detail than SMPL-X provided).

## Stage 2 — identity exploration ✓ (and surprising)

Rendered front views at 6 identity coefficient settings (`outputs/mhr/exploration/<name>/view_000.png`):

| name | description | observed body |
| --- | --- | --- |
| zero | all coeffs = 0 | mean-shape body, ambiguous sex presentation |
| all_plus_1 | every coeff = +1 | **female-presenting**: visible breasts, wider hips, fuller proportions |
| all_minus_1 | every coeff = −1 | **male-presenting**: flat chest, athletic V-shape, defined musculature |
| body_only_plus_1 | first 20 = +1, head/hands = 0 | same body changes as all_plus_1 minus the head shift |
| rand_a, rand_b | Gaussian σ=0.8 random | distinct bodies that read as different people |

**Critical observation**: moving along the identity coefficient vector traces a continuous path between bodies as different as "athletic male" and "curvy female." This is direct evidence MHR's shape space is fundamentally different from SMPL-X's. With SMPL-X, pushing β to extremes produced caricatures (pass 3's narrow-shoulder, scooped-abdomen "Gollum" body). MHR at ±1 produces realistic bodies at every interpolation point.

The 45-dim identity space is genuinely independent in a way SMPL-X's 10-β PCA was not. This validates the architectural choice — non-linear MLP-based shape model with decoupled axes. We can plausibly dial in "wide hips" without "flat chest" coming along for the ride.

## Stage 3 — SMPL-X → MHR conversion (deferred)

Not attempted this pass. The `external/MHR/tools/mhr_smpl_conversion/` tools exist but require pymomentum-gpu or further setup. Since stage 2 demonstrated MHR's intrinsic shape diversity, going via SMPL-X conversion (which would carry SMPL-X's limitations through) is the wrong target anyway. Pass 6 should fit MHR identity directly from photos or measurements.

## What's still needed for a full replacement (pass 6+)

1. **Measurement-driven identity fitting.** No A2B equivalent for MHR. Options: (a) build an optimizer that minimizes measurement loss against `target_measurements.json` (the einsum forward pass in `build_mhr_mesh` is differentiable; this is tractable), (b) use Meta's `Sam3D` to fit identity from our reference photos directly.
2. **Pose correctives.** Currently skipped. Need to wire in the MLP-based pose corrective layer when applying any non-zero pose, otherwise joint articulation will produce visible deformation artifacts.
3. **A measurement adapter for MHR topology.** Our `SMPL-Anthropometry` adapter only handles SMPL-X meshes (10,475 verts). For MHR (18,439 verts) we either need to write a direct measurer or run conversion-then-measure.
4. **Pose authoring.** MHR's 204-dim model_parameters has different conventions than SMPL-X's 63-dim body_pose. Need to learn the mapping.

## Files added / changed

- `passes/pass-5-mhr-migration/v1.md` — pass spec
- `passes/pass-5-mhr-migration/report.md` — this file
- `src/mhr_body.py` — adapter
- `scripts/build_mhr_default.py` — stage 1 driver
- `scripts/explore_mhr_identity.py` — stage 2 driver
- `outputs/mhr/mesh_default.obj`, `outputs/mhr/renders/view_*.png`
- `outputs/mhr/exploration/{zero,all_plus_1,all_minus_1,body_only_plus_1,rand_a,rand_b}/view_000.png`
- `.gitignore` updated to exclude `models/mhr/assets/`, `models/mhr/assets.zip`, `.venv-mhr/`
- `external/MHR/` cloned (gitignored)
