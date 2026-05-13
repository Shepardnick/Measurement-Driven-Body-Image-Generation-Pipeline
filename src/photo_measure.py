"""Extract body measurements from reference photos.

Uses MediaPipe Pose for landmark detection and selfie segmentation for body
silhouette extraction. Combines widths from a front view + depths from a
side view via the Ramanujan ellipse perimeter formula to get true
circumferences — not width × π.

All measurement planes (bust, waist, hip widest, etc.) are anchored to
anatomical landmarks (shoulders, hips, knees) rather than fixed image
fractions, so the script is robust to subject pose variation.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import mediapipe as mp
import numpy as np


# MediaPipe Pose landmark indices we care about
LM = {
    "nose": 0,
    "left_eye_inner": 1,
    "left_eye": 2,
    "left_ear": 7,
    "right_ear": 8,
    "mouth_left": 9,
    "mouth_right": 10,
    "left_shoulder": 11,
    "right_shoulder": 12,
    "left_elbow": 13,
    "right_elbow": 14,
    "left_wrist": 15,
    "right_wrist": 16,
    "left_hip": 23,
    "right_hip": 24,
    "left_knee": 25,
    "right_knee": 26,
    "left_ankle": 27,
    "right_ankle": 28,
    "left_heel": 29,
    "right_heel": 30,
    "left_foot_index": 31,
    "right_foot_index": 32,
}


@dataclass
class PoseResult:
    """Output of detect_pose, in pixel coordinates."""
    landmarks_px: dict[str, tuple[float, float, float]]  # name -> (x, y, visibility)
    mask: np.ndarray  # binary uint8, body=1
    image_h: int
    image_w: int


_POSE_MODEL_PATH = (
    Path(__file__).resolve().parents[1] / "models" / "mediapipe" / "pose_landmarker_heavy.task"
)
_pose_detector_cache = None


def _get_pose_detector():
    """Lazy singleton — MediaPipe Tasks PoseLandmarker is expensive to build."""
    global _pose_detector_cache
    if _pose_detector_cache is not None:
        return _pose_detector_cache
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision

    base = mp_python.BaseOptions(model_asset_path=str(_POSE_MODEL_PATH))
    opts = mp_vision.PoseLandmarkerOptions(
        base_options=base,
        running_mode=mp_vision.RunningMode.IMAGE,
        output_segmentation_masks=True,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
    )
    _pose_detector_cache = mp_vision.PoseLandmarker.create_from_options(opts)
    return _pose_detector_cache


def detect_pose(image_bgr: np.ndarray) -> PoseResult:
    """Detect MediaPipe Pose landmarks + segmentation mask. Input is BGR."""
    h, w = image_bgr.shape[:2]
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)

    detector = _get_pose_detector()
    result = detector.detect(mp_image)
    if not result.pose_landmarks:
        raise RuntimeError("MediaPipe Pose found no body in the image")

    pose_landmarks = result.pose_landmarks[0]  # first detected pose
    landmarks_px: dict[str, tuple[float, float, float]] = {}
    for name, idx in LM.items():
        lm = pose_landmarks[idx]
        landmarks_px[name] = (lm.x * w, lm.y * h, lm.visibility)

    if result.segmentation_masks:
        seg = result.segmentation_masks[0].numpy_view()
        seg = np.squeeze(seg)  # MediaPipe returns (h, w, 1); flatten to (h, w)
        mask = (seg > 0.5).astype(np.uint8)
    else:
        mask = np.zeros((h, w), dtype=np.uint8)
    return PoseResult(landmarks_px=landmarks_px, mask=mask, image_h=h, image_w=w)


def widest_segment_at_y(mask: np.ndarray, y_px: float, expand: int = 3) -> tuple[int, int, int]:
    """Find the widest contiguous body segment crossing row y_px.

    Many subjects have legs separated below the crotch — naive "leftmost
    to rightmost body pixel" overcounts because it includes the empty
    space between the legs. We pick the single longest run of body
    pixels in the row (averaged over a few rows for robustness) instead.

    Returns (left_x, right_x, width_px).
    """
    h = mask.shape[0]
    y_int = int(round(y_px))
    y0 = max(0, y_int - expand)
    y1 = min(h, y_int + expand + 1)
    band = mask[y0:y1].any(axis=0).astype(np.uint8)

    if not band.any():
        return (0, 0, 0)

    # Find all contiguous runs of 1s, pick the longest
    diff = np.diff(np.concatenate([[0], band, [0]]))
    starts = np.where(diff == 1)[0]
    ends = np.where(diff == -1)[0]
    runs = list(zip(starts, ends, ends - starts))
    runs.sort(key=lambda r: -r[2])
    s, e, w = runs[0]
    return (int(s), int(e), int(w))


def total_body_extent_at_y(mask: np.ndarray, y_px: float, expand: int = 3) -> int:
    """Leftmost to rightmost body pixel across a row band (legs combined).

    Use this for hip widest, where the widest extent spans both glutes
    even if there's a gap between thighs further down.
    """
    h = mask.shape[0]
    y_int = int(round(y_px))
    y0 = max(0, y_int - expand)
    y1 = min(h, y_int + expand + 1)
    band = mask[y0:y1].any(axis=0)
    xs = np.where(band)[0]
    if len(xs) == 0:
        return 0
    return int(xs.max() - xs.min())


def find_body_y_bounds(mask: np.ndarray) -> tuple[int, int]:
    """Return (top_y, bottom_y) of the body silhouette in pixel coordinates."""
    rows = mask.any(axis=1)
    ys = np.where(rows)[0]
    if len(ys) == 0:
        raise RuntimeError("empty segmentation mask")
    return int(ys.min()), int(ys.max())


def find_min_width_y(mask: np.ndarray, y_top: float, y_bot: float) -> tuple[int, int]:
    """Find the Y row between y_top and y_bot with the narrowest body width.

    Useful for locating the waist (narrowest point between bust and hip).
    Returns (y_px, width_px).
    """
    y_top = int(max(0, y_top))
    y_bot = int(min(mask.shape[0] - 1, y_bot))
    if y_bot <= y_top:
        raise ValueError(f"bad search range y_top={y_top} y_bot={y_bot}")
    widths = []
    for y in range(y_top, y_bot + 1):
        _, _, w = widest_segment_at_y(mask, y, expand=0)
        widths.append(w)
    arr = np.array(widths)
    # smooth a bit
    if len(arr) > 5:
        kernel = np.ones(5) / 5.0
        arr = np.convolve(arr, kernel, mode="same")
    rel = np.argmin(arr)
    return (y_top + rel, int(widths[rel]))


def find_max_width_y(mask: np.ndarray, y_top: float, y_bot: float, use_total_extent: bool = False) -> tuple[int, int]:
    """Find the Y row in [y_top, y_bot] with the widest body width.

    use_total_extent=True for hips (combined-legs extent).
    """
    y_top = int(max(0, y_top))
    y_bot = int(min(mask.shape[0] - 1, y_bot))
    if y_bot <= y_top:
        raise ValueError(f"bad search range y_top={y_top} y_bot={y_bot}")
    widths = []
    for y in range(y_top, y_bot + 1):
        if use_total_extent:
            w = total_body_extent_at_y(mask, y, expand=0)
        else:
            _, _, w = widest_segment_at_y(mask, y, expand=0)
        widths.append(w)
    arr = np.array(widths)
    if len(arr) > 5:
        kernel = np.ones(5) / 5.0
        arr = np.convolve(arr, kernel, mode="same")
    rel = np.argmax(arr)
    return (y_top + rel, int(widths[rel]))


def pixels_per_cm_from_height(
    mask: np.ndarray,
    declared_height_cm: float,
) -> float:
    """Calibration: body silhouette top→bottom pixel extent = declared height."""
    y_top, y_bot = find_body_y_bounds(mask)
    height_px = y_bot - y_top
    if height_px <= 0:
        raise RuntimeError("zero-height body bounds; bad segmentation")
    return height_px / declared_height_cm


def ellipse_perimeter_ramanujan(width: float, depth: float) -> float:
    """Ramanujan's approximation for the perimeter of an ellipse.

    width, depth are the two full diameters (not radii). Returns perimeter
    in the same units. Accuracy is within 0.04% for any aspect ratio that
    occurs on a human body.
    """
    a = width / 2.0
    b = depth / 2.0
    if a <= 0 or b <= 0:
        return 0.0
    h = ((a - b) / (a + b)) ** 2
    return float(np.pi * (a + b) * (1 + 3 * h / (10 + np.sqrt(4 - 3 * h))))


@dataclass
class FrontMeasurements:
    """Widths extracted from a front view, in cm.

    *_width_cm fields are corrected for arms-in-silhouette by subtracting
    2×upper_arm_width_cm where arms cross the measurement plane. waist_width_cm
    is NOT corrected — the waist plane sits between elbow and wrist, so arms
    are usually not at waist Y.
    """
    pixels_per_cm: float
    head_top_y_px: int
    feet_y_px: int
    shoulder_y_px: int
    bust_y_px: int
    waist_y_px: int
    hip_widest_y_px: int
    mid_thigh_y_px: int
    knee_y_px: int
    mid_calf_y_px: int
    shoulder_width_cm: float
    upper_arm_width_cm: float
    bust_width_silhouette_cm: float  # raw silhouette including arms
    bust_width_cm: float              # after arm subtraction
    waist_width_cm: float
    hip_width_silhouette_cm: float
    hip_width_cm: float               # after arm subtraction
    mid_thigh_width_cm: float
    knee_width_cm: float
    mid_calf_width_cm: float
    body_height_cm: float
    landmarks_px: dict[str, tuple[float, float, float]]


def extract_front_widths(
    image_bgr: np.ndarray,
    declared_height_cm: float = 193.04,
) -> FrontMeasurements:
    pr = detect_pose(image_bgr)
    mask = pr.mask
    lm = pr.landmarks_px

    shoulder_y = (lm["left_shoulder"][1] + lm["right_shoulder"][1]) / 2.0
    hip_lm_y = (lm["left_hip"][1] + lm["right_hip"][1]) / 2.0
    knee_y = (lm["left_knee"][1] + lm["right_knee"][1]) / 2.0
    ankle_y = (lm["left_ankle"][1] + lm["right_ankle"][1]) / 2.0

    y_top, y_bot = find_body_y_bounds(mask)
    pix_per_cm = pixels_per_cm_from_height(mask, declared_height_cm)

    # Bust = max torso width below shoulder and above the bust→waist midpoint
    bust_search_top = shoulder_y + (hip_lm_y - shoulder_y) * 0.15
    bust_search_bot = shoulder_y + (hip_lm_y - shoulder_y) * 0.40
    bust_y, bust_w_px = find_max_width_y(mask, bust_search_top, bust_search_bot)

    # Waist = min torso width between bust and the MP hip landmarks
    waist_y, waist_w_px = find_min_width_y(mask, bust_y + 5, hip_lm_y)

    # Hip widest = max width at or just below MP hip landmarks, before the
    # thighs start to separate too much; use total-extent (combined legs).
    hip_search_top = hip_lm_y - (hip_lm_y - waist_y) * 0.15
    hip_search_bot = hip_lm_y + (knee_y - hip_lm_y) * 0.35
    hip_y, hip_w_px = find_max_width_y(mask, hip_search_top, hip_search_bot, use_total_extent=True)

    # Mid-thigh = halfway between hip widest and knee, single leg
    mid_thigh_y = int((hip_y + knee_y) / 2.0)
    _, _, mid_thigh_w_px = widest_segment_at_y(mask, mid_thigh_y, expand=4)

    # Knee
    _, _, knee_w_px = widest_segment_at_y(mask, knee_y, expand=4)

    # Mid-calf
    mid_calf_y = int((knee_y + ankle_y) / 2.0)
    _, _, mid_calf_w_px = widest_segment_at_y(mask, mid_calf_y, expand=4)

    # Shoulder width: distance between MP shoulder landmarks (biacromial)
    shoulder_w_px = abs(lm["left_shoulder"][0] - lm["right_shoulder"][0])

    def to_cm(px: float) -> float:
        return px / pix_per_cm

    upper_arm_w_cm = estimate_upper_arm_width(mask, lm, pix_per_cm)

    # Subtract arms from bust/hip silhouette widths. Waist sits between elbow
    # and wrist so arms typically don't cross the waist plane.
    bust_silhouette = to_cm(bust_w_px)
    hip_silhouette = to_cm(hip_w_px)
    bust_corrected = max(0.0, bust_silhouette - 2.0 * upper_arm_w_cm)
    hip_corrected = max(0.0, hip_silhouette - 2.0 * upper_arm_w_cm)

    return FrontMeasurements(
        pixels_per_cm=pix_per_cm,
        head_top_y_px=y_top,
        feet_y_px=y_bot,
        shoulder_y_px=int(shoulder_y),
        bust_y_px=int(bust_y),
        waist_y_px=int(waist_y),
        hip_widest_y_px=int(hip_y),
        mid_thigh_y_px=int(mid_thigh_y),
        knee_y_px=int(knee_y),
        mid_calf_y_px=int(mid_calf_y),
        shoulder_width_cm=to_cm(shoulder_w_px),
        upper_arm_width_cm=upper_arm_w_cm,
        bust_width_silhouette_cm=bust_silhouette,
        bust_width_cm=bust_corrected,
        waist_width_cm=to_cm(waist_w_px),
        hip_width_silhouette_cm=hip_silhouette,
        hip_width_cm=hip_corrected,
        mid_thigh_width_cm=to_cm(mid_thigh_w_px),
        knee_width_cm=to_cm(knee_w_px),
        mid_calf_width_cm=to_cm(mid_calf_w_px),
        body_height_cm=(y_bot - y_top) / pix_per_cm,
        landmarks_px=lm,
    )


def estimate_upper_arm_width(
    front_mask: np.ndarray,
    landmarks_px: dict,
    pix_per_cm: float,
) -> float:
    """Estimate one upper arm's lateral width (cm) from the silhouette at biceps level.

    At biceps Y (between shoulder and elbow), the silhouette includes torso + 2
    arms. We approximate the torso width at biceps Y using the MediaPipe
    shoulder breadth, then attribute the excess to the two arms.
    """
    sh_l = landmarks_px["left_shoulder"]
    sh_r = landmarks_px["right_shoulder"]
    el_l = landmarks_px["left_elbow"]
    el_r = landmarks_px["right_elbow"]

    biceps_y = (sh_l[1] + sh_r[1] + el_l[1] + el_r[1]) / 4.0
    _, _, sil_w = widest_segment_at_y(front_mask, biceps_y, expand=4)
    sil_cm = sil_w / pix_per_cm

    shoulder_breadth_px = abs(sh_l[0] - sh_r[0])
    shoulder_breadth_cm = shoulder_breadth_px / pix_per_cm
    # Torso at biceps level is roughly shoulder breadth + small chest flare
    torso_at_biceps_cm = shoulder_breadth_cm * 1.05

    excess_cm = max(0.0, sil_cm - torso_at_biceps_cm)
    return excess_cm / 2.0  # divide between two arms


@dataclass
class SideMeasurements:
    """Depths extracted from a side view, in cm. Same Y planes as the front."""
    pixels_per_cm: float
    bust_depth_cm: float
    waist_depth_cm: float
    hip_depth_cm: float
    mid_thigh_depth_cm: float
    knee_depth_cm: float
    mid_calf_depth_cm: float
    body_height_cm: float


def extract_side_depths(
    image_bgr: np.ndarray,
    front: FrontMeasurements,
    subtract_arm: bool = True,
) -> SideMeasurements:
    """Run on a side-profile photo, calibrated against the front view's torso
    length (shoulder→hip in cm) so it works even on a cropped side photo
    that doesn't show the full body.

    Calibration: detect MP shoulders and hips in the side image; the vertical
    pixel distance corresponds to the same shoulder→hip cm distance measured
    in the front view. Y planes for bust/waist/hip widest/thigh are then
    located by anatomical-fraction offsets from these landmarks.
    """
    pr = detect_pose(image_bgr)
    mask = pr.mask
    lm = pr.landmarks_px

    # Side calibration: shoulder→hip pixel distance ↔ same cm distance from front
    side_sh_y = (lm["left_shoulder"][1] + lm["right_shoulder"][1]) / 2.0
    side_hip_y = (lm["left_hip"][1] + lm["right_hip"][1]) / 2.0
    side_torso_px = abs(side_hip_y - side_sh_y)

    front_sh_y = front.shoulder_y_px
    front_hip_y_landmark = (
        front.landmarks_px["left_hip"][1] + front.landmarks_px["right_hip"][1]
    ) / 2.0
    front_torso_px = abs(front_hip_y_landmark - front_sh_y)
    front_torso_cm = front_torso_px / front.pixels_per_cm

    if side_torso_px <= 0 or front_torso_cm <= 0:
        raise RuntimeError("zero torso length in side or front view")

    pix_per_cm = side_torso_px / front_torso_cm

    # Y planes by interpolation between side shoulder and side hip landmarks.
    # The hip MP landmark sits at iliac crest level which is slightly above
    # "hip widest" (trochanter); we extrapolate ~10% past the landmark for hip.
    def y_lerp(t: float) -> float:
        return side_sh_y + t * (side_hip_y - side_sh_y)

    bust_y = int(y_lerp(0.35))       # ~35% from shoulder to hip
    waist_y = int(y_lerp(0.75))      # ~75% from shoulder to hip
    hip_y = int(y_lerp(1.10))        # ~10% past MP hip landmark
    thigh_y = int(y_lerp(1.50))      # ~50% past MP hip landmark
    knee_y = int(y_lerp(2.10))       # if visible
    calf_y = int(y_lerp(2.60))       # if visible

    h_total = mask.shape[0]
    # Subtract one arm's lateral width from depth because the arm hangs in
    # the silhouette and adds anteriorly or posteriorly to the body depth.
    arm_subtract_cm = front.upper_arm_width_cm if subtract_arm else 0.0

    def safe_depth(y: int) -> float:
        if y < 0 or y >= h_total:
            return 0.0
        _, _, w = widest_segment_at_y(mask, y, expand=4)
        raw_cm = w / pix_per_cm
        return max(0.0, raw_cm - arm_subtract_cm)

    return SideMeasurements(
        pixels_per_cm=pix_per_cm,
        bust_depth_cm=safe_depth(bust_y),
        waist_depth_cm=safe_depth(waist_y),
        hip_depth_cm=safe_depth(hip_y),
        mid_thigh_depth_cm=safe_depth(thigh_y),
        knee_depth_cm=safe_depth(knee_y),
        mid_calf_depth_cm=safe_depth(calf_y),
        body_height_cm=front_torso_cm * (h_total / side_torso_px),
    )


def _circ_or_fallback(width: float, depth: float, fallback_aspect: float = 0.95) -> float:
    """Ellipse perimeter from width+depth, or fallback to a near-circular
    cylinder approximation (depth = fallback_aspect × width) when depth is 0."""
    if depth <= 0 or width <= 0:
        if width <= 0:
            return 0.0
        depth = width * fallback_aspect
    return ellipse_perimeter_ramanujan(width, depth)


def compute_circumferences(
    front: FrontMeasurements,
    side: SideMeasurements,
) -> dict[str, float]:
    """Combine widths + depths via Ramanujan into proper circumferences (cm).

    For limbs (thigh/knee/calf), if the side photo didn't reach low enough
    we fall back to a near-circular cross-section (depth ≈ 0.95 × width).
    """
    return {
        "bust_cm":      _circ_or_fallback(front.bust_width_cm,      side.bust_depth_cm),
        "waist_cm":     _circ_or_fallback(front.waist_width_cm,     side.waist_depth_cm),
        "hip_cm":       _circ_or_fallback(front.hip_width_cm,       side.hip_depth_cm),
        "thigh_circ_cm": _circ_or_fallback(front.mid_thigh_width_cm, side.mid_thigh_depth_cm, fallback_aspect=1.0),
        "knee_circ_cm":  _circ_or_fallback(front.knee_width_cm,      side.knee_depth_cm,       fallback_aspect=0.92),
        "calf_circ_cm":  _circ_or_fallback(front.mid_calf_width_cm,  side.mid_calf_depth_cm,   fallback_aspect=1.0),
    }
