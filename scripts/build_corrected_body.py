"""End-to-end pass 3 driver.

target_measurements.json -> A2B SVR clipped β -> SMPL-X T-pose mesh ->
hip inflation + waist compression corrections -> posed mesh -> 8 PNG renders.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import trimesh

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.a2b_adapter import predict_betas
from src.anthropometry_adapter import measure_mesh
from src.measurements import load_measurements
from src.mesh_correction import correct_to_target_circumference
from src.render import render_views
from src.smplx_body import (
    SMPLX_MODEL_DIR,
    build_smplx_mesh,
    fit_beta,
    relaxed_standing_pose,
)


MEASUREMENTS_PATH = REPO_ROOT / "target_measurements.json"
OUT_DIR = REPO_ROOT / "outputs" / "smplx"
RENDER_DIR = OUT_DIR / "renders"
MESH_PATH = OUT_DIR / "mesh_corrected.obj"
VERIF_RAW_PATH = OUT_DIR / "verification_raw.json"
VERIF_CORRECTED_PATH = OUT_DIR / "verification_corrected.json"
HISTORY_PATH = OUT_DIR / "correction_history.json"


def _measure_in_meters_to_cm(verts_m: np.ndarray) -> dict:
    # measure_mesh accepts the (10475, 3) array and returns measurements in cm
    return measure_mesh(verts_m, gender="female")


def _verify_report(measured: dict, target: dict) -> dict:
    report = {}
    for key, target_cm in target.items():
        if not key.endswith("_cm") or key not in measured:
            continue
        actual = float(measured[key])
        report[key] = {
            "target_cm": round(float(target_cm), 2),
            "actual_cm": round(actual, 2),
            "error_cm": round(actual - target_cm, 2),
        }
    return report


def main() -> None:
    if not SMPLX_MODEL_DIR.exists():
        raise SystemExit(
            f"SMPL-X weights not found at {SMPLX_MODEL_DIR}; abort"
        )
    os.environ["SMPLX_MODEL_DIR"] = str(SMPLX_MODEL_DIR)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)

    measurements = load_measurements(MEASUREMENTS_PATH)
    print(f"target: stature {measurements['stature_cm']} cm, "
          f"waist {measurements['waist_cm']} cm, hip {measurements['hip_cm']} cm, "
          f"W/H {measurements['waist_cm']/measurements['hip_cm']:.2f}")

    beta = fit_beta(measurements, model_type="svr", clip=5.0)
    print(f"β (SVR clipped ±5): "
          f"[{beta.min():+.2f}, {beta.max():+.2f}], "
          f"mean={beta.mean():+.2f}")

    mesh_raw, verts_raw, faces = build_smplx_mesh(beta, pose=None, gender="female")

    measured_raw = _measure_in_meters_to_cm(verts_raw)
    raw_report = _verify_report(measured_raw, measurements)
    print(f"\nraw SMPL-X (T-pose):")
    for k, v in raw_report.items():
        print(f"  {k}: {v['actual_cm']:.2f} (target {v['target_cm']:.2f}, "
              f"err {v['error_cm']:+.2f})")
    with VERIF_RAW_PATH.open("w") as f:
        json.dump(raw_report, f, indent=2)

    # --- Corrections ---
    verts = verts_raw.copy()
    history_all = {}

    print(f"\ninflating hip toward {measurements['hip_cm']:.1f} cm...")
    verts, hist_hip = correct_to_target_circumference(
        verts,
        faces,
        canonical_key="hip_cm",
        target_cm=float(measurements["hip_cm"]),
        sigma_y_m=0.06,
        anisotropy_posterior=1.4,
        measure_fn=_measure_in_meters_to_cm,
        max_iters=4,
    )
    history_all["hip"] = hist_hip

    print(f"compressing waist toward {measurements['waist_cm']:.1f} cm...")
    verts, hist_waist = correct_to_target_circumference(
        verts,
        faces,
        canonical_key="waist_cm",
        target_cm=float(measurements["waist_cm"]),
        sigma_y_m=0.04,
        anisotropy_posterior=1.0,
        measure_fn=_measure_in_meters_to_cm,
        max_iters=4,
    )
    history_all["waist"] = hist_waist

    measured_corr = _measure_in_meters_to_cm(verts)
    corr_report = _verify_report(measured_corr, measurements)
    print(f"\ncorrected SMPL-X:")
    for k, v in corr_report.items():
        print(f"  {k}: {v['actual_cm']:.2f} (target {v['target_cm']:.2f}, "
              f"err {v['error_cm']:+.2f})")
    with VERIF_CORRECTED_PATH.open("w") as f:
        json.dump(corr_report, f, indent=2)
    with HISTORY_PATH.open("w") as f:
        json.dump(history_all, f, indent=2, default=str)

    # --- Pose + render ---
    print(f"\napplying relaxed standing pose + building posed mesh...")
    pose = relaxed_standing_pose(shoulder_drop_deg=70.0)
    # The corrections were applied to the T-pose mesh. To re-pose, the
    # cleanest path is to re-run smplx with the same β AND apply the
    # delta from T-pose verts -> corrected verts as a custom offset.
    # smplx doesn't expose that hook, so we approximate: take the raw
    # posed mesh and apply the same delta-from-T-pose to its vertices.
    _, verts_posed_raw, _ = build_smplx_mesh(beta, pose=pose, gender="female")
    delta = verts - verts_raw
    verts_posed = verts_posed_raw + delta

    # Convert m -> cm so the render module's bounding-box logic (in cm
    # equivalent to pass 1) stays consistent.
    verts_cm = verts_posed * 100.0
    mesh_cm = trimesh.Trimesh(vertices=verts_cm, faces=faces, process=False)
    mesh_cm.visual.face_colors = [210, 180, 160, 255]
    mesh_cm.export(MESH_PATH)
    print(f"wrote {MESH_PATH.relative_to(REPO_ROOT)}")

    print(f"rendering 8 views (this is slower with 20k faces; ~30-60s)...")
    written = render_views(mesh_cm, RENDER_DIR, resolution=1024)
    for p in written:
        print(f"  wrote {p.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
