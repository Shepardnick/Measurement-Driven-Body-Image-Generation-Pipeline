"""Smooth-shaded, lit renderer for trimesh bodies.

pyrender with EGL backend. PBR-ish material (optional diffuse texture),
multi-directional ambient-heavy lighting designed to *not* hide mesh
defects in deep shadow. Same 8-view convention as before.

Lighting philosophy (pass 9): bright global ambient + 4 balanced
directional lights at moderate intensities, no rim. Result is closer
to overcast outdoor / studio softbox — slightly flatter but reveals
every surface variation. Good for diagnostic / reference renders.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Optional

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
    texture_path: Optional[str | Path] = None,
    uvs: Optional[np.ndarray] = None,
    bright_global: bool = True,
) -> list[Path]:
    """Render a mesh from a ring of cameras.

    If `texture_path` + `uvs` supplied, applies the texture via pyrender
    PBR material. Otherwise uses flat `skin_rgb` color.

    `bright_global=True` enables the high-ambient even-lighting rig
    introduced in pass 9. False keeps the original 3-point dramatic rig.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    base = trimesh.Trimesh(
        vertices=np.asarray(mesh.vertices, dtype=np.float64),
        faces=np.asarray(mesh.faces, dtype=np.int64),
        process=False,
    )

    # Material: either textured (baked to per-vertex color) or flat color.
    # We bake texture → vertex colors because pyrender's texture binding via
    # PyOpenGL+EGL has a known ctypes incompatibility on Python 3.12 that
    # makes the standard baseColorTexture path crash at glGenTextures.
    # Per-vertex color sidesteps the texture upload entirely.
    if texture_path is not None and uvs is not None:
        texture_img = np.asarray(Image.open(str(texture_path)).convert("RGB"))
        uv_arr = np.asarray(uvs, dtype=np.float32)
        if uv_arr.shape[0] != len(base.vertices):
            raise ValueError(
                f"UV count {uv_arr.shape[0]} != vertex count {len(base.vertices)}"
            )
        h, w = texture_img.shape[:2]
        # UV (0,0) is bottom-left in OpenGL convention; PIL is top-left.
        px = np.clip((uv_arr[:, 0] * (w - 1)).astype(np.int64), 0, w - 1)
        py = np.clip(((1.0 - uv_arr[:, 1]) * (h - 1)).astype(np.int64), 0, h - 1)
        vertex_colors = texture_img[py, px]  # (V, 3) uint8
        base.visual.vertex_colors = vertex_colors
        pyr_mesh = pyrender.Mesh.from_trimesh(base, smooth=True)
    else:
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
        if bright_global:
            scene = pyrender.Scene(ambient_light=(0.55, 0.55, 0.55))
            # 4 evenly-distributed lights at +25° elevation, all moderate
            # intensity, no dominant key. Camera-relative so every view
            # gets the same lighting setup.
            light_specs = (
                (deg - 45, +extent * 0.20, 1.6),
                (deg + 45, +extent * 0.20, 1.6),
                (deg + 135, +extent * 0.25, 1.4),
                (deg - 135, +extent * 0.25, 1.4),
            )
        else:
            scene = pyrender.Scene(ambient_light=(0.18, 0.18, 0.18))
            light_specs = (
                (deg - 35, +extent * 0.35, 3.0),
                (deg + 50, +extent * 0.10, 1.8),
                (deg + 170, +extent * 0.45, 2.2),
            )

        scene.add(pyr_mesh)

        cam_pose = _look_at(
            eye=_camera_eye(deg, center, cam_distance, cam_height),
            target=np.array([center[0], cam_height, center[2]]),
        )
        scene.add(
            pyrender.PerspectiveCamera(yfov=np.pi / 4.5, aspectRatio=1.0),
            pose=cam_pose,
        )

        for light_angle, light_y_offset, intensity in light_specs:
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
