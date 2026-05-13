"""Generate a catalog of every CharMorph morph slider.

For every storage-name (`<Part>_<Slider>_min|max` or
`<Part>_<DimA>-<DimB>_<min|max>-<min|max>`), derive the user-facing
slider names (e.g. `Pelvis_GluteusMass`, `Pelvis_GluteusTone`).

Groups by anatomical region. Tags which sliders are body-measurement-
relevant vs cosmetic. Writes JSON for programmatic access and a
human-readable Markdown summary.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
CHARDB_FEMALE = REPO_ROOT / "external" / "CharMorph-db" / "characters" / "mb_female"
OUT_JSON = REPO_ROOT / "data" / "charmorph_morph_catalog.json"
OUT_MD = REPO_ROOT / "passes" / "pass-8-morph-catalog-and-fitter" / "morph_catalog.md"


# Region prefixes — order matters when one prefix is a substring of another
REGION_GROUPS = [
    ("torso/breast", ["Torso_Breast"]),
    ("torso", ["Torso_"]),
    ("abdomen", ["Abdomen_"]),
    ("waist", ["Waist_"]),
    ("pelvis", ["Pelvis_"]),
    ("stomach", ["Stomach_"]),
    ("shoulders", ["Shoulders_"]),
    ("neck", ["Neck_"]),
    ("arms", ["Arms_", "Armpit_", "Elbows_", "Wrists_"]),
    ("legs", ["Legs_"]),
    ("hands", ["Hands_"]),
    ("feet", ["Feet_"]),
    ("head", ["Head_"]),
    ("face/cheeks", ["Cheeks_"]),
    ("face/chin", ["Chin_", "Jaw_"]),
    ("face/eyes", ["Eyes_", "Brow", "Lash"]),
    ("face/mouth", ["Mouth_", "Lips_", "Teeth_"]),
    ("face/nose", ["Nose_"]),
    ("face/forehead", ["Forehead_"]),
    ("face/ears", ["Ears_"]),
    ("face/other", ["Face_", "IDHumans"]),
    ("body global", ["Body_"]),
]

# Regions whose morphs are body-measurement-relevant (affect bust/waist/hip/etc.)
MEASUREMENT_REGIONS = {
    "torso", "torso/breast", "abdomen", "waist", "pelvis", "stomach",
    "shoulders", "neck", "arms", "legs", "hands", "feet", "head", "body global",
}


def region_for(name: str) -> str:
    for region, prefixes in REGION_GROUPS:
        for p in prefixes:
            if name.startswith(p):
                return region
    return "other"


def parse_storage_name(stored: str) -> tuple[list[str], list[str]] | None:
    """Parse a storage morph name into ([slider_names], [corner_suffixes]).

    Returns None if the name doesn't fit the expected pattern.

    Examples:
      'Torso_BreastMass-BreastTone_max-max' →
        sliders=['Torso_BreastMass', 'Torso_BreastTone'], corner=['max', 'max']
      'Waist_Size_max' → sliders=['Waist_Size'], corner=['max']
      'IDHumans_max' → sliders=['IDHumans'], corner=['max']
    """
    m = re.match(r"^(?P<stem>.+)_(?P<corner>(?:min|max)(?:-(?:min|max))*)$", stored)
    if not m:
        return None
    stem = m.group("stem")
    corner = m.group("corner").split("-")
    # If stem looks like "Part_DimA-DimB", split into slider names
    if "_" in stem:
        part, rest = stem.split("_", 1)
        dims = rest.split("-")
        sliders = [f"{part}_{d}" for d in dims]
    else:
        sliders = [stem]
    if len(sliders) != len(corner):
        return None
    return sliders, corner


def main() -> None:
    fem_morphs_main = CHARDB_FEMALE / "morphs" / "L2_packed" / "__main__.npz"
    fem_morphs_eth = CHARDB_FEMALE / "morphs" / "L2_packed" / "Caucasian.npz"

    catalog: dict[str, dict] = {}

    for src_path in (fem_morphs_main, fem_morphs_eth):
        if not src_path.exists():
            continue
        z = np.load(src_path, allow_pickle=False)
        names = [n.decode("utf-8") for n in bytes(z["names"]).split(b"\0") if n]
        for stored in names:
            parsed = parse_storage_name(stored)
            if parsed is None:
                continue
            sliders, corner = parsed
            for s in sliders:
                if s not in catalog:
                    region = region_for(s)
                    catalog[s] = {
                        "region": region,
                        "measurement_relevant": region in MEASUREMENT_REGIONS,
                        "value_range": [0.0, 1.0],
                        "compound_with": set(),
                        "stored_corners": [],
                    }
                # Compound pairing: list of other sliders co-stored
                others = [o for o in sliders if o != s]
                for o in others:
                    catalog[s]["compound_with"].add(o)
                catalog[s]["stored_corners"].append(stored)

    # Finalize: set → sorted list
    for k, v in catalog.items():
        v["compound_with"] = sorted(v["compound_with"])
        v["stored_corners"] = sorted(set(v["stored_corners"]))

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSON.open("w") as f:
        json.dump(catalog, f, indent=2, sort_keys=True)

    # Human-readable summary
    by_region: dict[str, list[str]] = {}
    for name, meta in catalog.items():
        by_region.setdefault(meta["region"], []).append(name)
    for region in by_region:
        by_region[region].sort()

    lines = []
    lines.append("# CharMorph mb_female morph catalog\n")
    lines.append(f"Total sliders: **{len(catalog)}**\n")
    lines.append("Generated from `external/CharMorph-db/characters/mb_female/morphs/L2_packed/{__main__,Caucasian}.npz`.\n")
    lines.append("\n## How to use\n")
    lines.append("Each slider name maps to one or more storage entries (`*_max`, `*_min`, or combo corners `*_max-max` etc.). ")
    lines.append("Set values in `configs/<body>.json::charmorph.morph_values` using the slider names below. ")
    lines.append("Range is [0, 1] for `_max` direction; [-1, 0] uses the corresponding `_min` morph.\n")
    lines.append("\nWhen two sliders are listed as 'compound with' each other, they're stored as a 2D combo grid; you can set them independently and the combo math handles the interaction.\n")
    lines.append("\n## Body-measurement-relevant regions (use these for fitting)\n")
    for region in sorted(by_region):
        if any(catalog[n]["measurement_relevant"] for n in by_region[region]):
            lines.append(f"\n### {region}\n")
            for n in by_region[region]:
                m = catalog[n]
                if m["compound_with"]:
                    lines.append(f"- **{n}** — combo-paired with: {', '.join(m['compound_with'])}")
                else:
                    lines.append(f"- **{n}** — 1D slider")
    lines.append("\n\n## Face / cosmetic regions (not used by the fitter)\n")
    for region in sorted(by_region):
        if not any(catalog[n]["measurement_relevant"] for n in by_region[region]):
            lines.append(f"\n### {region}\n")
            for n in by_region[region][:20]:
                lines.append(f"- {n}")
            if len(by_region[region]) > 20:
                lines.append(f"- … and {len(by_region[region]) - 20} more")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines))

    print(f"wrote {OUT_JSON.relative_to(REPO_ROOT)} ({len(catalog)} sliders)")
    print(f"wrote {OUT_MD.relative_to(REPO_ROOT)}")
    print("\nregion summary:")
    for region in sorted(by_region):
        rel = sum(1 for n in by_region[region] if catalog[n]["measurement_relevant"])
        total = len(by_region[region])
        marker = " (measurement-relevant)" if any(catalog[n]["measurement_relevant"] for n in by_region[region]) else ""
        print(f"  {region}: {total} sliders{marker}")


if __name__ == "__main__":
    main()
