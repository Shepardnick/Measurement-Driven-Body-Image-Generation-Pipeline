"""Build a primitive humanoid mesh from target measurements.

Y is up, X is the subject's right (from viewer: left), Z is forward (toward
viewer for the front view). Units are centimeters throughout. Origin at the
floor between the feet.

The body is a stack of ellipsoids and capsules. Anatomical fidelity is
deliberately low — this is scaffolding to validate the rendering pipeline,
not a SMPL-X replacement.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import pi
from typing import Any

import numpy as np
import trimesh


SKIN_RGBA = np.array([210, 180, 160, 255], dtype=np.uint8)


@dataclass
class Pose:
    """Relaxed standing pose — angles in radians.

    All angles default to zero (T-pose). Increase shoulder_outward to bring
    arms in toward the body.
    """

    shoulder_outward_rad: float = np.deg2rad(15.0)
    elbow_bend_rad: float = np.deg2rad(8.0)
    hip_outward_rad: float = np.deg2rad(3.0)


def build_proxy_body(m: dict[str, Any], pose: Pose | None = None) -> trimesh.Trimesh:
    if pose is None:
        pose = Pose()

    stature = m["stature_cm"]
    sitting_height = m["sitting_height_cm"]
    inseam = m["inseam_cm"]
    shoulder_breadth = m["shoulder_breadth_cm"]
    arm_length = m["arm_length_cm"]

    head_r = m["head_circ_cm"] / (2 * pi)
    neck_r = m["neck_circ_cm"] / (2 * pi)
    chest_lat_r = m["bust_cm"] / (2 * pi)
    chest_ap_r = m["chest_depth_cm"] / 2
    waist_lat_r = m["waist_cm"] / (2 * pi)
    waist_ap_r = m["waist_depth_cm"] / 2
    hip_lat_r = m["hip_cm"] / (2 * pi)
    hip_ap_r = m["hip_depth_cm"] / 2

    upper_arm_r = m["upper_arm_circ_cm"] / (2 * pi)
    forearm_r = m["forearm_circ_cm"] / (2 * pi)
    thigh_r = m["thigh_circ_cm"] / (2 * pi)
    calf_r = m["calf_circ_cm"] / (2 * pi)

    upper_arm_len = arm_length * 0.45
    forearm_len = arm_length * 0.55
    thigh_len = inseam * 0.48
    calf_len = inseam * 0.52

    head_h = 2 * head_r
    neck_h = max(0.05 * stature, 6.0)
    y_top = stature
    y_chin = y_top - head_h
    y_shoulder = y_chin - neck_h
    y_hip_joint = inseam
    y_pelvis_center = y_hip_joint + hip_ap_r * 0.5
    y_waist = stature - sitting_height + 0.55 * (y_shoulder - (stature - sitting_height))
    y_waist = max(y_pelvis_center + hip_ap_r * 0.6, min(y_waist, y_shoulder - 5))
    y_chest_center = (y_waist + y_shoulder) / 2

    parts: list[trimesh.Trimesh] = []

    head = _ellipsoid(head_r, head_r, head_r)
    head.apply_translation([0, y_chin + head_r, 0])
    parts.append(head)

    neck = _cylinder_y(radius=neck_r, length=neck_h)
    neck.apply_translation([0, y_shoulder + neck_h / 2, 0])
    parts.append(neck)

    chest_h = (y_shoulder - y_waist)
    chest = _ellipsoid(chest_lat_r, chest_h / 2, chest_ap_r)
    chest.apply_translation([0, y_chest_center, 0])
    parts.append(chest)

    pelvis_h = max(y_waist - y_hip_joint, 12.0)
    pelvis = _ellipsoid(hip_lat_r, pelvis_h / 2, hip_ap_r)
    pelvis.apply_translation([0, (y_waist + y_hip_joint) / 2, 0])
    parts.append(pelvis)

    waist_band_h = max(4.0, chest_h * 0.18)
    waist_band = _ellipsoid(waist_lat_r, waist_band_h / 2, waist_ap_r)
    waist_band.apply_translation([0, y_waist, 0])
    parts.append(waist_band)

    shoulder_x = shoulder_breadth / 2 - upper_arm_r * 0.6
    for side, sign in (("right", -1.0), ("left", +1.0)):
        shoulder = [sign * shoulder_x, y_shoulder, 0.0]
        arm_parts = _build_arm(
            shoulder=shoulder,
            upper_len=upper_arm_len,
            upper_r=upper_arm_r,
            fore_len=forearm_len,
            fore_r=forearm_r,
            outward_rad=pose.shoulder_outward_rad,
            elbow_bend_rad=pose.elbow_bend_rad,
            side_sign=sign,
        )
        parts.extend(arm_parts)

    hip_socket_x = hip_lat_r * 0.45
    for side, sign in (("right", -1.0), ("left", +1.0)):
        socket = [sign * hip_socket_x, y_hip_joint, 0.0]
        leg_parts = _build_leg(
            hip_socket=socket,
            thigh_len=thigh_len,
            thigh_r=thigh_r,
            calf_len=calf_len,
            calf_r=calf_r,
            outward_rad=pose.hip_outward_rad,
            side_sign=sign,
        )
        parts.extend(leg_parts)

    body = trimesh.util.concatenate(parts)
    body.visual.face_colors = SKIN_RGBA
    return body


def _ellipsoid(rx: float, ry: float, rz: float, subdivisions: int = 3) -> trimesh.Trimesh:
    s = trimesh.creation.icosphere(subdivisions=subdivisions, radius=1.0)
    s.vertices = s.vertices * np.array([rx, ry, rz])
    return s


def _cylinder_y(radius: float, length: float, sections: int = 24) -> trimesh.Trimesh:
    c = trimesh.creation.cylinder(radius=radius, height=length, sections=sections)
    R = trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0])
    c.apply_transform(R)
    return c


def _capsule_along_y(length: float, radius: float, sections: int = 20) -> trimesh.Trimesh:
    cyl = _cylinder_y(radius=radius, length=length)
    top = trimesh.creation.icosphere(subdivisions=2, radius=radius)
    top.apply_translation([0, length / 2, 0])
    bot = trimesh.creation.icosphere(subdivisions=2, radius=radius)
    bot.apply_translation([0, -length / 2, 0])
    return trimesh.util.concatenate([cyl, top, bot])


def _build_arm(
    shoulder: list[float],
    upper_len: float,
    upper_r: float,
    fore_len: float,
    fore_r: float,
    outward_rad: float,
    elbow_bend_rad: float,
    side_sign: float,
) -> list[trimesh.Trimesh]:
    upper = _capsule_along_y(length=upper_len, radius=upper_r)
    upper.apply_translation([0, -upper_len / 2, 0])
    R_shoulder = trimesh.transformations.rotation_matrix(
        side_sign * outward_rad, [0, 0, 1]
    )
    upper.apply_transform(R_shoulder)
    upper.apply_translation(shoulder)

    elbow_local = np.array([0, -upper_len, 0, 1.0])
    elbow_world = (R_shoulder @ elbow_local)[:3] + np.array(shoulder)

    fore = _capsule_along_y(length=fore_len, radius=fore_r)
    fore.apply_translation([0, -fore_len / 2, 0])
    R_elbow = trimesh.transformations.rotation_matrix(
        side_sign * (outward_rad - elbow_bend_rad), [0, 0, 1]
    )
    fore.apply_transform(R_elbow)
    fore.apply_translation(elbow_world.tolist())

    return [upper, fore]


def _build_leg(
    hip_socket: list[float],
    thigh_len: float,
    thigh_r: float,
    calf_len: float,
    calf_r: float,
    outward_rad: float,
    side_sign: float,
) -> list[trimesh.Trimesh]:
    thigh = _capsule_along_y(length=thigh_len, radius=thigh_r)
    thigh.apply_translation([0, -thigh_len / 2, 0])
    R_hip = trimesh.transformations.rotation_matrix(
        side_sign * outward_rad, [0, 0, 1]
    )
    thigh.apply_transform(R_hip)
    thigh.apply_translation(hip_socket)

    knee_local = np.array([0, -thigh_len, 0, 1.0])
    knee_world = (R_hip @ knee_local)[:3] + np.array(hip_socket)

    calf = _capsule_along_y(length=calf_len, radius=calf_r)
    calf.apply_translation([0, -calf_len / 2, 0])
    calf.apply_translation(knee_world.tolist())

    return [thigh, calf]
