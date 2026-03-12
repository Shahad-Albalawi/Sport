"""Movement recognition from pose landmarks over time.

Detects fundamental athletic movements with sport-aware scoring:
kick, jump, sprint, punch, swing, throw, squat, lunge, rotation.
Each movement has refined thresholds for higher accuracy.
"""

import logging
from collections import deque
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("sport_analysis.movement")

MOVEMENT_TYPES = [
    "kick", "jump", "sprint", "punch", "swing", "throw", "squat", "lunge", "rotation"
]

# Minimum scores to override other movements (prevents false positives)
MOVEMENT_DOMINANCE = {
    "squat": 0.55,
    "lunge": 0.5,
    "kick": 0.5,
    "jump": 0.5,
    "punch": 0.45,
    "swing": 0.45,
    "throw": 0.5,
    "sprint": 0.4,
    "rotation": 0.4,
}

# Temporal smoothing: frames new movement must dominate before switching
STICKY_FRAMES = 6
HYSTERESIS_FACTOR = 1.15  # New movement must exceed current by this to override
# Sequence consistency: boost confidence when movement persists (LSTM-like)
SEQUENCE_CONSISTENCY_BOOST = 0.08  # Bonus per frame of consistency (max ~0.2)


class MovementRecognizer:
    """Detect athletic movements from pose sequence."""

    def __init__(self, window_size: int = 15, min_confidence: float = 0.4):
        self.window_size = window_size
        self.min_confidence = min_confidence
        self.landmark_history: deque = deque(maxlen=window_size)
        self._current_movement = "unknown"
        self._current_confidence = 0.0
        self._sticky_counter = 0  # Frames new movement has been candidate
        self._candidate_movement = "unknown"
        self._candidate_confidence = 0.0

    def _get_landmark(self, landmarks: Dict, name: str) -> Optional[Tuple[float, float]]:
        if name in landmarks:
            return landmarks[name][0], landmarks[name][1]
        return None

    def _angle(self, p1, p2, p3) -> float:
        """Angle at p2 (degrees)."""
        v1 = (p1[0] - p2[0], p1[1] - p2[1])
        v2 = (p3[0] - p2[0], p3[1] - p2[1])
        dot = v1[0] * v2[0] + v1[1] * v2[1]
        mag1 = (v1[0]**2 + v1[1]**2) ** 0.5 or 1e-6
        mag2 = (v2[0]**2 + v2[1]**2) ** 0.5 or 1e-6
        cos_a = max(-1, min(1, dot / (mag1 * mag2)))
        return float(np.degrees(np.arccos(cos_a)))

    def _velocity(self, hist: List[Dict], key: str) -> float:
        """Average velocity of landmark over recent frames."""
        if len(hist) < 2:
            return 0.0
        total = 0.0
        n = 0
        for i in range(1, len(hist)):
            p0 = self._get_landmark(hist[i-1], key)
            p1 = self._get_landmark(hist[i], key)
            if p0 and p1:
                dx = p1[0] - p0[0]
                dy = p1[1] - p0[1]
                total += (dx**2 + dy**2) ** 0.5
                n += 1
        return total / max(n, 1)

    def _vertical_range(self, hist: List[Dict], key: str) -> float:
        """Range of vertical motion."""
        ys = []
        for h in hist:
            p = self._get_landmark(h, key)
            if p:
                ys.append(p[1])
        return max(ys) - min(ys) if ys else 0.0

    def recognize(
        self,
        landmarks: Optional[Dict[str, Tuple[float, float, float]]] = None,
    ) -> Tuple[str, float]:
        """
        Detect movement from pose sequence.
        Returns (movement_name, confidence).
        """
        if landmarks:
            self.landmark_history.append(landmarks.copy())
        hist = list(self.landmark_history)

        if len(hist) < 5:
            return self._current_movement, self._current_confidence

        scores: Dict[str, float] = {m: 0.0 for m in MOVEMENT_TYPES}

        # Knee angles (squat, lunge)
        l_hip = self._get_landmark(hist[-1], "left_hip")
        l_knee = self._get_landmark(hist[-1], "left_knee")
        l_ankle = self._get_landmark(hist[-1], "left_ankle")
        r_hip = self._get_landmark(hist[-1], "right_hip")
        r_knee = self._get_landmark(hist[-1], "right_knee")
        r_ankle = self._get_landmark(hist[-1], "right_ankle")

        avg_knee = 0.0
        knee_count = 0
        if l_hip and l_knee and l_ankle:
            avg_knee += self._angle(l_hip, l_knee, l_ankle)
            knee_count += 1
        if r_hip and r_knee and r_ankle:
            avg_knee += self._angle(r_hip, r_knee, r_ankle)
            knee_count += 1
        avg_knee = avg_knee / knee_count if knee_count else 180

        # Squat: knees bent (low angle), hips drop
        if avg_knee < 120:
            drop = self._vertical_range(hist, "left_hip") + self._vertical_range(hist, "right_hip")
            scores["squat"] = min(1.0, (120 - avg_knee) / 60 * 0.8 + drop * 2)

        # Lunge: asymmetric knee angles, one leg forward
        if l_hip and l_knee and l_ankle and r_hip and r_knee and r_ankle:
            l_ang = self._angle(l_hip, l_knee, l_ankle)
            r_ang = self._angle(r_hip, r_knee, r_ankle)
            asym = abs(l_ang - r_ang)
            if asym > 30 and min(l_ang, r_ang) < 120:
                scores["lunge"] = min(1.0, asym / 60)

        # Jump: rapid vertical motion at ankles
        ankle_vel = self._velocity(hist, "left_ankle") + self._velocity(hist, "right_ankle")
        ankle_range = self._vertical_range(hist, "left_ankle") + self._vertical_range(hist, "right_ankle")
        if ankle_range > 0.08 and ankle_vel > 0.02:
            scores["jump"] = min(1.0, ankle_vel * 20 + ankle_range * 5)

        # Sprint: high horizontal leg velocity
        knee_vel = self._velocity(hist, "left_knee") + self._velocity(hist, "right_knee")
        ankle_vel_h = knee_vel
        if knee_vel > 0.03:
            scores["sprint"] = min(1.0, knee_vel * 15)

        # Kick: one leg rapid extension
        l_leg_vel = self._velocity(hist, "left_ankle")
        r_leg_vel = self._velocity(hist, "right_ankle")
        if abs(l_leg_vel - r_leg_vel) > 0.02 and max(l_leg_vel, r_leg_vel) > 0.025:
            scores["kick"] = min(1.0, max(l_leg_vel, r_leg_vel) * 25)

        # Punch: rapid arm extension
        l_arm_vel = self._velocity(hist, "left_wrist")
        r_arm_vel = self._velocity(hist, "right_wrist")
        if l_arm_vel > 0.03 or r_arm_vel > 0.03:
            scores["punch"] = min(1.0, max(l_arm_vel, r_arm_vel) * 20)

        # Swing: rotational arm motion (elbow + shoulder)
        l_elb = self._get_landmark(hist[-1], "left_elbow")
        r_elb = self._get_landmark(hist[-1], "right_elbow")
        l_sh = self._get_landmark(hist[-1], "left_shoulder")
        r_sh = self._get_landmark(hist[-1], "right_shoulder")
        l_wr = self._get_landmark(hist[-1], "left_wrist")
        r_wr = self._get_landmark(hist[-1], "right_wrist")
        elbow_vel = self._velocity(hist, "left_elbow") + self._velocity(hist, "right_elbow")
        if l_elb and l_sh and l_wr:
            l_elb_ang = self._angle(l_sh, l_elb, l_wr)
            if 30 < l_elb_ang < 150 and elbow_vel > 0.02:
                scores["swing"] = min(1.0, elbow_vel * 25)
        if r_elb and r_sh and r_wr:
            r_elb_ang = self._angle(r_sh, r_elb, r_wr)
            if 30 < r_elb_ang < 150 and elbow_vel > 0.02:
                scores["swing"] = max(scores["swing"], min(1.0, elbow_vel * 25))

        # Throw: similar to swing but with more arm extension
        if scores["swing"] > 0.3 and elbow_vel > 0.035:
            scores["throw"] = min(1.0, scores["swing"] * 1.2)

        # Rotation: hip/shoulder twist
        if len(hist) >= 5:
            l_hip_0 = self._get_landmark(hist[0], "left_hip")
            r_hip_0 = self._get_landmark(hist[0], "right_hip")
            l_hip_n = self._get_landmark(hist[-1], "left_hip")
            r_hip_n = self._get_landmark(hist[-1], "right_hip")
            if l_hip_0 and r_hip_0 and l_hip_n and r_hip_n:
                dx0 = r_hip_0[0] - l_hip_0[0]
                dxn = r_hip_n[0] - l_hip_n[0]
                twist = abs(dxn - dx0)
                if twist > 0.05:
                    scores["rotation"] = min(1.0, twist * 8)

        # Pick best movement - require dominance threshold for high-confidence sports movements
        best = max(scores, key=scores.get)
        conf = float(scores[best])
        dom = MOVEMENT_DOMINANCE.get(best, self.min_confidence)

        # Temporal smoothing: require new movement to dominate for STICKY_FRAMES before switch
        if best == self._candidate_movement:
            self._sticky_counter += 1
            self._candidate_confidence = max(self._candidate_confidence, conf)
        else:
            self._sticky_counter = 1
            self._candidate_movement = best
            self._candidate_confidence = conf

        # Switch only if: (1) candidate sustained for STICKY_FRAMES, and (2) meets threshold
        if self._sticky_counter >= STICKY_FRAMES and self._candidate_confidence >= dom:
            # Hysteresis: new must beat current by factor to override quickly
            if (
                self._current_movement == "unknown"
                or self._candidate_confidence >= self._current_confidence * HYSTERESIS_FACTOR
            ):
                self._current_movement = self._candidate_movement
                self._current_confidence = min(1.0, self._candidate_confidence)
        elif conf >= dom and (not self._current_movement or self._current_movement == "unknown"):
            self._current_movement = best
            self._current_confidence = min(1.0, conf)
        elif conf < 0.15:
            self._current_confidence *= 0.92
            if self._current_confidence < 0.2:
                self._current_movement = "unknown"
                self._sticky_counter = 0

        return self._current_movement, self._current_confidence
