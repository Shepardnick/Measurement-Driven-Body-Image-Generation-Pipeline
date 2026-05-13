"""Drive photo-based measurement extraction. Reads references/, writes
target_measurements_v2.json + a comparison report against the old values.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.photo_measure import (
    compute_circumferences,
    detect_pose,
    extract_front_widths,
    extract_side_depths,
)


REFERENCES = REPO_ROOT / "references"
OLD_PATH = REPO_ROOT / "target_measurements.json"
NEW_PATH = REPO_ROOT / "target_measurements_v2.json"
REPORT_PATH = REPO_ROOT / "passes" / "pass-4-photo-measurements" / "report.md"
DEBUG_DIR = REPO_ROOT / "outputs" / "photo_measure_debug"

DECLARED_HEIGHT_CM = 193.04  # from original target_measurements.json


def crop_side_from_4panel(image: np.ndarray) -> np.ndarray:
    """The 4-panel collage layout is front | back / side | face (rough 2×2).
    The side panel is bottom-left. Find the panel boundaries by looking at
    the largest dark borders, or just split into quadrants.
    """
    h, w = image.shape[:2]
    # Bottom-left quadrant
    return image[h // 2 :, : w // 2]


def crop_side_from_labeled(image: np.ndarray) -> np.ndarray:
    """The labeled reference image has 3 panels on top (front-with-labels,
    back, side) and a half-row of small panels below. Side is rightmost top.
    Approximate split: width into thirds, take rightmost third of the
    top ~70% of the image height.
    """
    h, w = image.shape[:2]
    return image[: int(h * 0.70), int(w * 2 / 3) :]


def annotate_debug(image: np.ndarray, fm, label_prefix: str) -> np.ndarray:
    """Draw horizontal measurement lines on a copy of the image for review."""
    out = image.copy()
    lines = [
        ("shoulder", fm.shoulder_y_px, (0, 255, 255)),
        ("bust", fm.bust_y_px, (255, 0, 0)),
        ("waist", fm.waist_y_px, (0, 255, 0)),
        ("hip widest", fm.hip_widest_y_px, (255, 0, 255)),
        ("mid-thigh", fm.mid_thigh_y_px, (255, 128, 0)),
        ("knee", fm.knee_y_px, (200, 200, 200)),
        ("mid-calf", fm.mid_calf_y_px, (100, 100, 255)),
    ]
    for name, y, color in lines:
        cv2.line(out, (0, y), (out.shape[1], y), color, 2)
        cv2.putText(out, f"{label_prefix} {name}", (10, y - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    return out


def main() -> None:
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)

    print(f"declared height: {DECLARED_HEIGHT_CM} cm\n")

    # --- Front view ---
    front_path = REFERENCES / "front_full.jpg"
    print(f"[front] processing {front_path.name}")
    front_img = cv2.imread(str(front_path))
    if front_img is None:
        raise SystemExit(f"failed to read {front_path}")
    fm = extract_front_widths(front_img, declared_height_cm=DECLARED_HEIGHT_CM)
    print(f"  body_height: {fm.body_height_cm:.2f} cm (declared {DECLARED_HEIGHT_CM})")
    print(f"  shoulder_width: {fm.shoulder_width_cm:.2f} cm (biacromial)")
    print(f"  upper_arm_width: {fm.upper_arm_width_cm:.2f} cm (estimated)")
    print(f"  bust_silhouette: {fm.bust_width_silhouette_cm:.2f} cm  ->  bust_torso: {fm.bust_width_cm:.2f} cm")
    print(f"  waist_width:    {fm.waist_width_cm:.2f} cm")
    print(f"  hip_silhouette:  {fm.hip_width_silhouette_cm:.2f} cm  ->  hip_torso:  {fm.hip_width_cm:.2f} cm")
    print(f"  mid_thigh:      {fm.mid_thigh_width_cm:.2f} cm")
    print(f"  knee:           {fm.knee_width_cm:.2f} cm")
    print(f"  mid_calf:       {fm.mid_calf_width_cm:.2f} cm")
    cv2.imwrite(str(DEBUG_DIR / "front_annotated.jpg"), annotate_debug(front_img, fm, "F"))

    # --- Side view from 4-panel collage ---
    side_collage_path = REFERENCES / "collage_4panel.jpg"
    print(f"\n[side, from 4-panel] processing {side_collage_path.name}")
    side_full = cv2.imread(str(side_collage_path))
    side_img = crop_side_from_4panel(side_full)
    cv2.imwrite(str(DEBUG_DIR / "side_cropped_4panel.jpg"), side_img)
    try:
        sm_4panel = extract_side_depths(side_img, front=fm)
        print(f"  body_height: {sm_4panel.body_height_cm:.2f} cm")
        print(f"  bust_depth:  {sm_4panel.bust_depth_cm:.2f} cm")
        print(f"  waist_depth: {sm_4panel.waist_depth_cm:.2f} cm")
        print(f"  hip_depth:   {sm_4panel.hip_depth_cm:.2f} cm")
        print(f"  thigh_depth: {sm_4panel.mid_thigh_depth_cm:.2f} cm")
    except Exception as e:
        print(f"  FAILED: {e}")
        sm_4panel = None

    # --- Side view from labeled reference ---
    labeled_path = REFERENCES / "labeled_reference.jpg"
    print(f"\n[side, from labeled_reference] processing {labeled_path.name}")
    labeled_full = cv2.imread(str(labeled_path))
    side_labeled = crop_side_from_labeled(labeled_full)
    cv2.imwrite(str(DEBUG_DIR / "side_cropped_labeled.jpg"), side_labeled)
    try:
        sm_labeled = extract_side_depths(side_labeled, front=fm)
        print(f"  body_height: {sm_labeled.body_height_cm:.2f} cm")
        print(f"  bust_depth:  {sm_labeled.bust_depth_cm:.2f} cm")
        print(f"  waist_depth: {sm_labeled.waist_depth_cm:.2f} cm")
        print(f"  hip_depth:   {sm_labeled.hip_depth_cm:.2f} cm")
        print(f"  thigh_depth: {sm_labeled.mid_thigh_depth_cm:.2f} cm")
    except Exception as e:
        print(f"  FAILED: {e}")
        sm_labeled = None

    # --- Choose side source: prefer 4-panel if both work, otherwise labeled ---
    if sm_4panel is not None and sm_labeled is not None:
        # Average for robustness on the AP depths
        def avg(a, b): return (a + b) / 2.0
        from src.photo_measure import SideMeasurements
        sm = SideMeasurements(
            pixels_per_cm=avg(sm_4panel.pixels_per_cm, sm_labeled.pixels_per_cm),
            bust_depth_cm=avg(sm_4panel.bust_depth_cm, sm_labeled.bust_depth_cm),
            waist_depth_cm=avg(sm_4panel.waist_depth_cm, sm_labeled.waist_depth_cm),
            hip_depth_cm=avg(sm_4panel.hip_depth_cm, sm_labeled.hip_depth_cm),
            mid_thigh_depth_cm=avg(sm_4panel.mid_thigh_depth_cm, sm_labeled.mid_thigh_depth_cm),
            knee_depth_cm=avg(sm_4panel.knee_depth_cm, sm_labeled.knee_depth_cm),
            mid_calf_depth_cm=avg(sm_4panel.mid_calf_depth_cm, sm_labeled.mid_calf_depth_cm),
            body_height_cm=avg(sm_4panel.body_height_cm, sm_labeled.body_height_cm),
        )
        side_source = "4panel + labeled (averaged)"
    else:
        sm = sm_4panel or sm_labeled
        side_source = "4panel only" if sm_4panel is not None else "labeled only"

    if sm is None:
        raise SystemExit("Could not extract side depths from any source")

    # --- Combine widths + depths into circumferences ---
    print(f"\n[circumferences] via Ramanujan (side source: {side_source})")
    circs = compute_circumferences(fm, sm)
    for k, v in circs.items():
        print(f"  {k}: {v:.2f} cm")

    # --- Build v2 measurements ---
    with OLD_PATH.open() as f:
        old = json.load(f)

    v2 = dict(old)
    v2.update({
        "bust_cm": round(circs["bust_cm"], 2),
        "waist_cm": round(circs["waist_cm"], 2),
        "hip_cm": round(circs["hip_cm"], 2),
        "thigh_circ_cm": round(circs["thigh_circ_cm"], 2),
        "knee_circ_cm": round(circs["knee_circ_cm"], 2),
        "calf_circ_cm": round(circs["calf_circ_cm"], 2),
        "shoulder_breadth_cm": round(fm.shoulder_width_cm, 2),
        "chest_depth_cm": round(sm.bust_depth_cm, 2),
        "waist_depth_cm": round(sm.waist_depth_cm, 2),
        "hip_depth_cm": round(sm.hip_depth_cm, 2),
    })
    # Carry over un-measurable fields from old (head_circ, neck, wrist, etc.)

    with NEW_PATH.open("w") as f:
        json.dump(v2, f, indent=2)
    print(f"\nwrote {NEW_PATH.relative_to(REPO_ROOT)}")

    # --- Comparison report ---
    keys_to_compare = [
        "stature_cm", "bust_cm", "waist_cm", "hip_cm",
        "shoulder_breadth_cm", "thigh_circ_cm", "knee_circ_cm", "calf_circ_cm",
        "chest_depth_cm", "waist_depth_cm", "hip_depth_cm",
    ]
    lines = ["# Pass 4 — Execution report\n"]
    lines.append("## Old vs new measurements\n")
    lines.append(f"Calibration: declared stature {DECLARED_HEIGHT_CM} cm.")
    lines.append(f"Front source: `front_full.jpg`. Side source: {side_source}.\n")
    lines.append("| measurement | old | new | delta | implied old method |")
    lines.append("| --- | --- | --- | --- | --- |")
    for k in keys_to_compare:
        oldv = old.get(k, "—")
        newv = v2.get(k, "—")
        try:
            delta = round(float(newv) - float(oldv), 2)
        except Exception:
            delta = "—"
        method = ""
        if k in ("bust_cm", "waist_cm", "hip_cm"):
            width_key = {"bust_cm": "bust_width_cm", "waist_cm": "waist_width_cm",
                         "hip_cm": "hip_width_cm"}[k]
            w = getattr(fm, width_key)
            implied = w * np.pi
            if abs(implied - oldv) < 2.0:
                method = f"old ≈ width × π ({w:.1f} × π = {implied:.1f})"
        lines.append(f"| {k} | {oldv} | {newv} | {delta} | {method} |")
    lines.append("\n## Front widths (extracted from `front_full.jpg`)\n")
    lines.append(f"- shoulder: {fm.shoulder_width_cm:.2f} cm")
    lines.append(f"- bust: {fm.bust_width_cm:.2f} cm")
    lines.append(f"- waist: {fm.waist_width_cm:.2f} cm")
    lines.append(f"- hip widest: {fm.hip_width_cm:.2f} cm")
    lines.append(f"- mid-thigh: {fm.mid_thigh_width_cm:.2f} cm")
    lines.append(f"- knee: {fm.knee_width_cm:.2f} cm")
    lines.append(f"- mid-calf: {fm.mid_calf_width_cm:.2f} cm")
    lines.append(f"- detected body height: {fm.body_height_cm:.2f} cm (declared {DECLARED_HEIGHT_CM})\n")
    lines.append("## Side depths\n")
    lines.append(f"- bust depth: {sm.bust_depth_cm:.2f} cm")
    lines.append(f"- waist depth: {sm.waist_depth_cm:.2f} cm")
    lines.append(f"- hip depth: {sm.hip_depth_cm:.2f} cm")
    lines.append(f"- thigh depth: {sm.mid_thigh_depth_cm:.2f} cm\n")
    lines.append("## W/H ratio\n")
    wh = v2["waist_cm"] / v2["hip_cm"]
    lines.append(f"- old W/H: {old['waist_cm']/old['hip_cm']:.3f}")
    lines.append(f"- new W/H: {wh:.3f}\n")
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines))
    print(f"wrote {REPORT_PATH.relative_to(REPO_ROOT)}")
    print(f"\nW/H: old {old['waist_cm']/old['hip_cm']:.3f}  →  new {wh:.3f}")


if __name__ == "__main__":
    main()
