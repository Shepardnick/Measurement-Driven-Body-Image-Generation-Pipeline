# Pass 6 v2 — Execution report

## Phases delivered

### Phase A — `src/render_quality.py` (pyrender PBR renderer) ✓

pyrender 0.1.45 with EGL backend installed cleanly in the Python 3.12 venv (the Python 3.11 setuptools blocker is gone). 3-point world-space lighting (key + fill + rim), PBR skin material, composited onto a solid background post-render because pyrender 0.1.45's `Scene(bg_color=...)` misinterprets int tuples.

Visual quality: massive jump over matplotlib. Face features visible, anatomical detail (collarbones, knee caps, hand fingers), smooth shading, dimensional lighting, anti-aliased edges. ~1–3 s per view on 4-core CPU.

### Phase B — `src/body_fitter.py` (autograd optimizer) ✓

PyTorch optimizer over MHR identity_coeffs. Key architectural decision: **only optimize the first 20 components (body identity); leave the 20 head + 5 hands components at zero**. Earlier free-form optimization produced a curvy body with a distorted alien head — exactly what Meta's developer warned about in issue #25 ("shape parameters... will also change other body parts"). Constraining to body-only components fixed it cleanly.

Differentiable measurements via landmark vertex indices identified once on the default mesh (`data/mhr_landmarks.json`):
- Stature: `verts[head_top_idx].y - mean(verts[foot_indices].y)`
- Shoulder breadth, hip width: distance between specific vertex pairs
- Bust/waist/hip circumferences: sum of consecutive distances around pre-identified convex-hull rings at each Y level

Soft cap on coefficient magnitude (default 3.5) keeps the body in MHR's well-conditioned region.

### Phase C — `configs/<body>.json` + `scripts/build_body.py` ✓

Single-command end-to-end pipeline. Config schema:

```json
{
  "source": "measurements" | "obj",
  "measurements_path": "...",
  "obj_path": "...",
  "fitter": {"iterations": 300, "lr": 0.1, "regularization": 0.005, "clip_magnitude": 3.5, "body_components_only": true},
  "stature_scale": "auto",
  "identity_adjustment": {"deltas": {"5": +0.3, "11": -0.2, ...}},
  "render": {"resolution": 1024, "angles_deg": [...], "skin_rgb": [r, g, b]}
}
```

`scripts/build_body.py configs/<body>.json` runs:
1. Load config
2. Dispatch on `source` (fit MHR identity, or load OBJ directly)
3. Apply `identity_adjustment.deltas` (manual tuning knob; replaces the mesh-correction hacks from pass 3)
4. Build MHR mesh
5. Stature scale to actual target (body components don't include overall scale; circumferences proportionally adjusted via input pre-normalization so the final result hits both stature AND circumferences)
6. Render 8 views via pyrender
7. Re-measure mesh, write verification report

### Phase D — Legacy cleanup ✓

Deleted:
- `src/a2b_adapter.py`
- `src/anthropometry_adapter.py`
- `src/mesh_correction.py`
- `src/smplx_body.py`
- `scripts/build_corrected_body.py`
- `scripts/smoke_test_adapters.py`

Audit confirmed no remaining references from the new pipeline. Kept the pass-1 primitive proxy code (`src/proxy_body.py`, `src/render.py`, `src/main.py`) as a working legacy fallback for matplotlib-only environments.

## End-to-end result on `configs/subject_a.json`

Target measurements (from pass 4 photo-derived):
- stature 193.04 cm, bust 104.03, waist 73.58, hip 117.87 (W/H 0.62)

Verification of final rendered mesh:
| measurement | target | actual | residual |
| --- | --- | --- | --- |
| stature | 193.04 | 192.86 | -0.18 |
| bust | 104.03 | 103.59 | -0.44 |
| waist | 73.58 | 73.52 | -0.06 |
| hip | 117.87 | 117.67 | -0.20 |
| shoulder breadth | 38.23 | 44.86 | +6.63 |

Hip/waist/bust/stature all within 0.5 cm. Shoulder remains the outlier — same measurement-definition mismatch we identified in pass 4 (biacromial from MediaPipe vs vertex-distance from MHR landmarks). Not a fitter bug.

Visual outcome: realistic female silhouette with visible breasts, narrow waist, curvy hips, proportional and undistorted head, anatomical face features. First render in the project that reads as a real person rather than a 3D mannequin caricature.

## What this delivers vs. what came before

- **Single-command workflow.** Edit one JSON, run one script. No source code edits per body.
- **Plugin body source.** `source: "obj"` accepts a mesh from MakeHuman, Blender sculpt, anywhere — same downstream rendering, same identity.json output (minus the identity vector).
- **Manual tuning is first-class.** `identity_adjustment.deltas` in the config replaces the buried mesh-correction hacks from pass 3. Tweak components 0-19 (body) without code changes.
- **CPU-only, no GPU, no Sam3D, no Hugging Face dance.** Stays in the chat sandbox.
- **Pyrender quality.** Renders look like real lit bodies, not flat-shaded polygons.

## Known limits / pass-7+ work

- **Pose**: still default A-pose. Multi-pose authoring (sitting, walking, etc.) is pass 7.
- **Shoulder breadth fit**: definition mismatch; manual delta or a re-targeted shoulder landmark would fix.
- **No clothing**: bare body. Adding a bikini geometry layer would make better Nano Banana references.
- **Hands**: visible but still SMPL-X-style claw fingers (MHR's default hand pose).
- **No photo-driven fit**: would require Sam3D (GPU) or a new image-fitting path. Measurement-driven path is sufficient for now since pass 4 already extracts good measurements from photos.
- **Bust still slightly under-bias** per Meta dev's warning. Manual deltas handle it; the optimizer can't fully escape MHR's training distribution.
