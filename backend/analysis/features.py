"""
Feature engineering for sports movement analysis.

Computes meaningful biomechanical features from pose landmarks—not just raw positions.
Used by evaluator for scoring, injury risk, and motion fingerprinting.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np


@dataclass
class FrameFeatures:
    """Biomechanical features for a single frame."""

    # Joint angles (degrees)
    knee_angles: Dict[str, float] = field(default_factory=dict)  # left_knee, right_knee
    hip_angles: Dict[str, float] = field(default_factory=dict)
    ankle_angles: Dict[str, float] = field(default_factory=dict)
    shoulder_angles: Dict[str, float] = field(default_factory=dict)
    elbow_angles: Dict[str, float] = field(default_factory=dict)

    # Symmetry (0-1, 1 = perfect symmetry)
    left_right_symmetry: float = 1.0

    # Center of mass (normalized 0-1)
    com_x: float = 0.0
    com_y: float = 0.0

    # Stability (0-1, 1 = very stable)
    stability_score: float = 1.0

    # Angular velocity (deg/frame) - requires previous frame
    angular_velocity: Dict[str, float] = field(default_factory=dict)

    # Angular acceleration (deg/frame^2)
    angular_acceleration: Dict[str, float] = field(default_factory=dict)

    # Joint risk levels: "safe" | "moderate" | "high"
    joint_risk_levels: Dict[str, str] = field(default_factory=dict)

    def get_angle(self, joint: str) -> Optional[float]:
        """Get angle for joint (e.g. left_knee, right_hip)."""
        for d in (self.knee_angles, self.hip_angles, self.ankle_angles,
                  self.shoulder_angles, self.elbow_angles):
            if joint in d:
                return d[joint]
        return None


def angle_between(p1: Tuple[float, float, float], p2: Tuple[float, float, float],
                  p3: Tuple[float, float, float]) -> float:
    """Compute angle at p2 (vertex) in degrees. Points: (x, y, z)."""
    v1 = (p1[0] - p2[0], p1[1] - p2[1], (p1[2] - p2[2]) if len(p1) > 2 and len(p2) > 2 else 0)
    v2 = (p3[0] - p2[0], p3[1] - p2[1], (p3[2] - p2[2]) if len(p3) > 2 and len(p2) > 2 else 0)
    dot = v1[0] * v2[0] + v1[1] * v2[1] + v1[2] * v2[2]
    mag1 = np.sqrt(v1[0]**2 + v1[1]**2 + v1[2]**2) or 1e-6
    mag2 = np.sqrt(v2[0]**2 + v2[1]**2 + v2[2]**2) or 1e-6
    cos_a = np.clip(dot / (mag1 * mag2), -1, 1)
    return float(np.degrees(np.arccos(cos_a)))


def _get_pt(landmarks: Dict, name: str) -> Optional[Tuple[float, float, float]]:
    """Get (x, y, z) from landmarks."""
    if name not in landmarks:
        return None
    pt = landmarks[name]
    if isinstance(pt, (tuple, list)):
        if len(pt) >= 3:
            return (float(pt[0]), float(pt[1]), float(pt[2]))
        if len(pt) >= 2:
            return (float(pt[0]), float(pt[1]), 0.0)
    return None


def extract_frame_features(
    landmarks: Dict[str, Tuple[float, float, float]],
    prev_features: Optional[FrameFeatures] = None,
    fps: float = 30.0,
) -> FrameFeatures:
    """
    Extract biomechanical features from pose landmarks.

    Args:
        landmarks: Dict of landmark name -> (x, y, z)
        prev_features: Previous frame features (for velocity/acceleration)
        fps: Frame rate for temporal derivatives

    Returns:
        FrameFeatures with angles, symmetry, CoM, stability, velocities.
    """
    feat = FrameFeatures()

    def triple(p1, p2, p3):
        if p1 and p2 and p3:
            return angle_between(p1, p2, p3)
        return None

    # Knee angles: hip-knee-ankle
    l_hip = _get_pt(landmarks, "left_hip")
    l_knee = _get_pt(landmarks, "left_knee")
    l_ankle = _get_pt(landmarks, "left_ankle")
    r_hip = _get_pt(landmarks, "right_hip")
    r_knee = _get_pt(landmarks, "right_knee")
    r_ankle = _get_pt(landmarks, "right_ankle")

    l_knee_a = triple(l_hip, l_knee, l_ankle)
    r_knee_a = triple(r_hip, r_knee, r_ankle)
    if l_knee_a is not None:
        feat.knee_angles["left_knee"] = l_knee_a
    if r_knee_a is not None:
        feat.knee_angles["right_knee"] = r_knee_a

    # Hip angles: shoulder-hip-knee
    l_sh = _get_pt(landmarks, "left_shoulder")
    r_sh = _get_pt(landmarks, "right_shoulder")
    l_hip_a = triple(l_sh, l_hip, l_knee)
    r_hip_a = triple(r_sh, r_hip, r_knee)
    if l_hip_a is not None:
        feat.hip_angles["left_hip"] = l_hip_a
    if r_hip_a is not None:
        feat.hip_angles["right_hip"] = r_hip_a

    # Ankle angles: knee-ankle-foot_index
    l_foot = _get_pt(landmarks, "left_foot_index")
    r_foot = _get_pt(landmarks, "right_foot_index")
    l_ankle_a = triple(l_knee, l_ankle, l_foot or l_ankle)
    r_ankle_a = triple(r_knee, r_ankle, r_foot or r_ankle)
    if l_ankle_a is not None:
        feat.ankle_angles["left_ankle"] = l_ankle_a
    if r_ankle_a is not None:
        feat.ankle_angles["right_ankle"] = r_ankle_a

    # Shoulder angles: hip-shoulder-elbow
    l_elb = _get_pt(landmarks, "left_elbow")
    r_elb = _get_pt(landmarks, "right_elbow")
    l_sh_a = triple(l_hip, l_sh, l_elb)
    r_sh_a = triple(r_hip, r_sh, r_elb)
    if l_sh_a is not None:
        feat.shoulder_angles["left_shoulder"] = l_sh_a
    if r_sh_a is not None:
        feat.shoulder_angles["right_shoulder"] = r_sh_a

    # Elbow angles: shoulder-elbow-wrist
    l_wr = _get_pt(landmarks, "left_wrist")
    r_wr = _get_pt(landmarks, "right_wrist")
    l_elb_a = triple(l_sh, l_elb, l_wr)
    r_elb_a = triple(r_sh, r_elb, r_wr)
    if l_elb_a is not None:
        feat.elbow_angles["left_elbow"] = l_elb_a
    if r_elb_a is not None:
        feat.elbow_angles["right_elbow"] = r_elb_a

    # Left-right symmetry: compare corresponding angles
    sym_pairs = [
        (l_knee_a, r_knee_a),
        (l_hip_a, r_hip_a),
        (l_sh_a, r_sh_a),
        (l_elb_a, r_elb_a),
    ]
    diffs = []
    for a, b in sym_pairs:
        if a is not None and b is not None:
            diffs.append(abs(a - b))
    feat.left_right_symmetry = 1.0 - (np.mean(diffs) / 180.0) if diffs else 1.0
    feat.left_right_symmetry = max(0, min(1, feat.left_right_symmetry))

    # Center of mass: weighted average of key points
    points: List[Tuple[float, float, float]] = []
    if l_hip:
        points.append(l_hip)
    if r_hip:
        points.append(r_hip)
    if l_sh:
        points.append(l_sh)
    if r_sh:
        points.append(r_sh)
    if l_knee:
        points.append(l_knee)
    if r_knee:
        points.append(r_knee)
    if points:
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        feat.com_x = float(np.mean(xs))
        feat.com_y = float(np.mean(ys))

    # Stability: inverse of CoM variance over recent frames (single-frame placeholder)
    # Full stability requires multi-frame history; here we use symmetry + balance proxy
    feat.stability_score = feat.left_right_symmetry
    if l_ankle and r_ankle:
        ankle_dy = abs(l_ankle[1] - r_ankle[1])
        feat.stability_score = feat.stability_score * max(0, 1 - ankle_dy * 2)

    # Angular velocity and acceleration (frame-to-frame)
    if prev_features and fps > 0:
        dt = 1.0 / fps
        all_angles_now = {
            **feat.knee_angles,
            **feat.hip_angles,
            **feat.elbow_angles,
        }
        for jname, angle_now in all_angles_now.items():
            angle_prev = prev_features.get_angle(jname)
            if angle_prev is not None:
                vel = (angle_now - angle_prev) / dt
                feat.angular_velocity[jname] = vel
                vel_prev = prev_features.angular_velocity.get(jname)
                if vel_prev is not None:
                    acc = (vel - vel_prev) / dt
                    feat.angular_acceleration[jname] = acc

    return feat


def extract_frame_features_batch(
    landmarks_list: List[Dict[str, Tuple[float, float, float]]],
    fps: float = 30.0,
) -> List[FrameFeatures]:
    """
    Batch extract features from multiple frames using numpy for speed.
    Velocity/acceleration computed across consecutive frames.
    """
    if not landmarks_list:
        return []
    prev: Optional[FrameFeatures] = None
    out: List[FrameFeatures] = []
    for lm in landmarks_list:
        feat = extract_frame_features(lm, prev, fps)
        out.append(feat)
        prev = feat
    return out


def compute_motion_fingerprint(
    feature_sequence: List[FrameFeatures],
    window_size: int = 15,
) -> Dict[str, float]:
    """
    Aggregate features over a movement sequence to form a motion fingerprint.

    Returns mean and std of key metrics for movement classification/evaluation.
    """
    if not feature_sequence:
        return {}

    # Take last `window_size` frames
    seq = feature_sequence[-window_size:]

    fp: Dict[str, float] = {}

    knee_angles = []
    hip_angles = []
    for f in seq:
        knee_angles.extend(f.knee_angles.values())
        hip_angles.extend(f.hip_angles.values())
    if knee_angles:
        fp["knee_angle_mean"] = float(np.mean(knee_angles))
        fp["knee_angle_std"] = float(np.std(knee_angles))
    if hip_angles:
        fp["hip_angle_mean"] = float(np.mean(hip_angles))
        fp["hip_angle_std"] = float(np.std(hip_angles))

    syms = [f.left_right_symmetry for f in seq]
    fp["symmetry_mean"] = float(np.mean(syms))

    stabs = [f.stability_score for f in seq]
    fp["stability_mean"] = float(np.mean(stabs))

    vel_mags = []
    for f in seq:
        for v in f.angular_velocity.values():
            vel_mags.append(abs(v))
    if vel_mags:
        fp["angular_velocity_mean"] = float(np.mean(vel_mags))
        fp["angular_velocity_max"] = float(np.max(vel_mags))

    return fp
