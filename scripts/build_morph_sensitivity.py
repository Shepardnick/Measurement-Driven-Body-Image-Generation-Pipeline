"""Build a sensitivity catalog: for every CharMorph slider, compute how
much each body measurement changes when that slider goes from 0 → 1.

Output:
  - data/charmorph_morph_sensitivity.json
  - passes/pass-10-sensitivity-catalog/morph_sensitivity.md

Method: finite differences at the default mesh. For each slider, set its
value to 1.0 and all others to 0, compute the mesh, compute measurements,
diff against the default-mesh baseline. The diff is cm-per-unit-slider.

This is a *single-point* sensitivity at the default mesh. Combo morphs
have piecewise behavior; the table records the cleanest case (single
slider at 1, paired slider at 0).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.charmorph_body import _load_l2_main, _load_l2_ethnic
from src.charmorph_fitter import (
    forward_mesh,
    load_landmarks,
    load_catalog,
    measure_torch,
)


OUT_JSON = REPO_ROOT / "data" / "charmorph_morph_sensitivity.json"
OUT_MD = REPO_ROOT / "passes" / "pass-10-sensitivity-catalog" / "morph_sensitivity.md"


def main() -> None:
    landmarks = load_landmarks()
    catalog = load_catalog()
    print(f"catalog has {len(catalog)} sliders")

    # Baseline: all morphs at 0
    with torch.no_grad():
        baseline_verts = forward_mesh({}, ethnicity="Caucasian")
        baseline = {k: float(v) for k, v in measure_torch(baseline_verts, landmarks).items()}
    print("baseline measurements (default mesh):")
    for k, v in baseline.items():
        print(f"  {k}: {v:.2f} cm")
    print()

    measurement_keys = list(baseline.keys())
    sensitivities: dict[str, dict[str, float]] = {}

    for i, slider in enumerate(sorted(catalog.keys())):
        with torch.no_grad():
            verts = forward_mesh({slider: 1.0}, ethnicity="Caucasian")
            m = {k: float(v) for k, v in measure_torch(verts, landmarks).items()}
        sensitivities[slider] = {k: round(m[k] - baseline[k], 3) for k in measurement_keys}
        if i % 25 == 0:
            print(f"  {i:3d}/{len(catalog)}: {slider}")

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSON.open("w") as f:
        json.dump({
            "baseline_cm": {k: round(v, 3) for k, v in baseline.items()},
            "sensitivity_cm_per_unit_slider": sensitivities,
            "note": (
                "Each slider's value range is [0, 1]. The sensitivity number "
                "is the cm change in that measurement when this slider alone "
                "is set to 1.0 (all others at 0) vs the default mesh. Combo "
                "morphs interact: with the paired slider at non-zero, the "
                "effective sensitivity differs from this single-point table."
            ),
        }, f, indent=2, sort_keys=True)
    print(f"\nwrote {OUT_JSON.relative_to(REPO_ROOT)}")

    # Markdown summary
    lines = ["# CharMorph morph sensitivity catalog\n"]
    lines.append("For every slider, the cm change in each body measurement when the "
                 "slider goes from 0 → 1 (evaluated at the default mesh, all other "
                 "morphs at 0).\n")
    lines.append("\nUse this as a manual lookup table. Example: to make the waist 5 cm "
                 "smaller, look up the slider whose `waist_cm` is the most negative; "
                 "if it's -3.0 cm/unit, push it to ~1.67 (out of 1.0 = clamp).\n")
    lines.append("\n## Baseline (default-mesh measurements, cm)\n")
    for k, v in baseline.items():
        lines.append(f"- **{k}**: {v:.2f}")

    lines.append("\n## Top 10 influencers per measurement\n")
    for meas in measurement_keys:
        ranked = sorted(
            sensitivities.items(),
            key=lambda kv: -abs(kv[1].get(meas, 0.0)),
        )[:10]
        # filter out zero-effect
        ranked = [(n, d) for n, d in ranked if abs(d[meas]) > 0.05]
        if not ranked:
            continue
        lines.append(f"\n### `{meas}`")
        lines.append("| slider | Δ cm | region |")
        lines.append("| --- | --- | --- |")
        for name, deltas in ranked:
            d = deltas[meas]
            region = catalog.get(name, {}).get("region", "?")
            sign = "+" if d > 0 else ""
            lines.append(f"| **{name}** | {sign}{d:.2f} | {region} |")

    lines.append("\n## Full table grouped by region\n")
    # Group sliders by region
    region_to_sliders: dict[str, list[str]] = {}
    for s in sorted(catalog.keys()):
        r = catalog[s]["region"]
        region_to_sliders.setdefault(r, []).append(s)
    for region in sorted(region_to_sliders):
        sliders = region_to_sliders[region]
        # Only show regions where at least one slider has a nonzero effect on body measurements
        has_effect = any(any(abs(sensitivities[s][m]) > 0.05 for m in measurement_keys) for s in sliders)
        if not has_effect:
            continue
        lines.append(f"\n### {region}\n")
        header_meas = [m for m in measurement_keys]
        short_names = {
            "stature_cm": "stature", "shoulder_breadth_cm": "shldr",
            "hip_width_cm": "hipW", "bust_cm": "bust", "waist_cm": "waist",
            "hip_cm": "hip", "thigh_circ_cm": "thigh", "knee_circ_cm": "knee",
            "calf_circ_cm": "calf", "upper_arm_circ_cm": "uArm", "forearm_circ_cm": "fArm",
        }
        header = "| slider | " + " | ".join(short_names.get(m, m) for m in header_meas) + " |"
        sep = "| --- | " + " | ".join("---" for _ in header_meas) + " |"
        lines.append(header)
        lines.append(sep)
        for s in sliders:
            d = sensitivities[s]
            cells = []
            for m in header_meas:
                v = d.get(m, 0.0)
                cells.append(f"{v:+.2f}" if abs(v) > 0.05 else "·")
            lines.append(f"| `{s}` | " + " | ".join(cells) + " |")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines))
    print(f"wrote {OUT_MD.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
