# Pass 7 — Execution report

## Phases delivered

### Stage 1 — Verify data format ✓
- 18210-vertex MB-Lab female base mesh in `char.blend`, quad topology `faces.npy` (17288 quads → 34576 tris).
- L1 ethnic offsets: full per-vertex deltas in `.npy` (Caucasian, Asian, African, Latin, Elf, Anime).
- L2 packed morphs in `.npz`: `names` (uint8 null-separated UTF-8), `cnt` (per-morph), `idx` (flat vertex indices), `delta` (flat 3-D offsets), sliced by cumsum.
- 232 morphs in `__main__.npz` + 213 in ethnic-specific `Caucasian.npz`.
- 30+ body archetype presets (`type_fitness_model`, `type_athletic`, `type_hourglass01/02`, `type_ideal_shapely`, etc.) under `presets/*.json`.

### Stage 2 — Headless Blender base extraction ✓
- `scripts/extract_charmorph_base.py`: opens `char.blend`, identifies the largest mesh (`mb_female`, 18210 verts), exports vertices to `data/charmorph_female_base.npz`.
- Blender 4.0.2 (apt) used Python 3.12 system Python; required `apt install python3-numpy` to make numpy available to Blender's runtime.
- One-shot operation — Blender is not a runtime dependency.

### Stage 3 — Pure-Python adapter (`src/charmorph_body.py`) ✓
- Loads base mesh + faces + morph dicts with `@lru_cache` (fast repeated builds).
- Triangulates quads on load.
- Implements MB-Lab's combo-morph format: 1-D sliders use `_min`/`_max` corners (coeff 1.0); 2-D combos (Mass+Tone) use 4 corners with `get_combo_item_value(arr_idx, values) = max(sum(v_i * sign_i), 0) * 0.5` where sign_i = +1/-1 per bit i of arr_idx.
- Converts Z-up (CharMorph) → Y-up (our pipeline) at boundary. Scales m → cm.
- API: `build_charmorph_body(morph_values, ethnicity_l1, scale_to_cm) → trimesh`, plus `load_preset(name) → dict`, `list_presets()`, `list_morph_names()`.

### Stage 4 — `build_body.py` updated ✓
- Dispatches on `source ∈ {"charmorph", "obj", "measurements"}`.
- `charmorph` config schema:
  ```json
  {
    "source": "charmorph",
    "charmorph": {
      "preset": "type_ideal_shapely",
      "ethnicity_l1": "Caucasian",
      "morph_overrides": { "Torso_BreastTone": 0.9, ... }
    },
    "stature_scale": 193.04
  }
  ```
- `stature_scale` accepts a number, "auto" (reads from measurements_path), or null.
- Manual tuning is per-morph in `morph_overrides` — semantically meaningful names, no anonymous-PCA-component tuning.

### Stage 5 — MHR-era code archived ✓
Moved to `legacy/mhr/` (preserves git history; cleanly out of main paths):
- `src/mhr_body.py`
- `src/body_fitter.py`
- `scripts/build_mhr_default.py`
- `scripts/explore_mhr_identity.py`
- `data/mhr_landmarks.json`

`build_body.py` keeps a `source: "measurements"` legacy branch that imports from `legacy/mhr/` for reference; new work should use `source: "charmorph"`.

### Stage 6 — End-to-end validation ✓
`configs/subject_a_charmorph.json` runs `type_ideal_shapely` preset with manual overrides for bust shape, glute mass/tone, waist size, abdominal tone, leg/arm tone. Output:

- `outputs/subject_a_charmorph/mesh.obj`: 18210 verts, 34576 faces, 193 cm tall after stature scale ×1.126
- `outputs/subject_a_charmorph/renders/view_*.png`: 8 views, 1024×1024

Visual comparison front view vs MHR's previous render:

| | MHR (pass 6) | CharMorph (pass 7) |
|---|---|---|
| Body | soft, saggy, average | toned, defined musculature visible |
| Breasts | pendulous, droopy | perky, anatomically positioned |
| Abs/torso | scooped/concave | flat with visible tone, navel defined |
| Face | bald, near-featureless, eyes closed | face with eyes/nose/mouth/ears/jaw visible |
| Hands | claw-fingers | natural fingers and palms |
| Feet | stub | toes visible |
| Glutes | flat/average | rounded, anatomical |

The structural complaint from earlier ("saggy/gross") is resolved. The body looks like a real female athletic body, not a clay mannequin.

## Architectural wins (in addition to visual)

1. **No PCA entanglement.** Each named morph affects a specific anatomical region. `Torso_BreastTone=0.9` does not change waist or shoulders. The Meta dev's warning that motivated this entire pass no longer applies.

2. **Manual tuning is first-class.** Editing `configs/<body>.json::charmorph.morph_overrides` and re-running takes seconds. The output identity is fully reproducible (just commit the JSON).

3. **Body source is pluggable.** `source: "obj"` accepts any external mesh (MakeHuman, Blender sculpt, DAZ export). `source: "charmorph"` is the primary parametric path. `source: "measurements"` (MHR legacy) is still functional if needed.

4. **Blender is not a runtime dep.** One-shot extraction → runtime is pure Python (numpy + trimesh + pyrender). The pipeline runs on any machine with our Python deps.

5. **30+ preset archetypes ship for free.** `type_fitness_model`, `type_athletic`, `type_hourglass01/02`, `type_ideal_shapely`, `type_pear01/02`, `type_rectangle01`, `type_extreme_bodybuilder`, etc. — and ethnic variants of each.

## Known limits / pass-8+ work

- **No measurement-driven autograd optimizer for named morphs yet.** Would be straightforward (same machinery as MHR autograd, but operating on a vector indexed by named morphs; presets are dense starting points). Currently you hit measurements by editing the JSON until it looks right.
- **Pose**: still T-pose. Body comes out in straight-arm rest. CharMorph supports poses via the `poses/` directory but we don't read them yet.
- **Hair**: none. CharMorph ships `hair.blend` and `hairstyles/` but they're separate; out of scope here.
- **Skin texture**: solid color. The PBR material in `render_quality.py` could be upgraded to use the actual MB-Lab skin textures shipped under `textures/`.
- **The `_pycache_` issue and stale `.venv-mhr` name.** The venv was named for MHR but works fine for CharMorph; rename is cosmetic.

## Files added/changed

Added:
- `passes/pass-7-charmorph-migration/v1.md`
- `passes/pass-7-charmorph-migration/report.md`
- `src/charmorph_body.py`
- `scripts/extract_charmorph_base.py`
- `configs/subject_a_charmorph.json`
- `data/charmorph_female_base.npz`
- `external/CharMorph/` (gitignored)
- `external/CharMorph-db/` (gitignored)
- `outputs/subject_a_charmorph/` and `outputs/charmorph_test/`

Moved (archive):
- `src/mhr_body.py` → `legacy/mhr/mhr_body.py`
- `src/body_fitter.py` → `legacy/mhr/body_fitter.py`
- `scripts/build_mhr_default.py` → `legacy/mhr/`
- `scripts/explore_mhr_identity.py` → `legacy/mhr/`
- `data/mhr_landmarks.json` → `legacy/mhr/`

Modified:
- `scripts/build_body.py`: now dispatches on source ∈ {charmorph, obj, measurements}
- `passes/README.md`: pass 7 entry
- `.gitignore`: external/CharMorph* added
