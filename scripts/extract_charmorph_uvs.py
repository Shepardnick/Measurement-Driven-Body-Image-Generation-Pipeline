"""One-shot Blender extraction of per-vertex UV coords for mb_female.

Run with:
    blender --background --python scripts/extract_charmorph_uvs.py

CharMorph stores UVs per loop (per face-corner). A vertex shared by multiple
faces can have different UV values at each face (especially at UV seams).
For our renderer we want per-vertex UVs. We take the FIRST UV encountered
for each vertex — most vertices have a single consistent UV; the seam
vertices will get one of their UV values (acceptable for v1).
"""

import os
import sys

import bpy
import numpy as np


REPO = "/home/user/Measurement-Driven-Body-Image-Generation-Pipeline"
CHAR_BLEND = f"{REPO}/external/CharMorph-db/characters/mb_female/char.blend"
OUT_PATH = f"{REPO}/data/charmorph_female_uvs.npz"


def main() -> None:
    print(f"opening {CHAR_BLEND}")
    bpy.ops.wm.open_mainfile(filepath=CHAR_BLEND)

    body = max(
        (o for o in bpy.data.objects if o.type == "MESH"),
        key=lambda o: len(o.data.vertices),
    )
    mesh = body.data
    print(f"body mesh: '{body.name}' with {len(mesh.vertices)} verts, "
          f"{len(mesh.polygons)} polys, {len(mesh.loops)} loops")

    uv_layer = mesh.uv_layers.active
    if uv_layer is None:
        raise RuntimeError("no active UV layer on body mesh")
    print(f"using UV layer: '{uv_layer.name}'")

    n_verts = len(mesh.vertices)
    uvs = np.zeros((n_verts, 2), dtype=np.float32)
    seen = np.zeros(n_verts, dtype=bool)

    # Iterate loops; each loop has vertex_index and uv coord
    for loop_idx, loop in enumerate(mesh.loops):
        vert_idx = loop.vertex_index
        if seen[vert_idx]:
            continue  # take first UV per vertex
        uv = uv_layer.data[loop_idx].uv
        uvs[vert_idx] = (uv.x, uv.y)
        seen[vert_idx] = True

    missing = int((~seen).sum())
    if missing:
        print(f"WARNING: {missing} vertices had no UV (unused by any face)")

    print(f"UV stats: u {uvs[:, 0].min():.3f}..{uvs[:, 0].max():.3f}, "
          f"v {uvs[:, 1].min():.3f}..{uvs[:, 1].max():.3f}")

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    np.savez(OUT_PATH, uvs=uvs, mesh_name=body.name)
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
