"""Identify landmark vertex indices on the default CharMorph mb_female mesh.

Same heuristic approach used for MHR in pass 6: top-of-head, feet, shoulder
pair, hip-widest pair, and convex-hull rings at bust/waist/hip Y-bands.
The default CharMorph mesh is the Caucasian basis, Z-up, in meters.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import ConvexHull

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def main() -> None:
    base = np.load(REPO_ROOT / "data" / "charmorph_female_base.npz")["vertices"].astype(np.float64)
    # CharMorph is Z-up; convert to (X right, Y up, Z forward) for landmark search
    v = np.column_stack([base[:, 0], base[:, 2], -base[:, 1]])
    print(f"verts: {v.shape}, y range: {v[:, 1].min():.3f} .. {v[:, 1].max():.3f} (meters)")

    H = float(v[:, 1].max())

    # Top of head: max-Y near midline
    near_midline = np.where(np.abs(v[:, 0]) < 0.02)[0]
    head_top = int(near_midline[np.argmax(v[near_midline, 1])])
    print(f"head_top: idx={head_top}, pos={v[head_top]}")

    # Feet: two lowest-Y clusters split by X sign
    y_order = np.argsort(v[:, 1])
    lowest_500 = y_order[:500]
    left_feet = lowest_500[v[lowest_500, 0] > 0]
    right_feet = lowest_500[v[lowest_500, 0] < 0]
    left_foot = int(left_feet[np.argmin(v[left_feet, 1])])
    right_foot = int(right_feet[np.argmin(v[right_feet, 1])])
    print(f"feet: L={left_foot} pos={v[left_foot]}, R={right_foot} pos={v[right_foot]}")

    # Shoulder pair: extreme |X| at ~84% stature (acromion)
    shoulder_y = H * 0.84
    band = np.where(np.abs(v[:, 1] - shoulder_y) < 0.03)[0]
    left_shoulder = int(band[np.argmax(v[band, 0])])
    right_shoulder = int(band[np.argmin(v[band, 0])])
    print(f"shoulder: L={left_shoulder} pos={v[left_shoulder]}, R={right_shoulder} pos={v[right_shoulder]}")

    # Hip widest pair: search Y range, find max width
    hip_search = np.linspace(H * 0.48, H * 0.55, 40)
    best_y, best_w = None, 0.0
    for y in hip_search:
        b = np.where(np.abs(v[:, 1] - y) < 0.01)[0]
        if len(b) < 8:
            continue
        # Exclude arms — torso/hip must be within ±30 cm of midline
        b = b[np.abs(v[b, 0]) < 0.30]
        if len(b) < 8:
            continue
        w = v[b, 0].max() - v[b, 0].min()
        if w > best_w:
            best_y, best_w = y, w
    band = np.where(np.abs(v[:, 1] - best_y) < 0.01)[0]
    band = band[np.abs(v[band, 0]) < 0.30]
    left_hip = int(band[np.argmax(v[band, 0])])
    right_hip = int(band[np.argmin(v[band, 0])])
    print(f"hip_widest Y={best_y:.3f}, width={best_w*100:.1f} cm: L={left_hip}, R={right_hip}")

    def hull_ring(y_target: float, band_half: float = 0.005, max_abs_x: float | None = None) -> list[int]:
        mask = np.abs(v[:, 1] - y_target) < band_half
        if max_abs_x is not None:
            mask = mask & (np.abs(v[:, 0]) < max_abs_x)
        idxs = np.where(mask)[0]
        if len(idxs) < 8:
            return []
        pts_xz = np.column_stack([v[idxs, 0], v[idxs, 2]])
        try:
            hull = ConvexHull(pts_xz)
        except Exception:
            return []
        # hull.vertices is CCW-ordered indices into pts_xz
        return idxs[hull.vertices].tolist()

    bust_y = H * 0.74
    waist_y = H * 0.66
    # Better hip Y: use the trochanter (slightly below pelvis MP marker)
    hip_y = best_y

    bust_ring = hull_ring(bust_y, band_half=0.005, max_abs_x=0.20)
    waist_ring = hull_ring(waist_y, band_half=0.005, max_abs_x=0.18)
    hip_ring = hull_ring(hip_y, band_half=0.005, max_abs_x=0.30)
    print(f"bust ring at y={bust_y:.3f}: {len(bust_ring)} verts")
    print(f"waist ring at y={waist_y:.3f}: {len(waist_ring)} verts")
    print(f"hip ring at y={hip_y:.3f}: {len(hip_ring)} verts")

    # Thigh / knee / calf rings — restrict X to one leg only so we don't
    # catch the other leg's vertices. Use a wider Y band for thigh/calf
    # (sparse default-mesh sampling there) and a 4-vert hull minimum.
    def leg_hull_ring(y_target: float, band_half: float = 0.01, x_min: float = 0.02, x_max: float = 0.30) -> list[int]:
        mask = np.abs(v[:, 1] - y_target) < band_half
        mask = mask & (v[:, 0] > x_min) & (v[:, 0] < x_max)
        idxs = np.where(mask)[0]
        if len(idxs) < 4:
            return []
        pts_xz = np.column_stack([v[idxs, 0], v[idxs, 2]])
        try:
            hull = ConvexHull(pts_xz)
        except Exception:
            return []
        return idxs[hull.vertices].tolist()

    thigh_y = H * 0.38
    knee_y = H * 0.26
    calf_y = H * 0.16
    thigh_ring = leg_hull_ring(thigh_y, band_half=0.015)
    knee_ring = leg_hull_ring(knee_y, band_half=0.008)
    calf_ring = leg_hull_ring(calf_y, band_half=0.015)
    print(f"thigh ring at y={thigh_y:.3f} (left leg): {len(thigh_ring)} verts")
    print(f"knee ring at y={knee_y:.3f}: {len(knee_ring)} verts")
    print(f"calf ring at y={calf_y:.3f}: {len(calf_ring)} verts")

    # Arm rings — upper arm, forearm. Default body's arms are nearly
    # vertical (close to body), so at shoulder-ish Y the arm sits in
    # x ∈ [0.03, 0.20] roughly (left side). Use YZ-hull because for a
    # vertical limb the cross-section is in the XZ plane same as a leg.
    def arm_hull_ring(y_target: float, x_min: float = 0.03, x_max: float = 0.30, band_half: float = 0.01) -> list[int]:
        mask = np.abs(v[:, 1] - y_target) < band_half
        mask = mask & (v[:, 0] > x_min) & (v[:, 0] < x_max)
        idxs = np.where(mask)[0]
        if len(idxs) < 4:
            return []
        pts_xz = np.column_stack([v[idxs, 0], v[idxs, 2]])
        try:
            hull = ConvexHull(pts_xz)
        except Exception:
            return []
        return idxs[hull.vertices].tolist()

    upper_arm_y = shoulder_y - 0.02
    forearm_y = shoulder_y - 0.10
    upper_arm_ring = arm_hull_ring(upper_arm_y, x_min=0.03, x_max=0.20, band_half=0.012)
    forearm_ring = arm_hull_ring(forearm_y, x_min=0.03, x_max=0.30, band_half=0.012)
    print(f"upper_arm ring at y={upper_arm_y:.3f}: {len(upper_arm_ring)} verts")
    print(f"forearm ring at y={forearm_y:.3f}: {len(forearm_ring)} verts")

    # Sanity: default-body perimeters (rough; will scale with body)
    def perim(ring):
        if not ring:
            return 0.0
        pts = v[ring]
        return float(np.linalg.norm(np.roll(pts, -1, axis=0) - pts, axis=1).sum())

    print(f"default body (in meters): stature={H:.3f}, bust={perim(bust_ring):.3f}, "
          f"waist={perim(waist_ring):.3f}, hip={perim(hip_ring):.3f}")

    landmarks = {
        "default_height_m": H,
        "head_top_idx": head_top,
        "foot_indices": [left_foot, right_foot],
        "left_shoulder_idx": left_shoulder,
        "right_shoulder_idx": right_shoulder,
        "left_hip_idx": left_hip,
        "right_hip_idx": right_hip,
        "bust_ring": bust_ring,
        "waist_ring": waist_ring,
        "hip_ring": hip_ring,
        "thigh_ring": thigh_ring,
        "knee_ring": knee_ring,
        "calf_ring": calf_ring,
        "upper_arm_ring": upper_arm_ring,
        "forearm_ring": forearm_ring,
        "coord_convention": "applied to vertices after Z-up→Y-up swap "
                            "(x_world, y_world=z_blender, z_world=-y_blender)",
    }
    out = REPO_ROOT / "data" / "charmorph_landmarks.json"
    with out.open("w") as f:
        json.dump(landmarks, f, indent=2)
    print(f"\nwrote {out.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
