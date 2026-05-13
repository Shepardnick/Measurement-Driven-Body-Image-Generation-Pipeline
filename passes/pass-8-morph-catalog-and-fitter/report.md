# Pass 8 — Execution report

## What ran

### Stage 1 — Morph catalog ✓
- `scripts/build_morph_catalog.py` parses every storage-name in `L2_packed/__main__.npz` + `Caucasian.npz`, derives slider names from compound/single corner patterns, groups by anatomical region.
- 165 unique sliders catalogued.
- Output: `data/charmorph_morph_catalog.json` (programmatic) + `passes/pass-8-morph-catalog-and-fitter/morph_catalog.md` (human-readable).
- Region counts: torso 10, torso/breast 6, abdomen 2, waist 1, pelvis 10, stomach 2, shoulders 7, neck 9, arms 12, legs 16, hands 10, feet 6, head 9, body global 1, face 102 (cheeks/chin/ears/eyes/forehead/mouth/nose/other).

### Stage 2 — CharMorph landmark vertex rings ✓
- `scripts/build_charmorph_landmarks.py` identifies stable vertex indices on the default `mb_female` mesh: top-of-head, foot pair, shoulder pair, hip-widest pair, plus convex-hull rings at bust (74% stature), waist (66% stature), hip-widest (~50% stature).
- Output: `data/charmorph_landmarks.json`.
- Default body measurements (m): stature 1.678, bust ring 0.847, waist ring 0.529, hip ring 0.954.

### Stage 3 — Differentiable measurement layer ✓
- `src/charmorph_fitter.py::measure_torch(verts, landmarks)` computes stature, shoulder breadth, hip width, bust/waist/hip ring perimeters as `torch.Tensor`s. All operations differentiable through `verts`, and `verts` is differentiable through morph values via the forward pass.

### Stage 4 — Autograd optimizer ✓
- `src/charmorph_fitter.py::fit_charmorph_morphs(target, init, optimize_keys, …)`:
  - PyTorch `nn.Parameter` over a vector of named morph values.
  - Forward: applies single + combo morphs via `forward_mesh` (re-implements CharMorph's combo math in PyTorch).
  - Loss: weighted MSE against target measurements + L2 regularization toward init.
  - Bounds: `torch.clamp(0, 1)` projection inside forward + step.
  - Adam optimizer, ~300 iterations, ~30 s on 4-core CPU.

### Stage 5 — Wired into `build_body.py` ✓
- `source: "charmorph"` accepts:
  - `preset`: starting point (any of 30+ archetypes)
  - `morph_values`: manual overrides on top of preset
  - `fit_to_measurements: true` + `measurements_path`: enables the optimizer
  - `optimize_morphs`: list of slider groups (`"body"`, `"shape_only"`, `"all_measurement_relevant"`) or literal names
  - `fitter`: iterations / lr / regularization knobs
- Iterative pre-normalize/post-scale loop converges in 2 iterations to drive stature residual to zero.

### End-to-end verification (target_measurements.json)

| measurement | target | actual | residual |
| --- | --- | --- | --- |
| stature | 193.04 | 193.04 | **0.00** |
| bust | 104.03 | 104.03 | **0.00** |
| waist | 73.58 | 73.58 | **0.00** |
| hip | 117.87 | 117.87 | **0.00** |
| shoulder breadth | 38.23 | 41.78 | +3.55 |

**All four primary measurements hit exactly.** Shoulder breadth still off by 3.55 cm — same measurement-definition mismatch present since pass 4 (MediaPipe biacromial vs vertex-pair acromion distance).

Front render at `outputs/subject_a_fitted/renders/view_000.png` shows a coherent female body: visible breasts, narrow defined waist, curvy hips, anatomical face. One minor surface artifact on the left breast (a single vertex pushed by combo-corner clamps); not affecting silhouette.

## Bugs caught during execution

1. **Empty `Body_Size_max` morph.** The slider exists in the catalog with `_max` and `_min` corners listed, but the actual delta arrays in CharMorph's L2_packed bundle have 0 vertices — the morph is hollow. Workaround: handle stature via uniform mesh scaling after the morph-shape fit instead of trying to optimize it inside the fitter. Documented as a CharMorph-db quirk.

2. **Zero-gradient init.** When a morph in `optimize_keys` isn't in the preset, `init` is 0; the forward pass `clamp(v, min=0)` at v=0 has zero gradient → optimizer never moves it. Fixed in `fit_charmorph_morphs` by nudging unset-init values from 0 to 0.05 so the clamp's positive branch is active.

3. **Stature pre-normalize imprecision.** Single-shot pre-normalize uses `target_stature / default_stature` as the scale, but the post-fit mesh's actual stature differs slightly (morph composition isn't purely scale-preserving). Result: residuals 1–2 cm post-scale. Fixed via 2-pass iterative refine: refit with the *actual* post-fit stature as the normalization base. Converges in 1 refine iteration.

## Files added / changed

Added:
- `passes/pass-8-morph-catalog-and-fitter/v1.md`, `report.md`, `morph_catalog.md`
- `data/charmorph_morph_catalog.json`
- `data/charmorph_landmarks.json`
- `src/charmorph_fitter.py`
- `scripts/build_morph_catalog.py`
- `scripts/build_charmorph_landmarks.py`
- `configs/subject_a_fitted.json`
- `outputs/subject_a_fitted/` (mesh + 8 renders + identity.json)

Modified:
- `scripts/build_body.py`: `source: "charmorph"` now accepts `fit_to_measurements`, `optimize_morphs`, `fitter`. Iterative refine loop.
- `passes/README.md`: pass 8 entry.

## Stretch goal (deferred)

Stage 6 — skin texture maps & UV-based PBR material — was scoped as best-effort but not delivered in this pass. CharMorph-db ships skin diffuse textures and the .blend has UVs; integrating would require:
1. A second one-shot Blender script to extract per-vertex UV coords.
2. Picking the right diffuse texture file from `external/CharMorph-db/characters/mb_female/textures/`.
3. Updating `src/render_quality.py` to build a `pyrender.MetallicRoughnessMaterial` with `baseColorTexture`.

Tractable but separate from the measurement-accuracy work. Logged for pass 9.

## Known limits going forward

- **Shoulder definition mismatch**: pass-4 photo extraction gave biacromial (MediaPipe between shoulders) at 38.23 cm; our vertex-pair landmark measures shoulder mesh extent at 41.78 cm. Either rebuild the shoulder landmark to match biacromial more closely, or accept the 3.55 cm offset as a measurement-definition reality.
- **Breast artifact**: one vertex near the left breast occasionally pops due to combo-corner clamping at extreme morph values. Doesn't show in silhouette views. Could be smoothed by post-mesh-cleanup or by tighter morph bounds.
- **Skin still flat-colored** until pass 9.
- **Pose still T-pose**.
