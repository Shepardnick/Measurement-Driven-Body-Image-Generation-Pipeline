"""Adapter around kaulquappe23/a2b_human_mesh.

Wraps `AnthroToBeta` from `external/a2b_human_mesh/anthro/models.py`. The
upstream model expects a 36-element measurement vector ordered by
`anthro_names` (defined in `anthro/names.py`), in **meters**.

Our canonical `target_measurements.json` uses different key names and
centimeter units. This adapter translates between the two conventions and
fills any unmeasured anthro slots with reasonable defaults drawn from
A2B's `example_measurements.json` (scaled by the stature ratio so the
filler grows with the subject's height).
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path
from typing import Any

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
A2B_ROOT = REPO_ROOT / "external" / "a2b_human_mesh"
A2B_MODELS_DIR = A2B_ROOT / "anthro" / "a2b_models"
A2B_EXAMPLE_PATH = A2B_ROOT / "anthro" / "example_measurements.json"


# Canonical-key (ours, cm) -> A2B anthro_names (theirs, meters).
# A2B has left/right pairs for limb measurements; we mirror our single value
# to both sides. Things we don't have in target_measurements.json get filled
# from the A2B example file (scaled by stature ratio).
CANONICAL_TO_A2B: dict[str, list[str]] = {
    "stature_cm": ["height length"],
    "shoulder_breadth_cm": ["shoulder width length"],
    "head_circ_cm": ["head circumference"],
    "neck_circ_cm": ["neck circumference"],
    "waist_cm": ["waist circumference"],
    "bust_cm": ["chest circumference"],
    "hip_cm": ["hip circumference"],
    "upper_arm_circ_cm": ["left arm circumference", "right arm circumference"],
    "forearm_circ_cm": ["left forearm circumference", "right forearm circumference"],
    "thigh_circ_cm": ["left thigh circumference", "right thigh circumference"],
    "calf_circ_cm": ["left calf circumference", "right calf circumference"],
    "hand_length_cm": ["left hand length", "right hand length"],
    "arm_length_cm": ["left arm length", "right arm length"],
    "foot_length_cm": ["left heel to toe length", "right heel to toe length"],
}


def _ensure_a2b_on_path() -> None:
    if not A2B_ROOT.exists():
        raise RuntimeError(
            f"A2B repo not found at {A2B_ROOT}. Clone it with:\n"
            f"  git clone https://github.com/kaulquappe23/a2b_human_mesh.git "
            f"{A2B_ROOT}"
        )
    p = str(A2B_ROOT)
    if p not in sys.path:
        sys.path.insert(0, p)


def _load_anthro_names() -> list[str]:
    _ensure_a2b_on_path()
    from anthro.names import anthro_names
    return list(anthro_names)


def _load_example_measurements() -> dict[str, float]:
    with A2B_EXAMPLE_PATH.open() as f:
        data = json.load(f)
    first_subject = next(iter(data.values()))
    return {k: float(v) for k, v in first_subject.items()}


def _build_anthro_vector(measurements: dict[str, Any]) -> dict[str, float]:
    """Build the A2B 36-element measurement dict (meters) from our cm dict."""
    anthro_names = _load_anthro_names()
    example = _load_example_measurements()
    example_stature_m = example["height length"]
    our_stature_m = measurements["stature_cm"] / 100.0
    stature_ratio = our_stature_m / example_stature_m

    result: dict[str, float] = {}

    for canonical_key, a2b_keys in CANONICAL_TO_A2B.items():
        if canonical_key in measurements:
            value_m = measurements[canonical_key] / 100.0
            for k in a2b_keys:
                result[k] = value_m

    missing = [n for n in anthro_names if n not in result]
    if missing:
        for name in missing:
            if name not in example:
                warnings.warn(
                    f"anthro_name {name!r} not in A2B example; using zero"
                )
                result[name] = 0.0
                continue
            result[name] = example[name] * stature_ratio

    return result


def predict_betas(
    measurements: dict[str, Any],
    model_type: str = "nn",
    gender: str | None = None,
) -> np.ndarray:
    """Run A2B inference on a canonical measurements dict.

    Returns a (num_betas,) numpy array of SMPL-X shape parameters. For
    female models num_betas=10; male=11; neutral=16.
    """
    _ensure_a2b_on_path()
    import torch
    from anthro.models import AnthroToBeta

    if gender is None:
        gender = measurements.get("gender", "neutral")
    gender = gender.lower()
    if gender not in {"female", "male", "neutral"}:
        raise ValueError(f"unsupported gender: {gender}")

    if model_type == "nn":
        suffix = "uniform_nn.pth" if gender != "neutral" else "uniform_ext_nn.pth"
    elif model_type == "svr":
        suffix = "uniform_ext_svr.pth"
    else:
        raise ValueError(f"model_type must be 'nn' or 'svr', got {model_type!r}")

    candidate = A2B_MODELS_DIR / f"{gender}_{suffix}"
    if not candidate.exists():
        available = sorted(p.name for p in A2B_MODELS_DIR.glob("*.pth"))
        raise FileNotFoundError(
            f"A2B model {candidate.name} not found in {A2B_MODELS_DIR}. "
            f"Available: {available}"
        )

    anthro_names = _load_anthro_names()
    anthro_dict = _build_anthro_vector(measurements)
    vec = np.array([anthro_dict[name] for name in anthro_names], dtype=np.float32)
    tensor = torch.from_numpy(vec).unsqueeze(0)

    model = AnthroToBeta(str(candidate), model_type=model_type)
    betas = model.predict(tensor)
    if hasattr(betas, "detach"):
        betas = betas.detach().cpu().numpy()
    return np.asarray(betas).squeeze()
