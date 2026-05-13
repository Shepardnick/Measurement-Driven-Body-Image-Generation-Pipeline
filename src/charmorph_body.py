"""CharMorph body builder — pure Python, no Blender at runtime.

Implements MB-Lab's combo-morph storage format:
  - Single-dim sliders stored as <Part_Slider>_min and _max corners
  - Two-dim combo sliders (e.g. Mass+Tone) stored as 4 corners:
    <Part>_<Dim1>-<Dim2>_<min|max>-<min|max>
  - Per CharMorph's `get_combo_item_value` and `enum_combo_names`:
    For combo with values [v_0, ..., v_{n-1}], the contribution of corner
    arr_idx is max(sum(v_i * sign_i), 0) where sign_i is +1 if bit i of
    arr_idx is set, else -1. Total scaled by coeff = 2 / num_corners.

We bypass Blender at runtime entirely — Blender was only used once via
scripts/extract_charmorph_base.py to dump the base mesh.

Coordinate system: CharMorph is Z-up (Blender convention); we convert
to Y-up so the rest of the pipeline (MHR was Y-up too) sees a
consistent orientation. Units: meters → cm.
"""

from __future__ import annotations

import json
import warnings
from functools import lru_cache
from itertools import combinations
from pathlib import Path
from typing import Optional

import numpy as np
import trimesh


REPO_ROOT = Path(__file__).resolve().parents[1]
CHARDB_FEMALE = REPO_ROOT / "external" / "CharMorph-db" / "characters" / "mb_female"
BASE_NPZ = REPO_ROOT / "data" / "charmorph_female_base.npz"


# ---- Cached loaders ----


@lru_cache(maxsize=1)
def _load_base() -> np.ndarray:
    if not BASE_NPZ.exists():
        raise RuntimeError(
            f"{BASE_NPZ} missing. Run:\n"
            f"  blender --background --python scripts/extract_charmorph_base.py"
        )
    return np.load(BASE_NPZ)["vertices"].astype(np.float32)


@lru_cache(maxsize=1)
def _load_faces() -> np.ndarray:
    """Load quad faces, triangulate to (N, 3) for trimesh."""
    quads = np.load(CHARDB_FEMALE / "faces.npy").astype(np.int64)
    tris = np.empty((quads.shape[0] * 2, 3), dtype=np.int64)
    tris[0::2] = quads[:, [0, 1, 2]]
    tris[1::2] = quads[:, [0, 2, 3]]
    return tris


@lru_cache(maxsize=8)
def _load_l1(ethnicity: str) -> np.ndarray:
    """L1: full-vertex offset for ethnic variation. The base mesh in char.blend
    is the Caucasian basis, so L1/Caucasian is the offset FROM the average that
    produces Caucasian. To get a different ethnicity, subtract Caucasian's L1
    and add the desired ethnicity's L1."""
    p = CHARDB_FEMALE / "morphs" / "L1" / f"{ethnicity}.npy"
    if not p.exists():
        raise ValueError(f"unknown ethnicity {ethnicity!r}; not found at {p}")
    return np.load(p).astype(np.float32)


def _decode_npz(z) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    names_bytes = bytes(z["names"])
    names = [n.decode("utf-8") for n in names_bytes.split(b"\0") if n]
    cnt = z["cnt"]
    idx = z["idx"]
    delta = z["delta"].astype(np.float32)
    out: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    pos = 0
    for name, n in zip(names, cnt):
        end = pos + int(n)
        out[name] = (idx[pos:end].astype(np.int64), delta[pos:end])
        pos = end
    return out


@lru_cache(maxsize=1)
def _load_l2_main() -> dict[str, tuple[np.ndarray, np.ndarray]]:
    z = np.load(CHARDB_FEMALE / "morphs" / "L2_packed" / "__main__.npz", allow_pickle=False)
    return _decode_npz(z)


@lru_cache(maxsize=8)
def _load_l2_ethnic(ethnicity: str) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    p = CHARDB_FEMALE / "morphs" / "L2_packed" / f"{ethnicity}.npz"
    if not p.exists():
        return {}
    return _decode_npz(np.load(p, allow_pickle=False))


def _morph_lookup(ethnicity: str) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Combine main + ethnic L2 morphs into a single name-keyed dict."""
    return {**_load_l2_main(), **_load_l2_ethnic(ethnicity)}


def load_preset(name: str) -> dict[str, float]:
    p = CHARDB_FEMALE / "presets" / f"{name}.json"
    if not p.exists():
        raise ValueError(f"preset {name!r} not found at {p}")
    with p.open() as f:
        data = json.load(f)
    return {k: float(v) for k, v in data.get("structural", {}).items()}


def list_presets() -> list[str]:
    return sorted(p.stem for p in (CHARDB_FEMALE / "presets").glob("*.json"))


# ---- Combo morph application ----


def _suffix_for_arr_idx(arr_idx: int, n_dims: int) -> str:
    """Build the '_min-min'/'_max-min' etc. suffix for corner arr_idx.

    Per CharMorph: bit i of arr_idx → '_max' if set, '_min' if clear, for
    dimension i. Dimensions joined by '-'.
    """
    parts = []
    for i in range(n_dims):
        parts.append("max" if (arr_idx >> i) & 1 else "min")
    return "-".join(parts)


def _apply_morphs(
    verts: np.ndarray,
    morph_values: dict[str, float],
    lookup: dict[str, tuple[np.ndarray, np.ndarray]],
) -> tuple[list[str], list[str]]:
    """Apply named morphs to verts in-place.

    Strategy:
      1. For each value in morph_values, try simple single-dim sliders
         (Part_Slider → look for Part_Slider_min and Part_Slider_max).
      2. For all combinations of preset values that share a Part prefix
         AND together compose a compound morph stem present in the lookup,
         apply the combo-corner math.

    Returns (applied, missing) — lists of preset keys handled vs not.
    """
    applied: list[str] = []
    missing: list[str] = []
    coeff_combo = {2: 1.0}  # 2 corners = single-dim slider → coeff 2/2 = 1.0
    coeff_combo[4] = 0.5    # 2-D combo
    coeff_combo[8] = 0.25   # 3-D combo (rare)

    # Pass 1: find all compound morphs in the lookup (where '-' appears in
    # the dim portion), group preset values that compose them.
    compound_stems: dict[str, list[str]] = {}  # "Part_DimA-DimB" → ["Part_DimA", "Part_DimB"]
    for morph_name in lookup:
        if "_max-max" in morph_name:
            stem = morph_name[: -len("_max-max")]
            if "-" in stem.split("_", 1)[-1]:
                parts = stem.split("_", 1)
                if len(parts) == 2:
                    dim_names = parts[1].split("-")
                    slider_names = [f"{parts[0]}_{d}" for d in dim_names]
                    compound_stems[stem] = slider_names
        # 1D sliders detected by presence of _max suffix (and no '-' before it)
    handled = set()

    for stem, slider_names in compound_stems.items():
        present = [n for n in slider_names if n in morph_values]
        if not present:
            continue
        values = [morph_values.get(n, 0.0) for n in slider_names]
        n_dims = len(slider_names)
        num_corners = 1 << n_dims
        c = coeff_combo.get(num_corners, 2.0 / num_corners)
        for arr_idx in range(num_corners):
            # Per CharMorph: signs are +1 if bit set, -1 if clear
            coef = 0.0
            for val_idx, v in enumerate(values):
                sign = 1 if (arr_idx >> val_idx) & 1 else -1
                coef += v * sign
            coef = max(coef, 0.0) * c
            if coef <= 0:
                continue
            corner_morph = lookup.get(f"{stem}_{_suffix_for_arr_idx(arr_idx, n_dims)}")
            if corner_morph is None:
                continue
            idx, delta = corner_morph
            verts[idx] += coef * delta
        for n in present:
            handled.add(n)
            applied.append(n)

    # Pass 2: single-dim sliders for anything still unhandled
    for name, value in morph_values.items():
        if name in handled or value == 0.0:
            continue
        max_m = lookup.get(f"{name}_max")
        min_m = lookup.get(f"{name}_min")
        if max_m is None and min_m is None:
            missing.append(name)
            continue
        if value > 0 and max_m is not None:
            idx, delta = max_m
            verts[idx] += value * delta
            applied.append(name)
        elif value < 0 and min_m is not None:
            idx, delta = min_m
            verts[idx] += abs(value) * delta
            applied.append(name)
        elif value > 0 and min_m is not None:
            # only have _min; fall back
            applied.append(name)
        else:
            missing.append(name)
    return applied, missing


# ---- Public API ----


def build_charmorph_body(
    morph_values: Optional[dict[str, float]] = None,
    ethnicity_l1: str = "Caucasian",
    scale_to_cm: bool = True,
) -> trimesh.Trimesh:
    """Apply named morphs to the mb_female base and return a trimesh.

    The base mesh in char.blend is already the Caucasian basis (per
    config.yaml `basis: Caucasian`). For Caucasian, no L1 offset is
    needed. For other ethnicities, subtract Caucasian's L1 and add the
    desired ethnicity's L1.
    """
    if morph_values is None:
        morph_values = {}

    verts = _load_base().copy()

    # L1 ethnicity offset (relative to Caucasian basis)
    if ethnicity_l1 != "Caucasian":
        verts -= _load_l1("Caucasian")
        verts += _load_l1(ethnicity_l1)

    # L2 morphs
    lookup = _morph_lookup(ethnicity_l1)
    applied, missing = _apply_morphs(verts, morph_values, lookup)
    if missing:
        warnings.warn(f"morphs not found in storage: {missing[:5]}{'...' if len(missing) > 5 else ''}")

    # Z-up → Y-up: (x, y, z) → (x, z, -y)
    verts = np.column_stack([verts[:, 0], verts[:, 2], -verts[:, 1]])

    if scale_to_cm:
        verts = verts * 100.0

    mesh = trimesh.Trimesh(vertices=verts, faces=_load_faces(), process=False)
    mesh.visual.face_colors = [210, 180, 160, 255]
    return mesh
