"""End-to-end pass 1: measurements -> primitive humanoid -> 8 PNG renders."""

from __future__ import annotations

from pathlib import Path

from src.measurements import load_measurements
from src.proxy_body import Pose, build_proxy_body
from src.render import render_views


REPO_ROOT = Path(__file__).resolve().parents[1]
MEASUREMENTS_PATH = REPO_ROOT / "target_measurements.json"
RENDER_DIR = REPO_ROOT / "outputs" / "renders"
MESH_PATH = REPO_ROOT / "outputs" / "proxy_body.obj"


def main() -> None:
    measurements = load_measurements(MEASUREMENTS_PATH)
    print(f"loaded measurements for {measurements['gender']}, "
          f"stature {measurements['stature_cm']} cm, "
          f"W/H {measurements['waist_cm'] / measurements['hip_cm']:.2f}")

    mesh = build_proxy_body(measurements, pose=Pose())
    print(f"built proxy mesh: {len(mesh.vertices)} vertices, "
          f"{len(mesh.faces)} faces")

    MESH_PATH.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(MESH_PATH)
    print(f"wrote {MESH_PATH.relative_to(REPO_ROOT)}")

    written = render_views(mesh, RENDER_DIR, resolution=1024)
    for p in written:
        print(f"wrote {p.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
