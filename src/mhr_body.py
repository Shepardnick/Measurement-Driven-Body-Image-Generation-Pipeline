"""Adapter for Meta's MHR (Momentum Human Rig) parametric body model.

Uses pymomentum's FBX loader directly and applies identity blendshapes
manually. Bypasses `MHR.from_files()` because its
`character.with_blend_shape(...)` call segfaults on pymomentum-cpu
0.1.110.post0 + Python 3.12 + PyTorch 2.8 on Ubuntu 24.04.

The 45-dim identity coefficient vector controls the first 45 blendshape
directions of `character.blend_shape.shape_vectors` (117 total = 20 body +
20 head + 5 hands identity + 72 face expression).

For zero identity_coeffs you get MHR's mean-shape T-pose body. Pose
correctives (the MLP-based blendshapes that fire on joint articulation)
are not applied here — they'd be a pass-6 concern.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import torch
import trimesh

# Order matters: import torch before pymomentum so libtorch.so is loaded
# globally for pymomentum's native code to find.
import pymomentum.geometry as pym_geometry


REPO_ROOT = Path(__file__).resolve().parents[1]
MHR_ASSETS_DIR = REPO_ROOT / "models" / "mhr" / "assets"

NUM_IDENTITY_BLENDSHAPES = 45
NUM_FACE_EXPRESSION_BLENDSHAPES = 72


_character_cache = None


def _get_character(lod: int = 1):
    """Lazy singleton — FBX load is slow."""
    global _character_cache
    if _character_cache is not None:
        return _character_cache
    fbx = MHR_ASSETS_DIR / f"lod{lod}.fbx"
    mdl = MHR_ASSETS_DIR / "compact_v6_1.model"
    if not fbx.exists() or not mdl.exists():
        raise RuntimeError(
            f"MHR assets missing at {MHR_ASSETS_DIR}. Download with:\n"
            f"  curl -OL https://github.com/facebookresearch/MHR/releases/download/v1.0.0/assets.zip"
        )
    _character_cache = pym_geometry.Character.load_fbx(
        str(fbx), str(mdl), load_blendshapes=True
    )
    return _character_cache


def build_mhr_mesh(
    identity_coeffs: Optional[np.ndarray] = None,
    face_expr_coeffs: Optional[np.ndarray] = None,
    lod: int = 1,
) -> trimesh.Trimesh:
    """Run MHR's identity blendshape model and return a trimesh.

    Note: pose correctives are NOT applied. Body returns in T-pose. For a
    skinning + pose-deformed mesh you'd need to chain in the MLP-based
    pose corrective layer (deferred to pass 6).
    """
    character = _get_character(lod=lod)

    base_verts = np.asarray(character.mesh.vertices, dtype=np.float64)
    faces = np.asarray(character.mesh.faces, dtype=np.int64)
    shape_vectors = np.asarray(character.blend_shape.shape_vectors, dtype=np.float64)

    if identity_coeffs is None:
        identity_coeffs = np.zeros(NUM_IDENTITY_BLENDSHAPES, dtype=np.float32)
    if face_expr_coeffs is None:
        face_expr_coeffs = np.zeros(NUM_FACE_EXPRESSION_BLENDSHAPES, dtype=np.float32)

    id_coeffs = np.asarray(identity_coeffs, dtype=np.float64).reshape(-1)
    expr_coeffs = np.asarray(face_expr_coeffs, dtype=np.float64).reshape(-1)
    if id_coeffs.size != NUM_IDENTITY_BLENDSHAPES:
        raise ValueError(
            f"identity_coeffs must be ({NUM_IDENTITY_BLENDSHAPES},); got "
            f"{id_coeffs.shape}"
        )
    if expr_coeffs.size != NUM_FACE_EXPRESSION_BLENDSHAPES:
        raise ValueError(
            f"face_expr_coeffs must be ({NUM_FACE_EXPRESSION_BLENDSHAPES},); "
            f"got {expr_coeffs.shape}"
        )

    # shape_vectors: (N_blendshapes, N_verts, 3). First 45 are identity, last
    # 72 are face expression.
    id_dirs = shape_vectors[:NUM_IDENTITY_BLENDSHAPES]
    expr_dirs = shape_vectors[NUM_IDENTITY_BLENDSHAPES:NUM_IDENTITY_BLENDSHAPES + NUM_FACE_EXPRESSION_BLENDSHAPES]

    verts = base_verts.copy()
    verts += np.einsum("k,kvc->vc", id_coeffs, id_dirs)
    verts += np.einsum("k,kvc->vc", expr_coeffs, expr_dirs)

    return trimesh.Trimesh(vertices=verts, faces=faces, process=False)
