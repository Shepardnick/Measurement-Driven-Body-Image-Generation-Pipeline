"""Pass 5 stage 2: render bodies at varied identity_coeffs to see how
diverse MHR's shape space is. We compare the default (zeros), all-positive
and all-negative 1σ, and a few random Gaussian samples.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.mhr_body import build_mhr_mesh, NUM_IDENTITY_BLENDSHAPES
from src.render import render_views

OUT_DIR = REPO_ROOT / "outputs" / "mhr" / "exploration"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(0)

    samples: dict[str, np.ndarray] = {
        "zero": np.zeros(NUM_IDENTITY_BLENDSHAPES, dtype=np.float32),
        "all_plus_1": np.ones(NUM_IDENTITY_BLENDSHAPES, dtype=np.float32),
        "all_minus_1": -np.ones(NUM_IDENTITY_BLENDSHAPES, dtype=np.float32),
        "body_only_plus_1": np.concatenate([
            np.ones(20, dtype=np.float32),       # body
            np.zeros(20, dtype=np.float32),      # head
            np.zeros(5, dtype=np.float32),       # hands
        ]),
        "rand_a": 0.8 * rng.standard_normal(NUM_IDENTITY_BLENDSHAPES).astype(np.float32),
        "rand_b": 0.8 * rng.standard_normal(NUM_IDENTITY_BLENDSHAPES).astype(np.float32),
    }

    for name, coeffs in samples.items():
        mesh = build_mhr_mesh(identity_coeffs=coeffs)
        mesh.visual.face_colors = [210, 180, 160, 255]
        mesh_dir = OUT_DIR / name
        mesh_dir.mkdir(exist_ok=True)
        render_views(mesh, mesh_dir, angles_deg=(0,), resolution=512)
        print(f"  {name}: bbox y={mesh.bounds[1][1] - mesh.bounds[0][1]:.1f} cm  "
              f"x={mesh.bounds[1][0] - mesh.bounds[0][0]:.1f} cm  "
              f"z={mesh.bounds[1][2] - mesh.bounds[0][2]:.1f} cm")


if __name__ == "__main__":
    main()
