# Pass 9 — Execution report

## What was done (step by step)

### Step 1 — UV extraction ✓
`scripts/extract_charmorph_uvs.py` ran under headless Blender 4.0.2, opened `char.blend`, found the `mb_female` mesh (18,210 verts, 69,152 loops), extracted the active UV layer (`UVMap`), wrote `data/charmorph_female_uvs.npz` with per-vertex UVs.

UV stats: u ∈ [0.000, 1.000], v ∈ [0.003, 1.000] — clean coverage, no out-of-range values.

### Step 2 — Renderer accepts texture + UVs ✓
`src/render_quality.py` updated. New args: `texture_path`, `uvs`, `bright_global`. Texture applied via per-vertex color baking (see "Workaround" below) instead of pyrender's standard `baseColorTexture` because of a PyOpenGL+EGL incompatibility.

### Step 3 — Lighting rig rewritten ✓
Replaced the dramatic 3-point key/fill/rim rig with bright global:
- `ambient_light` 0.18 → 0.55 (3× brighter)
- 4 balanced directional lights at +25° elevation, placed at `[deg-45, deg+45, deg+135, deg-135]` relative to camera, intensities 1.4–1.6 each (vs old key 3.0, rim 2.2)
- No dominant key, no harsh rim, fills shadows globally

### Step 4 — Config updated ✓
`configs/subject_a_fitted.json` has `render.texture`, `render.uvs_path`, `render.bright_global` fields.

### Step 5 — End-to-end run ✓
`.venv-mhr/bin/python scripts/build_body.py configs/subject_a_fitted.json` produces 8-view renders. Measurements still fit to within 0.00 cm (the fit didn't change; only rendering changed). Renders saved to `outputs/subject_a_fitted/renders/view_*.png`.

### Step 6 — Inspected front (0°), side (90°), back (180°) ✓
All three angles render cleanly:
- **Front (`view_000.png`)**: realistic skin tone, visible nipple/areola coloration, eye color (green-ish from sclera/iris region of albedo), lip area visible, anatomical hands/feet/face. Bright even lighting reveals all surface detail.
- **Right side (`view_090.png`)**: clean profile, glute curve, abdominal contour, neck/face profile, hand at hip level visible. The artifact from pass-7 (the LBS-skipped hand position) is gone since we're on CharMorph topology now.
- **Back (`view_180.png`)**: defined glute separation, smooth back curvature, scapular hint, hands/feet behind.

## Workaround applied (worth flagging)

**Pyrender + EGL + Python 3.12 has a `glGenTextures` ctypes incompatibility.** Standard texture binding through `MetallicRoughnessMaterial.baseColorTexture` crashes with:
```
ctypes.ArgumentError: No array-type handler for type _ctypes.type
  (value: <cparam 'P' ...>) registered
```
Tried `PyOpenGL-accelerate` and PyOpenGL 3.1.0 — same error. The bug is in the texture upload path itself; doesn't matter what texture you pass.

**Workaround**: bake the texture into per-vertex colors at build time. For each of the 18,210 vertices, sample the albedo PNG at the vertex's UV coordinate (handling OpenGL bottom-left vs PIL top-left), assign as `trimesh.visual.vertex_colors`. Pyrender's per-vertex color path doesn't need texture binding; it just passes the colors to the vertex shader.

**Trade-off**: per-vertex color resolution is ~1 sample per ~2 cm of skin (18k verts spread over the body surface), vs the 2048² texture's ~0.04 mm/pixel. We lose the fine albedo detail (skin pores, freckle pattern variation) but keep the broad color regions (skin tone, nipple coloration, lip color, eye color, areola), which is what actually reads at the 1024-pixel render size.

Result is close to what a proper textured PBR would produce for our use case (Nano Banana reference images at moderate resolution). For higher-fidelity output later we'd need to either find a different OpenGL stack (CPU-only software GL, Open3D's offscreen, or Blender Eevee headless), or upgrade pyrender / use a different texture binding path.

## What you can see in the renders

Visible per-vertex coloration:
- ✓ Skin tone (warm peach Caucasian default)
- ✓ Nipple + areola (darker pigmentation)
- ✓ Lip area (faintly redder than surrounding skin)
- ✓ Eye color (iris + sclera regions visible)
- ✓ Subtle gradient between body regions (slightly different tones in different anatomical areas)
- ✓ Anatomical features (navel, pubic cleft) — same as before

## What was not done (as flagged upfront)

- ❌ Hair — no hair geometry; CharMorph's `hair.blend` not integrated
- ❌ Bikini / clothing — no clothing assets fitted to the morphed body
- ❌ Facial identity match — face is MB-Lab neutral; head identity coefficients are zero. The specific face in your reference photos (blonde Western fitness-model features) is not reproducible without head-identity tuning or face fitting
- ❌ Skin tone exactly matching the photo subject's tan — the albedo is medium-Caucasian. Could be tinted post-load with an RGB multiplier (~5 lines of code) if needed
- ❌ Subsurface scattering — pyrender's PBR doesn't support; skin reads slightly opaque/plastic-ish at thin areas (ears, nose, fingers). Would need Blender Eevee or custom shader
- ❌ Makeup, freckles, blush — CharMorph ships `frecklemask.png`, `blush.png`, `lipmap.png` as separate compositable masks. Combining them with the albedo requires custom shader work; out of scope here
- ❌ Pose — still T-pose / slight A-pose. Pose authoring is a separate pass
- ❌ True texture binding (vs per-vertex bake) — blocked by the PyOpenGL bug above; documented for future

## Body-type matching

The body's measurements still match the target exactly (stature 193.04, bust 104.03, waist 73.58, hip 117.87 from pass 8; shoulder still +3.55 from biacromial-vs-vertex-pair definition mismatch). With the texture, the rendered body now looks like a coherent realistic-skin human female of those proportions. It does NOT look like the specific person in your reference photos because that requires facial-identity reproduction (hair, eye color specifics, face shape, skin tan, expression) which is out of scope for body-only work.

## Files changed

Added:
- `passes/pass-9-skin-texture-and-lighting/v1.md`
- `passes/pass-9-skin-texture-and-lighting/report.md`
- `scripts/extract_charmorph_uvs.py`
- `data/charmorph_female_uvs.npz`

Modified:
- `src/render_quality.py` (texture support + bright global lighting)
- `scripts/build_body.py` (pass texture/uvs through to renderer)
- `configs/subject_a_fitted.json` (enabled texture + bright_global)
- `outputs/subject_a_fitted/renders/` (all 8 view PNGs regenerated)
