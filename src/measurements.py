"""Load and validate target measurements."""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any


REQUIRED_KEYS = (
    "gender",
    "stature_cm",
    "weight_kg",
    "bust_cm",
    "underbust_cm",
    "waist_cm",
    "hip_cm",
    "shoulder_breadth_cm",
    "thigh_circ_cm",
    "calf_circ_cm",
    "upper_arm_circ_cm",
    "forearm_circ_cm",
    "neck_circ_cm",
    "inseam_cm",
    "head_circ_cm",
    "arm_length_cm",
    "chest_depth_cm",
    "waist_depth_cm",
    "hip_depth_cm",
    "sitting_height_cm",
)


def load_measurements(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    with path.open() as f:
        data = json.load(f)

    missing = [k for k in REQUIRED_KEYS if k not in data]
    if missing:
        raise ValueError(f"target_measurements.json missing keys: {missing}")

    _sanity_check(data)
    return data


def _sanity_check(m: dict[str, Any]) -> None:
    stature = m["stature_cm"]
    weight = m["weight_kg"]
    waist = m["waist_cm"]
    bust = m["bust_cm"]
    underbust = m["underbust_cm"]
    hip = m["hip_cm"]

    if not 140 <= stature <= 210:
        warnings.warn(f"stature {stature} cm outside typical [140, 210]")

    bmi = weight / (stature / 100) ** 2
    if not 16 <= bmi <= 35:
        warnings.warn(f"BMI {bmi:.1f} outside typical [16, 35]")

    wh = waist / hip
    if not 0.4 <= wh <= 1.0:
        warnings.warn(f"waist/hip ratio {wh:.2f} outside [0.4, 1.0]")
    elif wh < 0.5:
        warnings.warn(f"extreme waist/hip ratio {wh:.2f}; primitive proxy may distort")

    if not bust > underbust > waist:
        warnings.warn("anatomical: expected bust > underbust > waist")

    if hip <= waist:
        warnings.warn("anatomical: expected hip > waist (default proxy assumption)")
