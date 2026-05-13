"""Pass 5 stage 1: render the MHR default-shape body to validate the
install + topology + render pipeline end-to-end."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.mhr_body import build_mhr_mesh
from src.render import render_views

OUT_DIR = REPO_ROOT / "outputs" / "mhr"
RENDER_DIR = OUT_DIR / "renders"
MESH_PATH = OUT_DIR / "mesh_default.obj"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)

    print("loading MHR (LOD 1, CPU) and building default-shape body...")
    mesh = build_mhr_mesh()  # all-zeros: mean shape, T-pose, neutral expression
    print(f"  vertices: {len(mesh.vertices)}, faces: {len(mesh.faces)}")
    print(f"  bbox: {mesh.bounds[0]} → {mesh.bounds[1]}")

    # MHR meshes are in centimeters per Meta's convention. SMPL-X was in
    # meters and we scaled ×100 at render time. Detect by extent: if max
    # vertical extent < 5 it's meters, otherwise cm.
    y_extent = float(mesh.bounds[1][1] - mesh.bounds[0][1])
    if y_extent < 5.0:
        print(f"  mesh is in meters (extent {y_extent:.2f}); scaling ×100 → cm")
        mesh.vertices = mesh.vertices * 100.0

    mesh.visual.face_colors = [210, 180, 160, 255]
    mesh.export(MESH_PATH)
    print(f"wrote {MESH_PATH.relative_to(REPO_ROOT)}")

    print("rendering 8 views...")
    written = render_views(mesh, RENDER_DIR, resolution=1024)
    for p in written:
        print(f"  wrote {p.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
