"""Render a trimesh from a ring of viewpoints to PNGs using matplotlib's 3D backend.

This is intentionally low-fidelity. The goal is geometric correctness across
8 angles, not photorealism. Once SMPL-X meshes are in play, swap in a real
renderer (pyrender / open3d) here without touching anything else.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from matplotlib.colors import LightSource
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


DEFAULT_ANGLES_DEG = (0, 45, 90, 135, 180, 225, 270, 315)


def render_views(
    mesh: trimesh.Trimesh,
    output_dir: str | Path,
    angles_deg=DEFAULT_ANGLES_DEG,
    resolution: int = 1024,
    bg_rgb: tuple[float, float, float] = (1.0, 1.0, 1.0),
    base_color_rgb: tuple[float, float, float] = (0.82, 0.71, 0.63),
) -> list[Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    verts = np.asarray(mesh.vertices, dtype=np.float64)
    faces = np.asarray(mesh.faces, dtype=np.int64)
    face_normals = np.asarray(mesh.face_normals, dtype=np.float64)

    # Subject coords: X right, Y up, Z forward. Matplotlib's mplot3d puts Z
    # up by convention, so feed coordinates as (X, -Z, Y) — this maps the
    # subject's "forward" to matplotlib's -Y axis (toward viewer at azim=0).
    plot_verts = np.column_stack([verts[:, 0], -verts[:, 2], verts[:, 1]])
    plot_normals = np.column_stack(
        [face_normals[:, 0], -face_normals[:, 2], face_normals[:, 1]]
    )

    # Frame bounds — use the body's actual extents with a small margin
    mins = plot_verts.min(axis=0)
    maxs = plot_verts.max(axis=0)
    center = (mins + maxs) / 2
    extent = (maxs - mins).max() * 0.55
    bbox = [(center[i] - extent, center[i] + extent) for i in range(3)]

    # matplotlib's azim=0 looks down +X, but we want azim=0 to be the front
    # view (looking down +Z toward -Z). Add 90° so the user-visible angles
    # match subject-frame conventions (0=front, 90=subject's right, etc.).
    AZIM_OFFSET_DEG = 90.0

    written: list[Path] = []
    for deg in angles_deg:
        path = output_dir / f"view_{deg:03d}.png"
        _render_one(
            plot_verts,
            faces,
            plot_normals,
            azim_deg=deg + AZIM_OFFSET_DEG,
            elev_deg=2.0,
            bbox=bbox,
            resolution=resolution,
            bg_rgb=bg_rgb,
            base_color_rgb=base_color_rgb,
            output_path=path,
        )
        written.append(path)
    return written


def _render_one(
    plot_verts: np.ndarray,
    faces: np.ndarray,
    plot_normals: np.ndarray,
    azim_deg: float,
    elev_deg: float,
    bbox: list[tuple[float, float]],
    resolution: int,
    bg_rgb: tuple[float, float, float],
    base_color_rgb: tuple[float, float, float],
    output_path: Path,
) -> None:
    # Per-face shading: dot product of face normal with a light direction.
    # Light comes from camera direction + a bit above and to the side, which
    # rotates with the view so every angle is decently lit.
    az = np.deg2rad(azim_deg)
    el = np.deg2rad(elev_deg + 25.0)  # raise the light a bit
    light_dir = np.array(
        [
            np.cos(el) * np.sin(az),
            -np.cos(el) * np.cos(az),
            np.sin(el),
        ]
    )
    light_dir = light_dir / np.linalg.norm(light_dir)

    intensity = plot_normals @ light_dir
    intensity = np.clip(intensity, 0.0, 1.0)
    # Ambient + diffuse mix so unlit faces aren't pure black
    shade = 0.30 + 0.70 * intensity
    base = np.array(base_color_rgb)
    colors = np.clip(shade[:, None] * base[None, :], 0.0, 1.0)
    colors = np.column_stack([colors, np.ones(len(colors))])

    dpi = 100
    figsize = resolution / dpi
    fig = plt.figure(figsize=(figsize, figsize), dpi=dpi, facecolor=bg_rgb)
    ax = fig.add_subplot(111, projection="3d")
    ax.set_facecolor(bg_rgb)

    triangles = plot_verts[faces]
    poly = Poly3DCollection(triangles, facecolors=colors, edgecolors="none")
    ax.add_collection3d(poly)

    ax.set_xlim(*bbox[0])
    ax.set_ylim(*bbox[1])
    ax.set_zlim(*bbox[2])
    try:
        ax.set_box_aspect((1, 1, 1))
    except AttributeError:
        pass
    ax.view_init(elev=elev_deg, azim=azim_deg)
    ax.set_axis_off()
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)

    fig.savefig(output_path, dpi=dpi, facecolor=bg_rgb, pad_inches=0)
    plt.close(fig)
