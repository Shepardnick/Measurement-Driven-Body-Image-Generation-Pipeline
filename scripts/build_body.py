"""Single-command end-to-end body builder.

Usage:
    .venv-mhr/bin/python scripts/build_body.py configs/<body>.json

Dispatches on config["source"]:
  - "charmorph": apply MB-Lab named morphs to mb_female base
  - "obj":       load an external OBJ (MakeHuman, Blender sculpt, etc.)
  - "measurements" (legacy): MHR autograd-fit. Kept for reference; moved
    to legacy/mhr/. New work should use "charmorph".
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("PYOPENGL_PLATFORM", "egl")

import numpy as np
import trimesh

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.render_quality import render_views_quality


def _build_charmorph(config: dict) -> tuple[trimesh.Trimesh, dict]:
    """Build via CharMorph: preset → manual morph_values → optional autograd fit."""
    from src.charmorph_body import build_charmorph_body, load_preset

    cm = config.get("charmorph", {})
    preset_name = cm.get("preset")
    # Layer 1: preset
    morph_values: dict[str, float] = {}
    if preset_name:
        morph_values.update(load_preset(preset_name))
    # Layer 2: manual morph_values from config (back-compat alias: morph_overrides)
    morph_values.update(cm.get("morph_values") or cm.get("morph_overrides") or {})

    ethnicity = cm.get("ethnicity_l1", "Caucasian")

    fit_residuals: dict | None = None
    if cm.get("fit_to_measurements"):
        from src.charmorph_fitter import (
            fit_charmorph_morphs,
            expand_optimize_groups,
            load_landmarks,
        )
        from src.measurements import load_measurements

        target_path = cm.get("measurements_path") or config.get("measurements_path")
        if not target_path:
            raise ValueError("fit_to_measurements=true requires measurements_path")
        target = load_measurements(REPO_ROOT / target_path)

        # Stature scaling trick: body-shape morphs don't include overall scale.
        # Pre-normalize circumference targets to default-mesh-stature units
        # before fitting; post-scale the resulting mesh to actual stature.
        lm = load_landmarks()
        default_stature_cm = lm["default_height_m"] * 100.0
        scale = float(target["stature_cm"]) / default_stature_cm

        target_normalized = {"stature_cm": default_stature_cm}
        for k in ("bust_cm", "waist_cm", "hip_cm", "shoulder_breadth_cm"):
            if k in target:
                target_normalized[k] = float(target[k]) / scale

        # Drop Body_Size from optimize (it's an empty morph in CharMorph-db);
        # use uniform mesh scale post-fit to handle stature instead.
        optimize_keys = [k for k in expand_optimize_groups(cm.get("optimize_morphs", ["body"]))
                         if k != "Body_Size"]
        fit_cfg = cm.get("fitter", {})

        # Iterative pre-normalize/fit/measure/refine. After the first fit the
        # post-fit stature differs slightly from the default; recomputing the
        # scale factor and re-normalizing targets gets us within tolerance in
        # 2-3 iterations.
        from src.charmorph_body import build_charmorph_body
        from src.charmorph_fitter import forward_mesh, measure_torch
        import torch as _torch

        current_stature = default_stature_cm
        for refine_iter in range(3):
            scale = float(target["stature_cm"]) / current_stature
            target_normalized = {"stature_cm": current_stature}
            for k in ("bust_cm", "waist_cm", "hip_cm", "shoulder_breadth_cm"):
                if k in target:
                    target_normalized[k] = float(target[k]) / scale

            print(f"  refine iter {refine_iter}: assumed stature {current_stature:.2f} cm, "
                  f"scale {scale:.4f}")
            morph_values, fit_residuals = fit_charmorph_morphs(
                target_normalized,
                init=morph_values,
                optimize_keys=optimize_keys,
                ethnicity=ethnicity,
                iterations=fit_cfg.get("iterations", 300),
                lr=fit_cfg.get("lr", 0.03),
                regularization=fit_cfg.get("regularization", 0.02),
                verbose=(refine_iter == 0),
            )

            # Measure the as-fit mesh stature to update our scale estimate
            with _torch.no_grad():
                v = forward_mesh(morph_values, ethnicity=ethnicity)
                m = measure_torch(v, load_landmarks())
                actual_stature = float(m["stature_cm"])
            print(f"    fitter mesh stature: {actual_stature:.2f} cm")
            if abs(actual_stature - current_stature) < 0.2:
                break
            current_stature = actual_stature

    mesh = build_charmorph_body(
        morph_values=morph_values,
        ethnicity_l1=ethnicity,
        scale_to_cm=True,
    )
    record = {
        "preset": preset_name,
        "ethnicity_l1": ethnicity,
        "morph_values_applied": morph_values,
        "fit_residuals": fit_residuals,
    }
    return mesh, record


def _build_obj(config: dict) -> tuple[trimesh.Trimesh, dict]:
    obj_path = REPO_ROOT / config["obj_path"]
    m = trimesh.load(str(obj_path), process=False)
    if hasattr(m, "geometry") and m.geometry:
        m = list(m.geometry.values())[0]
    if not isinstance(m, trimesh.Trimesh):
        raise ValueError(f"OBJ at {obj_path} did not load as a Trimesh: {type(m)}")
    return m, {"obj_path": str(obj_path)}


def _build_measurements_legacy(config: dict) -> tuple[trimesh.Trimesh, dict]:
    """Legacy MHR autograd-fit path. Code moved to legacy/mhr/."""
    sys.path.insert(0, str(REPO_ROOT / "legacy" / "mhr"))
    from mhr_body import build_mhr_mesh
    from body_fitter import (
        apply_identity_adjustment,
        fit_identity_from_measurements,
    )
    from src.measurements import load_measurements

    target = load_measurements(REPO_ROOT / config["measurements_path"])
    fitter_cfg = config.get("fitter", {})
    from src.mhr_body_legacy_import_helper import _get_character  # noqa
    default_stature = 172.62
    stature_scale = float(target["stature_cm"]) / default_stature
    target_for_fit = {k: v for k, v in target.items()}
    for k in ("bust_cm", "waist_cm", "hip_cm", "shoulder_breadth_cm"):
        if k in target_for_fit:
            target_for_fit[k] = float(target_for_fit[k]) / stature_scale
    target_for_fit["stature_cm"] = default_stature
    coeffs, _ = fit_identity_from_measurements(
        target_for_fit,
        iterations=fitter_cfg.get("iterations", 300),
        body_components_only=True,
        clip_magnitude=fitter_cfg.get("clip_magnitude", 3.5),
        verbose=False,
    )
    adj = config.get("identity_adjustment", {}).get("deltas", {})
    if adj:
        coeffs = apply_identity_adjustment(coeffs, adj)
    mesh = build_mhr_mesh(identity_coeffs=coeffs, lod=config.get("lod", 1))
    current = float(mesh.bounds[1][1] - mesh.bounds[0][1])
    mesh.vertices = mesh.vertices * (float(target["stature_cm"]) / current)
    return mesh, {"identity_coeffs": coeffs.tolist()}


def _apply_stature_scale(mesh: trimesh.Trimesh, config: dict) -> tuple[trimesh.Trimesh, float | None]:
    """If the config specifies a target stature, uniformly scale to hit it."""
    stat_cfg = config.get("stature_scale")
    if stat_cfg in (None, "none"):
        return mesh, None
    if stat_cfg == "auto":
        # Auto-scale to the stature in measurements_path
        mpath = config.get("measurements_path")
        if not mpath:
            return mesh, None
        from src.measurements import load_measurements
        target_h = float(load_measurements(REPO_ROOT / mpath)["stature_cm"])
    elif isinstance(stat_cfg, (int, float)):
        target_h = float(stat_cfg)
    else:
        return mesh, None

    current = float(mesh.bounds[1][1] - mesh.bounds[0][1])
    scale = target_h / current
    mesh.vertices = mesh.vertices * scale
    return mesh, scale


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
    if source == "charmorph":
        mesh, record = _build_charmorph(config)
    elif source == "obj":
        mesh, record = _build_obj(config)
    elif source == "measurements":
        mesh, record = _build_measurements_legacy(config)
    else:
        raise ValueError(f"unknown source: {source!r}")

    mesh, scale = _apply_stature_scale(mesh, config)
    if scale is not None:
        print(f"  stature scaled by ×{scale:.3f}")

    mesh.visual.face_colors = [210, 180, 160, 255]
    mesh_path = out_dir / "mesh.obj"
    mesh.export(mesh_path)
    print(f"  wrote {mesh_path.relative_to(REPO_ROOT)} "
          f"({len(mesh.vertices)} verts, {len(mesh.faces)} faces)")

    r_cfg = config.get("render", {})
    angles = tuple(r_cfg.get("angles_deg", [0, 45, 90, 135, 180, 225, 270, 315]))
    res = r_cfg.get("resolution", 1024)
    skin = tuple(r_cfg.get("skin_rgb", [0.78, 0.62, 0.52]))
    print(f"  rendering {len(angles)} views at {res}×{res}...")
    written = render_views_quality(
        mesh, renders_dir, angles_deg=angles, resolution=res, skin_rgb=skin
    )
    for p in written:
        print(f"    {p.relative_to(REPO_ROOT)}")

    out_data = {
        "name": name,
        "config_path": str(config_path),
        "source": source,
        "stature_scale": scale,
        "build_record": record,
        "render_paths": [str(p.relative_to(REPO_ROOT)) for p in written],
        "mesh_path": str(mesh_path.relative_to(REPO_ROOT)),
    }
    with (out_dir / "identity.json").open("w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"  wrote {(out_dir / 'identity.json').relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
