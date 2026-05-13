"""Single-command end-to-end body builder.

Usage:
    .venv-mhr/bin/python scripts/build_body.py configs/<body>.json

Reads a config, runs the fitting / OBJ-load path per `source`, applies
manual identity_adjustment deltas, scales to stature, renders 8 views,
and writes everything to outputs/<name>/.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("PYOPENGL_PLATFORM", "egl")

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.body_fitter import (
    apply_identity_adjustment,
    fit_identity_from_measurements,
    load_obj_as_mesh,
)
from src.measurements import load_measurements
from src.mhr_body import build_mhr_mesh
from src.render_quality import render_views_quality


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: build_body.py <config.json>")
        sys.exit(2)
    config_path = Path(sys.argv[1])
    with config_path.open() as f:
        config = json.load(f)

    name = config["name"]
    out_dir = REPO_ROOT / "outputs" / name
    renders_dir = out_dir / "renders"
    out_dir.mkdir(parents=True, exist_ok=True)
    renders_dir.mkdir(parents=True, exist_ok=True)

    print(f"[{name}] source = {config['source']}")

    source = config["source"]
    if source == "measurements":
        target = load_measurements(REPO_ROOT / config["measurements_path"])
        print(f"  target: stature={target['stature_cm']}, "
              f"bust={target['bust_cm']}, waist={target['waist_cm']}, "
              f"hip={target['hip_cm']}, shoulder={target['shoulder_breadth_cm']}")
        fitter_cfg = config.get("fitter", {})

        # The 20 body-shape components don't include overall scale (height).
        # Strategy: scale-normalize the target measurements to MHR's native
        # default stature (~172.62 cm) before fitting, then scale the mesh
        # up to the actual target stature. This way the optimizer fits a
        # shape that's the right proportions, and uniform scaling preserves
        # all proportions including circumferences.
        from src.mhr_body import _get_character
        char = _get_character(lod=1)
        default_stature = float(np.asarray(char.mesh.vertices)[:, 1].max())
        stature_scale = float(target["stature_cm"]) / default_stature
        print(f"  default MHR stature: {default_stature:.2f} cm; "
              f"target: {target['stature_cm']:.2f} cm; scale: {stature_scale:.4f}")

        # Normalize target circumferences to default-size space
        target_for_fit = {k: v for k, v in target.items()}
        for k in ("bust_cm", "waist_cm", "hip_cm", "shoulder_breadth_cm",
                  "thigh_circ_cm", "knee_circ_cm", "calf_circ_cm",
                  "upper_arm_circ_cm", "forearm_circ_cm", "neck_circ_cm"):
            if k in target_for_fit and isinstance(target_for_fit[k], (int, float)):
                target_for_fit[k] = float(target_for_fit[k]) / stature_scale
        target_for_fit["stature_cm"] = default_stature

        coeffs, history = fit_identity_from_measurements(
            target_for_fit,
            iterations=fitter_cfg.get("iterations", 300),
            lr=fitter_cfg.get("lr", 0.1),
            regularization=fitter_cfg.get("regularization", 0.005),
            clip_magnitude=fitter_cfg.get("clip_magnitude", 3.5),
            body_components_only=fitter_cfg.get("body_components_only", True),
            verbose=True,
        )
        # Apply manual deltas AFTER fitting
        adj = config.get("identity_adjustment", {}).get("deltas", {})
        if adj:
            print(f"  applying identity_adjustment.deltas: {adj}")
            coeffs = apply_identity_adjustment(coeffs, adj)

        mesh = build_mhr_mesh(identity_coeffs=coeffs, lod=config.get("lod", 1))

        # Uniform scale to actual target stature — circumferences fitted at
        # default-stature scale up proportionally and hit their real targets.
        current = float(mesh.bounds[1][1] - mesh.bounds[0][1])
        target_h = float(target["stature_cm"])
        scale = target_h / current
        mesh.vertices = mesh.vertices * scale
        print(f"  stature scale: {current:.2f} → {target_h:.2f} cm  (×{scale:.3f})")

        identity_record = coeffs.tolist()

    elif source == "obj":
        obj_path = REPO_ROOT / config["obj_path"]
        print(f"  loading {obj_path}")
        mesh = load_obj_as_mesh(obj_path)
        identity_record = None
        history = None

    else:
        raise ValueError(f"unknown source: {source}")

    mesh.visual.face_colors = [210, 180, 160, 255]
    mesh_path = out_dir / "mesh.obj"
    mesh.export(mesh_path)
    print(f"  wrote {mesh_path.relative_to(REPO_ROOT)} "
          f"({len(mesh.vertices)} verts, {len(mesh.faces)} faces)")

    # Render
    r_cfg = config.get("render", {})
    angles = tuple(r_cfg.get("angles_deg", [0, 45, 90, 135, 180, 225, 270, 315]))
    res = r_cfg.get("resolution", 1024)
    skin = tuple(r_cfg.get("skin_rgb", [0.78, 0.62, 0.52]))
    print(f"  rendering {len(angles)} views at {res}×{res}...")
    written = render_views_quality(
        mesh, renders_dir, angles_deg=angles, resolution=res, skin_rgb=skin
    )
    for p in written:
        print(f"    wrote {p.relative_to(REPO_ROOT)}")

    # Verification: re-measure the (post-scaled) mesh and compare to target
    verification = {}
    if source == "measurements":
        from src.body_fitter import _load_landmarks, _ring_perimeter
        import torch
        v_t = torch.tensor(mesh.vertices, dtype=torch.float32)
        lm = _load_landmarks()
        feet_y = (v_t[lm["foot_indices"][0]][1] + v_t[lm["foot_indices"][1]][1]) / 2
        verification = {
            "stature_cm": float(v_t[lm["head_top_idx"]][1] - feet_y),
            "shoulder_breadth_cm": float(torch.norm(v_t[lm["left_shoulder_idx"]] - v_t[lm["right_shoulder_idx"]])),
            "hip_width_cm": float(torch.norm(v_t[lm["left_hip_idx"]] - v_t[lm["right_hip_idx"]])),
            "bust_cm": float(_ring_perimeter(v_t, lm["bust_ring"])),
            "waist_cm": float(_ring_perimeter(v_t, lm["waist_ring"])),
            "hip_cm": float(_ring_perimeter(v_t, lm["hip_ring"])),
        }
        target = load_measurements(REPO_ROOT / config["measurements_path"])
        verification = {
            k: {"actual": round(v, 2),
                "target": round(float(target.get(k, 0.0)), 2),
                "residual": round(v - float(target.get(k, 0.0)), 2)}
            for k, v in verification.items()
            if k in target
        }
        print(f"  verification:")
        for k, d in verification.items():
            print(f"    {k}: target {d['target']:.2f}, actual {d['actual']:.2f}, residual {d['residual']:+.2f}")

    out_data = {
        "name": name,
        "config_path": str(config_path),
        "identity_coeffs": identity_record,
        "verification_cm": verification,
        "render_paths": [str(p.relative_to(REPO_ROOT)) for p in written],
        "mesh_path": str(mesh_path.relative_to(REPO_ROOT)),
    }
    with (out_dir / "identity.json").open("w") as f:
        json.dump(out_data, f, indent=2)
    print(f"  wrote {(out_dir / 'identity.json').relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
