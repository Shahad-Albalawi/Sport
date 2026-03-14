"""
Key movement frame detection for high-detail analysis.

Detects Landing, Strike, Jump, Throw moments for prioritized evaluation.
Uses angular velocity, CoM, and angle thresholds.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from backend.analysis.features import FrameFeatures, extract_frame_features

logger = logging.getLogger("sport_analysis.key_frame")

# Thresholds (tunable per sport)
LANDING_KNEE_FLEX_THRESHOLD = 25  # deg/frame - rapid knee flexion
JUMP_COM_VELOCITY_THRESHOLD = 0.03  # rapid CoM y drop (normalized)
STRIKE_ELBOW_VELOCITY_THRESHOLD = 50  # deg/frame - rapid elbow extension
THROW_SHOULDER_VELOCITY_THRESHOLD = 40  # deg/frame
WINDOW_SIZE = 3  # Frames for velocity smoothing


@dataclass
class KeyFrameEvent:
    """Detected key movement event."""

    frame_idx: int
    event_type: str  # "landing", "jump", "strike", "throw"
    confidence: float
    joint_angles: Dict[str, float]
    trigger_value: float


class KeyFrameDetector:
    """
    Detect high-impact movement frames for detailed analysis.
    Landing, Jump, Strike, Throw.
    """

    def __init__(
        self,
        knee_flex_threshold: float = LANDING_KNEE_FLEX_THRESHOLD,
        com_vel_threshold: float = JUMP_COM_VELOCITY_THRESHOLD,
        elbow_vel_threshold: float = STRIKE_ELBOW_VELOCITY_THRESHOLD,
        shoulder_vel_threshold: float = THROW_SHOULDER_VELOCITY_THRESHOLD,
    ):
        self.knee_flex_threshold = knee_flex_threshold
        self.com_vel_threshold = com_vel_threshold
        self.elbow_vel_threshold = elbow_vel_threshold
        self.shoulder_vel_threshold = shoulder_vel_threshold
        self._prev_com_y: Optional[float] = None
        self._prev_features: Optional[FrameFeatures] = None

    def reset(self) -> None:
        """Reset for new video."""
        self._prev_com_y = None
        self._prev_features = None

    def detect(
        self,
        frame_idx: int,
        features: FrameFeatures,
    ) -> Optional[KeyFrameEvent]:
        """
        Check if current frame is a key movement event.
        Returns KeyFrameEvent if detected, else None.
        """
        event = None

        # Landing: rapid knee flexion (negative angular velocity)
        for jname, vel in features.angular_velocity.items():
            if "knee" in jname and vel < -self.knee_flex_threshold:
                ang = features.knee_angles.get(jname, 0)
                event = KeyFrameEvent(
                    frame_idx=frame_idx,
                    event_type="landing",
                    confidence=min(1.0, abs(vel) / (self.knee_flex_threshold * 2)),
                    joint_angles=dict(features.knee_angles),
                    trigger_value=vel,
                )
                break

        # Jump: rapid CoM y decrease (moving up in frame = y decreases)
        if not event and self._prev_com_y is not None:
            dy = self._prev_com_y - features.com_y
            if dy > self.com_vel_threshold:
                event = KeyFrameEvent(
                    frame_idx=frame_idx,
                    event_type="jump",
                    confidence=min(1.0, dy / (self.com_vel_threshold * 2)),
                    joint_angles={**features.knee_angles, **features.hip_angles},
                    trigger_value=dy,
                )

        # Strike / Throw: rapid elbow or shoulder extension
        if not event:
            for jname, vel in features.angular_velocity.items():
                if "elbow" in jname and vel > self.elbow_vel_threshold:
                    event = KeyFrameEvent(
                        frame_idx=frame_idx,
                        event_type="strike",
                        confidence=min(1.0, vel / (self.elbow_vel_threshold * 2)),
                        joint_angles=dict(features.elbow_angles),
                        trigger_value=vel,
                    )
                    break
                if "shoulder" in jname and vel > self.shoulder_vel_threshold:
                    event = KeyFrameEvent(
                        frame_idx=frame_idx,
                        event_type="throw",
                        confidence=min(1.0, vel / (self.shoulder_vel_threshold * 2)),
                        joint_angles=dict(features.shoulder_angles),
                        trigger_value=vel,
                    )
                    break

        self._prev_com_y = features.com_y
        self._prev_features = features
        return event

    def is_key_frame(self, frame_idx: int, features: FrameFeatures) -> Tuple[bool, Optional[str]]:
        """
        Quick check: is this a key frame? Returns (is_key, event_type).
        """
        ev = self.detect(frame_idx, features)
        if ev:
            return True, ev.event_type
        return False, None
