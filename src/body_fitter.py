"""Body fitting: find MHR identity_coeffs that match target measurements.

Pure-Python autograd optimizer. CPU-friendly (~10–30 s per fit). No GPU,
no Sam3D, no external image-fitting models. Uses landmark vertex
indices on the MHR mesh (`data/mhr_landmarks.json`) to compute
differentiable measurements directly from the einsum forward pass.

Also exposes `load_identity_from_obj(...)` for when the body source is
a pre-built OBJ (MakeHuman, Blender sculpt, etc.) — pipeline still
renders it via the same path, just skipping the fit step.

`apply_identity_adjustment(...)` is the explicit "tweak manually" knob
from Meta's recommended workflow — exposed as a JSON config field, not
buried in code.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import torch
import trimesh

# Import torch BEFORE pymomentum so libtorch is RTLD_GLOBAL
import pymomentum.geometry as pym_geometry  # noqa: F401 — used via mhr_body

from src.mhr_body import (
    NUM_IDENTITY_BLENDSHAPES,
    NUM_FACE_EXPRESSION_BLENDSHAPES,
    _get_character,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
LANDMARKS_PATH = REPO_ROOT / "data" / "mhr_landmarks.json"


def _load_landmarks() -> dict:
    with LANDMARKS_PATH.open() as f:
        return json.load(f)


def _ring_perimeter(verts: torch.Tensor, ring_indices: list[int]) -> torch.Tensor:
    """Sum of consecutive distances around a ring of vertices (cm).

    verts: (V, 3) torch tensor. ring_indices: ordered (by angle around
    centroid) vertex indices forming a closed loop.
    """
    ring = verts[ring_indices]  # (R, 3)
    rolled = torch.roll(ring, shifts=-1, dims=0)
    seg = rolled - ring
    return torch.norm(seg, dim=1).sum()


def _mhr_forward_torch(
    base_verts: torch.Tensor,
    shape_vectors: torch.Tensor,
    identity_coeffs: torch.Tensor,
) -> torch.Tensor:
    """Build MHR mesh vertices from identity coeffs (face expression = 0).

    base_verts: (V, 3); shape_vectors: (NUM_IDENTITY+NUM_FACE, V, 3);
    identity_coeffs: (45,). Returns (V, 3).
    """
    id_dirs = shape_vectors[:NUM_IDENTITY_BLENDSHAPES]  # (45, V, 3)
    return base_verts + torch.einsum("k,kvc->vc", identity_coeffs, id_dirs)


NUM_BODY_BLENDSHAPES = 20  # first 20 of 45 identity components are body; rest are head+hands


def fit_identity_from_measurements(
    target: dict[str, float],
    *,
    init: np.ndarray | None = None,
    iterations: int = 200,
    lr: float = 0.05,
    regularization: float = 0.005,
    weights: dict[str, float] | None = None,
    body_components_only: bool = True,
    clip_magnitude: float | None = 4.0,
    verbose: bool = True,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Optimize identity_coeffs to make MHR mesh measurements match target.

    By default only the first 20 components (body identity) are
    optimized; head (20) and hands (5) stay at zero. This avoids
    distorting the head while chasing body circumference targets.
    `clip_magnitude` puts a soft cap on individual coefficient magnitude
    to keep the body in MHR's well-conditioned region.

    Returns (full_identity_coeffs_np (45,), history_dict).
    """
    lm = _load_landmarks()
    character = _get_character(lod=1)
    base = torch.tensor(np.asarray(character.mesh.vertices), dtype=torch.float32)
    shape_vecs = torch.tensor(np.asarray(character.blend_shape.shape_vectors), dtype=torch.float32)

    n_optim = NUM_BODY_BLENDSHAPES if body_components_only else NUM_IDENTITY_BLENDSHAPES
    if init is None:
        free = torch.zeros(n_optim, dtype=torch.float32, requires_grad=True)
    else:
        init_arr = np.asarray(init, dtype=np.float32)
        free = torch.tensor(init_arr[:n_optim], requires_grad=True)

    head_top = lm["head_top_idx"]
    foot_idxs = lm["foot_indices"]
    left_sh, right_sh = lm["left_shoulder_idx"], lm["right_shoulder_idx"]
    left_hip, right_hip = lm["left_hip_idx"], lm["right_hip_idx"]
    bust_ring = lm["bust_ring"]
    waist_ring = lm["waist_ring"]
    hip_ring = lm["hip_ring"]

    # Default weights — stature highest (sets scale), then big circumferences
    default_weights = {
        "stature_cm": 8.0,
        "hip_cm": 3.0,
        "waist_cm": 3.0,
        "bust_cm": 2.0,
        "shoulder_breadth_cm": 1.5,
    }
    if weights:
        default_weights.update(weights)

    optimizer = torch.optim.Adam([free], lr=lr)
    history: dict[str, list] = {"loss": [], "iter_residuals": []}

    for it in range(iterations):
        optimizer.zero_grad()
        # Build full 45-dim coeffs: free body components + zeros for head/hands
        if body_components_only:
            full_coeffs = torch.cat([free, torch.zeros(NUM_IDENTITY_BLENDSHAPES - n_optim)])
        else:
            full_coeffs = free
        verts = _mhr_forward_torch(base, shape_vecs, full_coeffs)

        # Differentiable measurements
        feet_y = (verts[foot_idxs[0], 1] + verts[foot_idxs[1], 1]) / 2.0
        stature = verts[head_top, 1] - feet_y

        shoulder_breadth = torch.norm(verts[left_sh] - verts[right_sh])
        hip_width = torch.norm(verts[left_hip] - verts[right_hip])

        bust = _ring_perimeter(verts, bust_ring)
        waist = _ring_perimeter(verts, waist_ring)
        hip = _ring_perimeter(verts, hip_ring)

        predicted = {
            "stature_cm": stature,
            "bust_cm": bust,
            "waist_cm": waist,
            "hip_cm": hip,
            "shoulder_breadth_cm": shoulder_breadth,
        }

        loss = torch.tensor(0.0)
        residuals = {}
        for key, target_val in target.items():
            if key not in predicted:
                continue
            w = default_weights.get(key, 1.0)
            r = predicted[key] - target_val
            loss = loss + w * r * r
            residuals[key] = float(r.detach().item())

        # L2 regularization keeps coeffs near 0 → bodies near the mean
        reg = regularization * (free * free).sum()
        # Soft cap: penalize |coeff| exceeding clip_magnitude with a stiff barrier
        if clip_magnitude is not None:
            over = torch.clamp(torch.abs(free) - clip_magnitude, min=0.0)
            reg = reg + 5.0 * (over * over).sum()
        total = loss + reg

        total.backward()
        optimizer.step()

        history["loss"].append(float(loss.detach().item()))
        if it % 20 == 0 or it == iterations - 1:
            if verbose:
                print(f"  iter {it:3d}: loss={float(loss):.3f}, "
                      f"residuals: stature {residuals.get('stature_cm', 0):+.2f}, "
                      f"hip {residuals.get('hip_cm', 0):+.2f}, "
                      f"waist {residuals.get('waist_cm', 0):+.2f}, "
                      f"bust {residuals.get('bust_cm', 0):+.2f}")
            history["iter_residuals"].append({"iter": it, **residuals})

    free_np = free.detach().cpu().numpy()
    full_np = np.zeros(NUM_IDENTITY_BLENDSHAPES, dtype=np.float32)
    full_np[:n_optim] = free_np
    return full_np, history


def apply_identity_adjustment(
    base: np.ndarray,
    deltas: dict[str | int, float],
) -> np.ndarray:
    """Add per-component deltas to a base identity vector.

    `deltas` keys can be ints or stringified ints — JSON config friendly.
    """
    out = np.asarray(base, dtype=np.float32).copy()
    for k, v in deltas.items():
        idx = int(k)
        if 0 <= idx < len(out):
            out[idx] += float(v)
    return out


def load_obj_as_mesh(obj_path: Path) -> trimesh.Trimesh:
    """Load an OBJ from disk as a trimesh. For the `source: "obj"` path,
    we skip MHR fitting and just render the supplied mesh directly.
    """
    m = trimesh.load(str(obj_path), process=False)
    if hasattr(m, "geometry") and m.geometry:
        m = list(m.geometry.values())[0]
    if not isinstance(m, trimesh.Trimesh):
        raise ValueError(f"loaded object is not a Trimesh: {type(m)}")
    return m
