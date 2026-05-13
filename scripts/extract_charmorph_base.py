"""One-shot Blender extraction of the CharMorph mb_female base mesh.

Run with:
    blender --background --python scripts/extract_charmorph_base.py

Loads external/CharMorph-db/characters/mb_female/char.blend, finds the
body mesh, exports its vertices to data/charmorph_female_base.npz so the
rest of the pipeline can operate without Blender at runtime.
"""

import os
import sys

import bpy
import numpy as np


REPO = "/home/user/Measurement-Driven-Body-Image-Generation-Pipeline"
CHAR_BLEND = f"{REPO}/external/CharMorph-db/characters/mb_female/char.blend"
OUT_PATH = f"{REPO}/data/charmorph_female_base.npz"


def main() -> None:
    print(f"opening {CHAR_BLEND}")
    bpy.ops.wm.open_mainfile(filepath=CHAR_BLEND)

    print("all mesh objects:")
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            print(f"  {obj.name}: {len(obj.data.vertices)} verts, {len(obj.data.polygons)} polys")

    # Pick the mesh with the most vertices — that's the body
    body = max(
        (o for o in bpy.data.objects if o.type == "MESH"),
        key=lambda o: len(o.data.vertices),
    )
    print(f"\npicked body mesh: '{body.name}' with {len(body.data.vertices)} verts")

    verts = np.zeros((len(body.data.vertices), 3), dtype=np.float32)
    for i, v in enumerate(body.data.vertices):
        verts[i] = (v.co.x, v.co.y, v.co.z)

    # Sanity: bbox
    print(f"  bbox x: {verts[:,0].min():.3f}..{verts[:,0].max():.3f}")
    print(f"  bbox y: {verts[:,1].min():.3f}..{verts[:,1].max():.3f}")
    print(f"  bbox z: {verts[:,2].min():.3f}..{verts[:,2].max():.3f}")

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    np.savez(OUT_PATH, vertices=verts, mesh_name=body.name)
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
