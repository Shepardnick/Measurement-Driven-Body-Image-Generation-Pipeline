"""Build a SMPL-X mesh from target measurements via A2B β + optional pose."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import numpy as np
import torch
import trimesh

from src.a2b_adapter import predict_betas


REPO_ROOT = Path(__file__).resolve().parents[1]
SMPLX_MODEL_DIR = REPO_ROOT / "models" / "smplx"


# Indices into SMPL-X body_pose (63 dims = 21 joints × 3 axis-angle).
# Body_pose excludes pelvis (joint 0 in the full kinematic tree). So the
# body-pose index for joint J is J - 1.
JOINT_LEFT_SHOULDER = 16
JOINT_RIGHT_SHOULDER = 17


def relaxed_standing_pose(shoulder_drop_deg: float = 70.0) -> np.ndarray:
    """body_pose (63,) for a relaxed standing pose.

    Only the shoulder joints get non-zero rotations; everything else is the
    default T-pose. `shoulder_drop_deg` is the rotation from T-pose toward
    the body (so 90° = arms fully at sides, 0° = T-pose). Sign convention
    matches SMPL's design-doc example: left shoulder negative, right
    positive, rotation around the Z (forward) axis at each shoulder.
    """
    pose = np.zeros(63, dtype=np.float32)
    rad = np.deg2rad(shoulder_drop_deg)
    left_idx = (JOINT_LEFT_SHOULDER - 1) * 3
    pose[left_idx + 2] = -rad
    right_idx = (JOINT_RIGHT_SHOULDER - 1) * 3
    pose[right_idx + 2] = +rad
    return pose


def fit_beta(
    measurements: dict[str, Any],
    model_type: str = "svr",
    clip: float | None = 5.0,
) -> np.ndarray:
    betas = predict_betas(measurements, model_type=model_type)
    if clip is not None:
        betas = np.clip(betas, -clip, clip)
    return betas


def build_smplx_mesh(
    beta: np.ndarray,
    pose: np.ndarray | None = None,
    gender: str = "female",
    model_dir: Path | str = SMPLX_MODEL_DIR,
) -> tuple[trimesh.Trimesh, np.ndarray, np.ndarray]:
    """Run SMPL-X forward and return (trimesh, verts, faces).

    Mesh is in meters (SMPL-X convention); convert to cm at render time if
    needed. `pose` is the body_pose vector (63,); None means T-pose.
    """
    import smplx as smplx_pkg

    model_dir = Path(model_dir)
    model = smplx_pkg.create(
        str(model_dir.parent),  # parent of smplx/ subdir
        model_type="smplx",
        gender=gender,
        num_betas=len(beta),
        use_pca=False,
        flat_hand_mean=True,
        ext="npz",
    )

    beta_t = torch.from_numpy(beta.astype(np.float32)).unsqueeze(0)
    pose_t = (
        torch.from_numpy(pose.astype(np.float32)).unsqueeze(0)
        if pose is not None
        else torch.zeros(1, 63)
    )

    output = model(betas=beta_t, body_pose=pose_t, return_verts=True)
    verts = output.vertices[0].detach().cpu().numpy().astype(np.float64)
    faces = model.faces.astype(np.int64)

    mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
    return mesh, verts, faces
