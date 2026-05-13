"""Adapter around DavidBoja/SMPL-Anthropometry.

The upstream `MeasureBody("smplx")` is a factory that returns a
`MeasureSMPLX` instance. Its `__init__` loads the SMPL-X face topology via
the `smplx` package, which requires `data/smplx/SMPLX_{GENDER}.pkl` files
present at the upstream repo's data root.

Without SMPL-X weights, this adapter cannot be instantiated. It will raise
a clear error in that case. Once weights are available (registration on
smpl-x.is.tue.mpg.de), set `SMPLX_MODEL_DIR` env var or pass the path to
`measure_mesh`, and this adapter wraps the upstream API to return
measurements in cm under our canonical key names.

The library is NumPy-based — gradients do not flow through measurements.
A differentiable measurement layer is deferred to a later pass.
"""

from __future__ import annotations

import os
import shutil
import sys
import warnings
from pathlib import Path
from typing import Any

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
ANTHROPOMETRY_ROOT = REPO_ROOT / "external" / "SMPL-Anthropometry"


# Our canonical key -> upstream measurement name.
# Upstream's exact measurement vocabulary is in
# `external/SMPL-Anthropometry/measurement_definitions.py`. The mapping
# below covers the measurements that appear in our target_measurements.json;
# additional measurements can be requested by passing them directly to
# measure_mesh(..., names=[...]).
UPSTREAM_NAME_MAP: dict[str, str] = {
    "stature_cm": "height",
    "bust_cm": "chest circumference",
    "waist_cm": "waist circumference",
    "hip_cm": "hip circumference",
    "head_circ_cm": "head circumference",
    "neck_circ_cm": "neck circumference",
    "upper_arm_circ_cm": "bicep right circumference",
    "forearm_circ_cm": "forearm right circumference",
    "thigh_circ_cm": "thigh left circumference",
    "calf_circ_cm": "calf left circumference",
    "shoulder_breadth_cm": "shoulder breadth",
    "arm_length_cm": "arm right length",
    "inseam_cm": "inside leg height",
}


def _ensure_on_path() -> None:
    if not ANTHROPOMETRY_ROOT.exists():
        raise RuntimeError(
            f"SMPL-Anthropometry repo not found at {ANTHROPOMETRY_ROOT}. "
            f"Clone with:\n"
            f"  git clone https://github.com/DavidBoja/SMPL-Anthropometry.git "
            f"{ANTHROPOMETRY_ROOT}"
        )
    p = str(ANTHROPOMETRY_ROOT)
    if p not in sys.path:
        sys.path.insert(0, p)


def _ensure_smplx_weights(model_dir: str | Path | None) -> Path:
    """Locate SMPL-X .pkl weights and link them into the upstream repo's
    expected `data/smplx/` directory so `MeasureSMPLX.__init__` can load.
    """
    if model_dir is None:
        model_dir = os.environ.get("SMPLX_MODEL_DIR")
    if not model_dir:
        raise RuntimeError(
            "SMPL-X weights required. Set SMPLX_MODEL_DIR env var or pass "
            "model_dir= to the SMPL-X folder containing SMPLX_FEMALE.pkl "
            "etc. Download from https://smpl-x.is.tue.mpg.de/ (academic "
            "registration required)."
        )
    model_dir = Path(model_dir).resolve()
    if not model_dir.is_dir():
        raise FileNotFoundError(f"SMPL-X model dir not found: {model_dir}")

    target = ANTHROPOMETRY_ROOT / "data" / "smplx"
    target.mkdir(parents=True, exist_ok=True)
    for pkl in model_dir.glob("SMPLX_*.pkl"):
        dest = target / pkl.name
        if not dest.exists():
            try:
                dest.symlink_to(pkl)
            except OSError:
                shutil.copy(pkl, dest)
    return model_dir


def measure_mesh(
    vertices: np.ndarray,
    gender: str = "female",
    names: list[str] | None = None,
    smplx_model_dir: str | Path | None = None,
) -> dict[str, float]:
    """Measure a (10475, 3) SMPL-X vertex array.

    Returns a dict mapping our canonical key names (with `_cm` suffixes) to
    measurement values in cm. Pass `names=` to request specific upstream
    measurement names directly (skips the canonical-key mapping).
    """
    _ensure_on_path()
    _ensure_smplx_weights(smplx_model_dir)

    import torch
    from measure import MeasureBody

    verts = np.asarray(vertices, dtype=np.float32)
    if verts.shape != (10475, 3):
        raise ValueError(
            f"expected (10475, 3) SMPL-X vertices; got {verts.shape}"
        )
    verts_t = torch.from_numpy(verts)

    measurer = MeasureBody("smplx")
    measurer.from_verts(verts=verts_t)

    if names is None:
        upstream_names = list(UPSTREAM_NAME_MAP.values())
        upstream_to_canonical = {v: k for k, v in UPSTREAM_NAME_MAP.items()}
    else:
        upstream_names = list(names)
        upstream_to_canonical = {n: n for n in upstream_names}

    measurer.measure(upstream_names)
    raw = measurer.measurements

    out: dict[str, float] = {}
    for upstream_name in upstream_names:
        if upstream_name not in raw:
            warnings.warn(f"upstream measurement {upstream_name!r} missing from results")
            continue
        key = upstream_to_canonical[upstream_name]
        out[key] = float(raw[upstream_name])
    return out
