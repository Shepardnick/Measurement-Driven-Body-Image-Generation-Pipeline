"""PyTorch autograd optimizer over CharMorph named morphs.

Same machinery used for MHR in pass 6, adapted for CharMorph's mesh +
named-morph storage:
  * Forward pass: apply combo + single morphs to the mb_female base
    (Z-up Blender coords → Y-up render coords inside the forward pass)
  * Differentiable measurements: vertex-distance pairs + ring perimeters
    on landmark vertex indices identified once on the default mesh
  * Loss: weighted MSE against target measurements + L2 regularization
    toward an initial morph dict (typically a preset)
  * Bounds: clamp morph values to [0, 1] via projection after each step

Combo morphs are handled by parameterizing over the underlying SLIDER
NAMES (e.g. `Torso_BreastMass`, `Torso_BreastTone` independently). The
combo-corner math runs inside the forward pass; clamps are non-smooth
at corner boundaries but the gradient elsewhere is clean.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import torch

from src.charmorph_body import (
    _decode_npz,
    _load_base,
    _load_l1,
    _load_l2_main,
    _load_l2_ethnic,
    list_presets,
    load_preset,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
LANDMARKS_PATH = REPO_ROOT / "data" / "charmorph_landmarks.json"
CATALOG_PATH = REPO_ROOT / "data" / "charmorph_morph_catalog.json"


@lru_cache(maxsize=1)
def load_landmarks() -> dict:
    with LANDMARKS_PATH.open() as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_catalog() -> dict:
    with CATALOG_PATH.open() as f:
        return json.load(f)


# Default "body" group — measurement-relevant body sliders worth optimizing.
# Excludes face/head detail and very-fine knee/wrist sliders that don't move
# circumferences meaningfully.
def expand_optimize_groups(groups: Iterable[str]) -> list[str]:
    cat = load_catalog()
    out: set[str] = set()
    for g in groups:
        if g == "body":
            # Primary measurement-driving body sliders + global Body_Size for stature
            for name, meta in cat.items():
                if not meta.get("measurement_relevant"):
                    continue
                region = meta.get("region", "")
                if region in {
                    "torso", "torso/breast", "abdomen", "waist", "pelvis",
                    "stomach", "shoulders", "neck", "arms", "legs",
                    "body global",
                }:
                    out.add(name)
        elif g == "all_measurement_relevant":
            for name, meta in cat.items():
                if meta.get("measurement_relevant"):
                    out.add(name)
        elif g == "shape_only":
            # Same as body but exclude SIZE sliders that should be user-set
            # (so the fitter handles toning/proportion, user handles breast/glute size)
            exclude = {"Torso_BreastMass", "Pelvis_GluteusMass", "Pelvis_GluteusSize"}
            for name, meta in cat.items():
                if not meta.get("measurement_relevant"):
                    continue
                if name in exclude:
                    continue
                region = meta.get("region", "")
                if region in {
                    "torso", "abdomen", "waist", "pelvis", "stomach",
                    "shoulders", "neck", "arms", "legs", "body global",
                }:
                    out.add(name)
        else:
            # treat as literal slider name
            out.add(g)
    return sorted(out)


# ---- Forward pass: morph values → mesh vertices (Y-up cm), differentiable ----


def _suffix(arr_idx: int, n_dims: int) -> str:
    return "-".join("max" if (arr_idx >> i) & 1 else "min" for i in range(n_dims))


def _enum_combos(lookup: dict) -> dict[str, list[str]]:
    """Find compound morph stems and their constituent slider names."""
    stems: dict[str, list[str]] = {}
    for name in lookup:
        if not name.endswith("_max-max"):
            continue
        stem = name[: -len("_max-max")]
        if "_" not in stem:
            continue
        part, rest = stem.split("_", 1)
        if "-" not in rest:
            continue
        dims = rest.split("-")
        sliders = [f"{part}_{d}" for d in dims]
        stems[stem] = sliders
    return stems


def _build_apply_plan(lookup: dict) -> tuple[dict[str, list], dict[str, list]]:
    """Pre-compute, per slider name:
      single_plan[slider] = [(idx_array, delta_tensor, sign), ...]
        sign +1 means apply at value>=0 (the _max corner)
        sign -1 means apply at value<0 (the _min corner)
      combo_plan[combo_stem] = (list_of_slider_names, [(idx, delta) for arr_idx in 0..N-1])
    """
    combo_stems = _enum_combos(lookup)
    combo_plan: dict[str, tuple[list[str], list]] = {}
    sliders_in_combo: set[str] = set()
    for stem, sliders in combo_stems.items():
        n_dims = len(sliders)
        corner_morphs = []
        ok = True
        for arr_idx in range(1 << n_dims):
            corner_name = f"{stem}_{_suffix(arr_idx, n_dims)}"
            if corner_name not in lookup:
                ok = False
                break
            corner_morphs.append(lookup[corner_name])
        if not ok:
            continue
        combo_plan[stem] = (sliders, corner_morphs)
        for s in sliders:
            sliders_in_combo.add(s)

    single_plan: dict[str, list] = {}
    for name, (idx, delta) in lookup.items():
        m = name.rsplit("_", 1)
        if len(m) != 2:
            continue
        base_name, suffix = m
        if suffix not in ("max", "min"):
            continue
        if "-" in base_name.split("_", 1)[-1]:
            continue  # part of a combo
        if base_name in sliders_in_combo:
            continue
        single_plan.setdefault(base_name, []).append((idx, delta, +1 if suffix == "max" else -1))
    return single_plan, combo_plan


@lru_cache(maxsize=8)
def _torch_plan(ethnicity: str, device: str = "cpu"):
    """All torch tensors needed for the forward pass, cached."""
    lookup = {**_load_l2_main(), **_load_l2_ethnic(ethnicity)}
    single_plan, combo_plan = _build_apply_plan(lookup)

    dev = torch.device(device)
    single_torch = {
        slider: [
            (torch.from_numpy(idx).long().to(dev),
             torch.from_numpy(delta).float().to(dev),
             sign)
            for (idx, delta, sign) in entries
        ]
        for slider, entries in single_plan.items()
    }
    combo_torch = {
        stem: (
            sliders,
            [
                (torch.from_numpy(idx).long().to(dev),
                 torch.from_numpy(delta).float().to(dev))
                for (idx, delta) in corners
            ],
        )
        for stem, (sliders, corners) in combo_plan.items()
    }

    base_np = _load_base().copy().astype(np.float32)
    if ethnicity != "Caucasian":
        base_np = base_np - _load_l1("Caucasian") + _load_l1(ethnicity)
    base_t = torch.from_numpy(base_np).float().to(dev)
    return base_t, single_torch, combo_torch


def forward_mesh(
    morph_values: dict[str, torch.Tensor | float],
    ethnicity: str = "Caucasian",
    device: str = "cpu",
) -> torch.Tensor:
    """Apply all morphs and return (V, 3) vertex tensor in Y-up cm coords."""
    base_t, single_torch, combo_torch = _torch_plan(ethnicity, device)
    verts = base_t.clone()

    # Convert any float values to 0-d tensors for uniform handling
    def _val(name: str) -> torch.Tensor | None:
        if name not in morph_values:
            return None
        v = morph_values[name]
        if isinstance(v, torch.Tensor):
            return v
        return torch.tensor(float(v), dtype=verts.dtype, device=verts.device)

    # Single (1D) sliders
    for slider, entries in single_torch.items():
        v = _val(slider)
        if v is None:
            continue
        for idx, delta, sign in entries:
            # max corner if sign=+1 and v>0; min corner if sign=-1 and v<0
            if sign > 0:
                coef = torch.clamp(v, min=0.0)
            else:
                coef = torch.clamp(-v, min=0.0)
            if float(coef.detach()) == 0.0:
                continue
            verts = verts.clone()
            verts.index_add_(0, idx, coef * delta)

    # Combo (2D+) sliders
    for stem, (sliders, corners) in combo_torch.items():
        values = [_val(s) for s in sliders]
        if all(v is None for v in values):
            continue
        # Replace None with zero tensor
        values = [
            v if v is not None else torch.tensor(0.0, dtype=verts.dtype, device=verts.device)
            for v in values
        ]
        n_dims = len(sliders)
        coeff_norm = 2.0 / (1 << n_dims)
        for arr_idx in range(1 << n_dims):
            idx, delta = corners[arr_idx]
            # per-bit sign
            s = torch.tensor(0.0, dtype=verts.dtype, device=verts.device)
            for val_idx, vv in enumerate(values):
                sign = 1.0 if (arr_idx >> val_idx) & 1 else -1.0
                s = s + vv * sign
            coef = torch.clamp(s, min=0.0) * coeff_norm
            if float(coef.detach()) == 0.0:
                continue
            verts = verts.clone()
            verts.index_add_(0, idx, coef * delta)

    # Z-up → Y-up: (x, y, z) → (x, z, -y); meters → cm
    out = torch.stack([verts[:, 0], verts[:, 2], -verts[:, 1]], dim=1) * 100.0
    return out


# ---- Differentiable measurements ----


def measure_torch(verts: torch.Tensor, landmarks: dict) -> dict[str, torch.Tensor]:
    """All measurements in cm. verts is (V, 3) torch tensor in Y-up cm."""
    feet = (verts[landmarks["foot_indices"][0], 1] + verts[landmarks["foot_indices"][1], 1]) / 2.0
    stature = verts[landmarks["head_top_idx"], 1] - feet

    shoulder = torch.linalg.norm(
        verts[landmarks["left_shoulder_idx"]] - verts[landmarks["right_shoulder_idx"]]
    )
    hip_w = torch.linalg.norm(
        verts[landmarks["left_hip_idx"]] - verts[landmarks["right_hip_idx"]]
    )

    def perim(ring: list[int]) -> torch.Tensor:
        if not ring:
            return torch.tensor(0.0, dtype=verts.dtype, device=verts.device)
        pts = verts[ring]
        return torch.linalg.norm(pts - torch.roll(pts, shifts=-1, dims=0), dim=1).sum()

    out = {
        "stature_cm": stature,
        "shoulder_breadth_cm": shoulder,
        "hip_width_cm": hip_w,
        "bust_cm": perim(landmarks["bust_ring"]),
        "waist_cm": perim(landmarks["waist_ring"]),
        "hip_cm": perim(landmarks["hip_ring"]),
    }
    # Optional rings — present if landmarks were built with limb rings
    if landmarks.get("thigh_ring"):
        out["thigh_circ_cm"] = perim(landmarks["thigh_ring"]) * 2.0  # ring is one leg; doubling gives "per-leg sum" — actually leave as single leg
        out["thigh_circ_cm"] = perim(landmarks["thigh_ring"])
    if landmarks.get("knee_ring"):
        out["knee_circ_cm"] = perim(landmarks["knee_ring"])
    if landmarks.get("calf_ring"):
        out["calf_circ_cm"] = perim(landmarks["calf_ring"])
    if landmarks.get("upper_arm_ring"):
        out["upper_arm_circ_cm"] = perim(landmarks["upper_arm_ring"])
    if landmarks.get("forearm_ring"):
        out["forearm_circ_cm"] = perim(landmarks["forearm_ring"])
    return out


# ---- Fitter ----


# Reasonable loss weights — stature anchors scale, circumferences carry most signal
DEFAULT_WEIGHTS = {
    "stature_cm": 8.0,
    "bust_cm": 3.0,
    "waist_cm": 4.0,
    "hip_cm": 4.0,
    "shoulder_breadth_cm": 1.0,
}


def fit_charmorph_morphs(
    target: dict[str, float],
    init: dict[str, float],
    optimize_keys: list[str],
    *,
    ethnicity: str = "Caucasian",
    iterations: int = 300,
    lr: float = 0.03,
    regularization: float = 0.02,
    weights: Optional[dict[str, float]] = None,
    verbose: bool = True,
) -> tuple[dict[str, float], dict[str, dict[str, float]]]:
    """Find morph_values that hit target measurements.

    `init`: starting dict (preset values + manual overrides).
    `optimize_keys`: subset of slider names to treat as torch.Parameters.
        All other sliders stay fixed at their init value.
    Returns (final_morph_values, per_measurement_residuals).
    """
    weights = {**DEFAULT_WEIGHTS, **(weights or {})}
    landmarks = load_landmarks()

    # Split into optimized vs fixed
    optimize_set = set(optimize_keys)
    fixed = {k: float(v) for k, v in init.items() if k not in optimize_set}
    # Initialize at preset value if present; otherwise small positive so the
    # clamp(v, min=0) has non-zero gradient. Without this nudge, optimize-set
    # morphs absent from the preset have zero gradient and never move.
    init_vec = torch.tensor(
        [float(init.get(k, 0.05)) for k in optimize_keys],
        dtype=torch.float32,
    )
    # Ensure no init value is exactly 0
    init_vec = torch.where(init_vec < 0.01, torch.full_like(init_vec, 0.05), init_vec)
    raw = torch.nn.Parameter(init_vec.clone())

    optimizer = torch.optim.Adam([raw], lr=lr)
    history: list[dict] = []

    for it in range(iterations):
        optimizer.zero_grad()
        # Clamp values to [0, 1] via projection inside the forward pass
        clamped = torch.clamp(raw, 0.0, 1.0)

        morph_values = {**fixed, **{k: clamped[i] for i, k in enumerate(optimize_keys)}}
        verts = forward_mesh(morph_values, ethnicity=ethnicity)
        m = measure_torch(verts, landmarks)

        loss = torch.tensor(0.0)
        residuals: dict[str, float] = {}
        for key, target_val in target.items():
            if key not in m:
                continue
            w = weights.get(key, 1.0)
            r = m[key] - float(target_val)
            loss = loss + w * r * r
            residuals[key] = float(r.detach())

        reg = regularization * ((clamped - init_vec) ** 2).sum()
        total = loss + reg
        total.backward()
        optimizer.step()
        with torch.no_grad():
            raw.clamp_(0.0, 1.0)

        if verbose and (it % 25 == 0 or it == iterations - 1):
            res_str = ", ".join(f"{k.replace('_cm', '')}={v:+.2f}" for k, v in residuals.items())
            print(f"  iter {it:3d}: loss={float(loss):.3f}  {res_str}")
        history.append({"iter": it, "loss": float(loss.detach()), "residuals": residuals})

    final_vec = raw.detach().cpu().numpy()
    final_values = {**fixed, **{k: float(final_vec[i]) for i, k in enumerate(optimize_keys)}}

    # Compute final residuals with a clean (no-grad) forward pass
    with torch.no_grad():
        verts_final = forward_mesh(final_values, ethnicity=ethnicity)
        m_final = measure_torch(verts_final, landmarks)
    final_residuals = {
        k: {
            "target_cm": float(target[k]),
            "actual_cm": float(m_final[k]),
            "residual_cm": float(m_final[k]) - float(target[k]),
        }
        for k in target
        if k in m_final
    }
    return final_values, final_residuals
