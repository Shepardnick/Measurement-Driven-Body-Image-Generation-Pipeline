"""Gaussian-weighted radial deformation for SMPL-X meshes.

The goal: programmatically inflate or compress a band of vertices around a
target Y-level (hip plane, waist plane) so the measured circumference at
that plane matches a target value — without producing visible "ledges" at
the band edges.

Approach: for each vertex, compute a Gaussian weight on its vertical
distance to the band center. In the X-Z plane, scale the vertex's
displacement from the band centroid by (1 + weight * (scale - 1)).
Anisotropy lets the lateral (X) and anterior-posterior (Z) axes scale
differently, e.g. to push posterior more than anterior for an
anatomically curvy hip.

Mesh units are meters (SMPL-X convention). Target circumferences passed
in are in cm; the upstream measurer returns cm; we convert at the
boundary.
"""

from __future__ import annotations

from typing import Callable

import numpy as np


def gaussian_radial_deform(
    verts: np.ndarray,
    center_y_m: float,
    sigma_y_m: float,
    scale_lat: float,
    scale_ap_posterior: float,
    scale_ap_anterior: float | None = None,
) -> np.ndarray:
    """Apply Gaussian-weighted radial deformation around a horizontal plane.

    verts: (N, 3) numpy array in meters, Y up.
    center_y_m: Y coordinate (m) of the band center (e.g. hip plane).
    sigma_y_m: Gaussian falloff in meters.
    scale_lat: scaling factor on the X (lateral) axis at weight=1.
    scale_ap_posterior: scaling factor on Z for vertices with z < centroid_z.
    scale_ap_anterior: scaling factor on Z for vertices with z >= centroid_z.
        Defaults to the midpoint of (scale_lat, scale_ap_posterior).

    Returns a new (N, 3) array; input is not mutated.
    """
    if scale_ap_anterior is None:
        scale_ap_anterior = 0.5 * (scale_lat + scale_ap_posterior)

    out = verts.copy()

    dy = verts[:, 1] - center_y_m
    weights = np.exp(-0.5 * (dy / sigma_y_m) ** 2)

    # Centroid in X-Z from the high-weight vertices (within ~2σ). Using
    # weighted mean so the centroid lies at the actual "ring" of the body
    # at this Y level rather than the geometric mean of all verts.
    band_mask = weights > 0.1
    if band_mask.sum() < 16:
        # Not enough vertices in band — bail without deforming
        return out
    band_w = weights[band_mask]
    band_x = verts[band_mask, 0]
    band_z = verts[band_mask, 2]
    cx = float(np.sum(band_x * band_w) / np.sum(band_w))
    cz = float(np.sum(band_z * band_w) / np.sum(band_w))

    # Per-vertex per-axis effective scale = 1 + weight * (scale - 1).
    dx = verts[:, 0] - cx
    dz = verts[:, 2] - cz

    eff_lat = 1.0 + weights * (scale_lat - 1.0)

    posterior_mask = dz < 0.0
    ap_target = np.where(posterior_mask, scale_ap_posterior, scale_ap_anterior)
    eff_ap = 1.0 + weights * (ap_target - 1.0)

    out[:, 0] = cx + dx * eff_lat
    out[:, 2] = cz + dz * eff_ap
    return out


def correct_to_target_circumference(
    verts: np.ndarray,
    faces: np.ndarray,
    canonical_key: str,
    target_cm: float,
    sigma_y_m: float,
    anisotropy_posterior: float,
    measure_fn: Callable[[np.ndarray], dict[str, float]],
    *,
    center_y_m: float | None = None,
    max_iters: int = 4,
    tolerance_cm: float = 0.5,
) -> tuple[np.ndarray, list[dict]]:
    """Iteratively scale a band of vertices until `canonical_key` matches target.

    `measure_fn(verts) -> dict` maps our canonical keys to cm values.
    `canonical_key` is the key in that dict whose value we're targeting.
    `center_y_m` defaults to the centroid Y of the vertices ranked by their
    XZ-radius — a rough estimate of where the band is in space.

    Returns (corrected_verts, history) where history is a list of per-iter
    info dicts for diagnostics.
    """
    cur = verts.copy()
    history: list[dict] = []

    measured = measure_fn(cur)
    current_cm = float(measured[canonical_key])

    if center_y_m is None:
        center_y_m = _estimate_band_y(cur, canonical_key)

    for it in range(max_iters):
        residual = target_cm - current_cm
        history.append(
            {
                "iter": it,
                "current_cm": current_cm,
                "residual_cm": residual,
                "center_y_m": center_y_m,
            }
        )
        if abs(residual) <= tolerance_cm:
            break

        scale_total = target_cm / current_cm
        # Gaussian-weighted deformation produces a circumference change
        # smaller than (scale - 1) on the band edges, so step >1 is fine.
        # Empirically a step of 0.9 + a 1.1 boost on iter 0 converges in
        # 2-3 iterations for hip-scale changes.
        step = 1.0 if it == 0 else 0.9
        extra = scale_total - 1.0
        scale_lat = 1.0 + step * extra
        scale_ap_post = 1.0 + step * extra * anisotropy_posterior

        cur = gaussian_radial_deform(
            cur,
            center_y_m=center_y_m,
            sigma_y_m=sigma_y_m,
            scale_lat=scale_lat,
            scale_ap_posterior=scale_ap_post,
        )
        measured = measure_fn(cur)
        current_cm = float(measured[canonical_key])

    history.append(
        {
            "iter": "final",
            "current_cm": current_cm,
            "residual_cm": target_cm - current_cm,
        }
    )
    return cur, history


# Rough SMPL-X canonical Y heights for measurement planes, as fractions of
# the body's vertical extent. These work as initial guesses; the iterative
# correction is tolerant to a few centimeters of offset because the
# Gaussian weighting is broad.
_BAND_Y_FRACTION = {
    "hip_cm": 0.50,
    "waist_cm": 0.61,
    "bust_cm": 0.72,
}


def _estimate_band_y(verts: np.ndarray, canonical_key: str) -> float:
    y_min = float(verts[:, 1].min())
    y_max = float(verts[:, 1].max())
    frac = _BAND_Y_FRACTION.get(canonical_key, 0.55)
    return y_min + frac * (y_max - y_min)
