"""Smooth-shaded, lit renderer for trimesh bodies.

pyrender with EGL backend. PBR skin material, 3-point soft lighting,
anti-aliased. Same 8-view convention as `src/render.py`.

Backgrounds composited onto white post-render (pyrender's bg_color
parameter handles int/float inconsistently in 0.1.45).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

os.environ.setdefault("PYOPENGL_PLATFORM", "egl")

import numpy as np
import pyrender
import trimesh
from PIL import Image


DEFAULT_ANGLES_DEG = (0, 45, 90, 135, 180, 225, 270, 315)


def render_views_quality(
    mesh: trimesh.Trimesh,
    output_dir: str | Path,
    angles_deg: Iterable[int] = DEFAULT_ANGLES_DEG,
    resolution: int = 1024,
    skin_rgb: tuple[float, float, float] = (0.78, 0.62, 0.52),
    bg_rgb: tuple[int, int, int] = (240, 240, 240),
) -> list[Path]:
    """Render a mesh from a ring of cameras. 0°=front (mesh assumed to face +Z)."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    base = trimesh.Trimesh(
        vertices=np.asarray(mesh.vertices, dtype=np.float64),
        faces=np.asarray(mesh.faces, dtype=np.int64),
        process=False,
    )
    pbr = pyrender.MetallicRoughnessMaterial(
        baseColorFactor=(*skin_rgb, 1.0),
        metallicFactor=0.0,
        roughnessFactor=0.55,
        doubleSided=False,
    )
    pyr_mesh = pyrender.Mesh.from_trimesh(base, material=pbr, smooth=True)

    bounds = base.bounds
    center = (bounds[0] + bounds[1]) / 2.0
    extent = float((bounds[1] - bounds[0]).max())
    cam_distance = extent * 1.55
    cam_height = center[1]

    bg_arr = np.array(bg_rgb, dtype=np.uint8)

    written: list[Path] = []
    for deg in angles_deg:
        scene = pyrender.Scene(ambient_light=(0.18, 0.18, 0.18))
        scene.add(pyr_mesh)

        cam_pose = _look_at(
            eye=_camera_eye(deg, center, cam_distance, cam_height),
            target=np.array([center[0], cam_height, center[2]]),
        )
        # FOV chosen so a body of `extent` height fits with margin from `cam_distance`
        scene.add(
            pyrender.PerspectiveCamera(yfov=np.pi / 4.5, aspectRatio=1.0),
            pose=cam_pose,
        )

        # Key + fill + rim, in WORLD coords (not following the camera headlamp-style)
        for light_angle, light_y_offset, intensity in (
            (deg - 35, +extent * 0.35, 3.0),   # key, high-front-left
            (deg + 50, +extent * 0.10, 1.8),   # fill, mid-front-right
            (deg + 170, +extent * 0.45, 2.2),  # rim, from behind
        ):
            light_pose = _look_at(
                eye=_camera_eye(light_angle, center, cam_distance * 1.3, cam_height + light_y_offset),
                target=np.array([center[0], cam_height, center[2]]),
            )
            scene.add(
                pyrender.DirectionalLight(color=(1.0, 1.0, 1.0), intensity=intensity),
                pose=light_pose,
            )

        renderer = pyrender.OffscreenRenderer(viewport_width=resolution, viewport_height=resolution)
        color_rgba, depth = renderer.render(scene, flags=pyrender.RenderFlags.RGBA)
        renderer.delete()

        # Composite onto solid background (pyrender bg_color is unreliable)
        rgb = color_rgba[..., :3]
        is_bg = depth <= 0
        out = np.where(is_bg[..., None], bg_arr[None, None, :], rgb).astype(np.uint8)

        path = output_dir / f"view_{deg:03d}.png"
        Image.fromarray(out).save(path)
        written.append(path)
    return written


def _camera_eye(angle_deg: float, center: np.ndarray, distance: float, height: float) -> np.ndarray:
    angle_rad = np.deg2rad(angle_deg)
    return np.array(
        [center[0] + distance * np.sin(angle_rad), height, center[2] + distance * np.cos(angle_rad)],
        dtype=np.float64,
    )


def _look_at(eye: np.ndarray, target: np.ndarray, up: np.ndarray = np.array([0, 1, 0])) -> np.ndarray:
    """Right-handed look-at, OpenGL-style (camera looks down its local -Z)."""
    f = target - eye
    f = f / np.linalg.norm(f)
    s = np.cross(f, up)
    s = s / np.linalg.norm(s)
    u = np.cross(s, f)

    pose = np.eye(4, dtype=np.float64)
    pose[:3, 0] = s
    pose[:3, 1] = u
    pose[:3, 2] = -f
    pose[:3, 3] = eye
    return pose
