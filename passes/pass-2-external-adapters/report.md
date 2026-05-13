# Pass 2 — Execution report

## What ran

`scripts/smoke_test_adapters.py` against `target_measurements.json` (W/H 0.52, female, 193.04 cm). Output: `outputs/adapter_smoke_test.json`.

## A2B adapter — verified end-to-end

Both pretrained model variants ran successfully on our measurements:

| Variant | Shape | β range | Notes |
| ------- | ----- | ------- | ----- |
| `female_uniform_nn.pth` | (10,) | [-14.61, +14.46] | mean +1.73, std 7.25 |
| `female_uniform_ext_svr.pth` | (10,) | [-18.34, +17.14] | mean -1.87, std 10.03 |

**β magnitudes are far outside the typical SMPL-X range** (normal is roughly ±3, sometimes up to ±5 for unusual bodies). Both models report values > 14 on multiple components, with `magnitude_ok = false` (threshold < 8.0). This is exactly the failure mode the design doc's §10 predicts for W/H 0.52: A2B's regression head was trained on more conventional anthropometry and extrapolates by pushing β to extreme values that may produce a distorted mesh.

Implication for pass 3: when SMPL-X weights land, expect the rendered mesh from these β to look caricatured — bust/hip overshoot, possibly degenerate proportions elsewhere. The SVR head's magnitudes (up to 18) are worse than NN's (up to 14.6); we should prefer NN by default. Either way, β optimization (pass 4) will have to ratchet these values back toward the training distribution while trading off measurement residuals.

### Corrections to the design doc

| Doc claimed | Actual |
| ----------- | ------ |
| 36 measurements expected | 36 (correct; pre-pass WebFetch said 34 — that was wrong) |
| `A2BModel.from_pretrained(...)` Python API | `AnthroToBeta(model_path, model_type="svr"\|"nn")`; `.predict(tensor)` |
| Pretrained weights gated | Ship in `anthro/a2b_models/`, no academic registration |
| One model file per gender | Two: `*_uniform_nn.pth` and `*_uniform_ext_svr.pth` |
| 10 β for all genders | Female=10, male=11, **neutral=16** |

Measurement names: see `external/a2b_human_mesh/anthro/names.py:anthro_names` (36 entries, meters). Our canonical → upstream mapping is `CANONICAL_TO_A2B` in `src/a2b_adapter.py`. Unmapped slots (head length, footwidth, heel-to-ball, etc.) are filled from A2B's `example_measurements.json` scaled by stature ratio — a serviceable proxy but not principled; revisit if results look bad in pass 3.

## SMPL-Anthropometry adapter — API verified, full smoke test deferred

The upstream import path is `from measure import MeasureBody`. `MeasureBody(model_type)` is a factory `__new__` that returns `MeasureSMPLX()` for `"smplx"`. `MeasureSMPLX.__init__` immediately calls `smplx.SMPLX(self.body_model_path, ext="pkl").faces`, which requires `data/smplx/SMPLX_*.pkl` files to be present.

In this environment we don't have those weights (academic registration on smpl-x.is.tue.mpg.de). `_ensure_smplx_weights` in `src/anthropometry_adapter.py` checks for an `SMPLX_MODEL_DIR` env var pointing to a directory of `.pkl` files; if set, it symlinks them into the upstream repo's expected layout. With `SMPLX_MODEL_DIR` unset, `measure_mesh` raises with a clear "weights required" message.

Until that env var is provided, the most we can confirm is:
- The upstream module imports cleanly (after installing `smplx` + `plotly` deps)
- The `MeasureBody`/`MeasureSMPLX`/`Measurer` class structure matches what we wrote the adapter against
- The `from_verts(verts: torch.Tensor)` and `measure(names: list[str])` signatures match the upstream source

### Corrections to the design doc

| Doc claimed | Actual |
| ----------- | ------ |
| Single `Measurer` class | `Measurer` is the abstract base; concrete classes are `MeasureSMPL`/`MeasureSMPLX`; `MeasureBody` is the factory |
| `measurer.measure_from_vertices(vertices, names=...)` | `measurer.from_verts(verts)` then `measurer.measure(names)` (two-step) |
| Differentiable through PyTorch | NumPy-based, **not differentiable**. Some early steps (`torch.matmul(joint_regressor, verts)`) are torch but the subsequent measurement code (plane cuts, circumference summation) goes through NumPy. |
| Lives at `measurer.measure_from_vertices()` return value | Lives at `measurer.measurements` dict after calling `.measure(names)` |

## Open items for pass 3

1. **Get SMPL-X weights.** Without them the SMPL-Anthropometry adapter is half-built and the rendering pipeline can't move past the primitive proxy.
2. **Validate A2B β on a real mesh.** Once we can run SMPL-X, feed the smoke-test β into `body_model(betas=betas)` and render — confirm whether the caricature concern is real or whether magnitude > 14 still produces a recognizable body. (Pretty sure it'll be distorted; need to see how badly.)
3. **Decide A2B variant.** NN's smaller magnitudes suggest it's the better starting point. SVR may be more stable for typical bodies but worse for extreme.
4. **Plan the optimization fallback for pass 4.** Given A2B's magnitude blowout, direct β optimization with strong regularization (pulling β toward zero) plus measurement loss will likely beat A2B-alone for this body. The differentiability question becomes urgent here: do we (a) reimplement measurements in PyTorch, (b) use finite differences, or (c) pivot to a different upstream that's already differentiable?

## What's in the repo after this pass

- `src/a2b_adapter.py` — full implementation, end-to-end working
- `src/anthropometry_adapter.py` — full implementation, gated on SMPL-X weights
- `scripts/smoke_test_adapters.py` — reproducible adapter check
- `outputs/adapter_smoke_test.json` — captured A2B β outputs and SMPL-Anthropometry import status
- `external/a2b_human_mesh/` and `external/SMPL-Anthropometry/` — both cloned, gitignored
- `requirements.txt` — torch, scikit-learn, smplx, plotly added
