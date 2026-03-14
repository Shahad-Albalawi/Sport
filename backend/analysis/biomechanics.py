"""
Biomechanics rules and injury risk analysis.

Defines safe ranges for joint angles per movement per sport.
Maps detected errors to possible injuries and coaching advice.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from backend.analysis.sport_profiles import get_sport_profile, get_ideal_angle_fallback


@dataclass
class SafeRange:
    """Safe angle range (degrees) for a joint in a movement."""

    joint: str
    movement: str
    min_deg: float
    max_deg: float
    risk_below_min: str  # e.g. "ACL risk - knee too flexed at landing"
    risk_above_max: str


# Error -> (coaching_advice, possible_injuries)
ERROR_COACHING_MAP: Dict[str, Tuple[str, List[str]]] = {
    "knee_valgus": (
        "Keep knees aligned with toes. Strengthen glutes. Control landing with soft knees.",
        ["ACL tear", "MCL strain", "Patellofemoral pain"],
    ),
    "knee_angle_unsafe": (
        "Maintain knee within safe range for this movement. Avoid hyperextension or excessive flexion under load.",
        ["ACL injury", "Meniscus tear", "Patellar tendinitis"],
    ),
    "poor_hip_extension": (
        "Drive through the hip for power. Engage glutes at lockout.",
        ["Lower back strain", "Hip flexor strain", "Hip impingement"],
    ),
    "ankle_instability": (
        "Strengthen calves. Practice soft landings. Add balance work.",
        ["Ankle sprain", "Achilles tendinitis", "Chronic ankle instability"],
    ),
    "unstable_landing": (
        "Practice soft landings with bent knees. Land with feet shoulder-width apart.",
        ["Knee injury", "Ankle sprain", "Stress fracture"],
    ),
    "shoulder_imbalance": (
        "Improve shoulder symmetry. Rotator cuff strengthening. Retract scapula.",
        ["Rotator cuff strain", "Impingement", "Labral tear"],
    ),
    "limited_rotation": (
        "Drive from hips and core. Unit turn. Hip-shoulder separation.",
        ["Spine compensation", "Lower back strain", "Hip strain"],
    ),
    "elbow_alignment": (
        "Keep elbow in line with wrist. Avoid flaring.",
        ["Elbow strain", "Tennis elbow", "UCL injury"],
    ),
    "elbow_drop": (
        "Maintain guard position. Elbows in.",
        ["Body exposure (sport-specific)", "Elbow strain"],
    ),
    "core_instability": (
        "Engage core during movement. Breathe and brace. Hollow body holds.",
        ["Lower back stress", "Hernia risk", "Poor posture"],
    ),
    "unstable_posture": (
        "Maintain upright posture. Slight lean from ankles. Core engaged.",
        ["Lower back strain", "Hip strain"],
    ),
}


# Default safe ranges: (min, max) degrees. Used when movement-specific not defined.
# Landing/jump: knee < 160° = high ACL risk
DEFAULT_SAFE_RANGES: Dict[str, Dict[str, Tuple[float, float]]] = {
    "landing": {"knee": (140, 170), "hip": (80, 120)},
    "jump": {"knee": (140, 170), "hip": (80, 120)},
    "squat": {"knee": (70, 120), "hip": (60, 100)},
    "lunge": {"knee": (70, 120), "hip": (80, 120)},
    "sprint": {"knee": (155, 180), "hip": (165, 200)},
    "kick": {"knee": (140, 180), "hip": (80, 120)},
    "throw": {"elbow": (80, 140), "shoulder": (60, 120)},
    "swing": {"elbow": (90, 150), "shoulder": (60, 120)},
    "punch": {"elbow": (150, 180), "shoulder": (0, 15)},
    "static": {"knee": (160, 180), "hip": (160, 185)},
}


def get_safe_range(sport: str, joint: str, movement: str) -> Tuple[float, float]:
    """Get safe angle range (min, max) for joint in movement. Uses training overrides when available."""
    sport = (sport or "unknown").lower()
    movement = (movement or "unknown").lower()
    joint = (joint or "").lower()

    # Check sport-specific training overrides first (from continuous improvement)
    try:
        from backend.training.data_store import load_sport_training_data
        data = load_sport_training_data(sport)
        overrides = data.get("safe_ranges_overrides", {})
        for key, val in overrides.items():
            if "__" in key:
                mov, j = key.split("__", 1)
                jbase = joint.replace("left_", "").replace("right_", "")
                if mov.lower() in movement or movement in mov.lower():
                    if j in joint or jbase in j or j in jbase:
                        if isinstance(val, dict) and "min" in val and "max" in val:
                            return float(val["min"]), float(val["max"])
    except Exception:
        pass

    profile = get_sport_profile(sport)
    ideal = profile.get("ideal_angles", {})

    # Try movement-specific key
    key = f"{joint}_{movement}"
    if key in ideal and isinstance(ideal[key], (tuple, list)) and len(ideal[key]) >= 2:
        v = ideal[key]
        return float(v[0]), float(v[1])

    # Try generic joint
    if joint in ideal and isinstance(ideal[joint], (tuple, list)) and len(ideal[joint]) >= 2:
        v = ideal[joint]
        return float(v[0]), float(v[1])

    # Fallback: sport-specific generic
    fb = get_ideal_angle_fallback(sport, joint)
    if fb:
        return float(fb[0]), float(fb[1])

    # Default by movement type
    for mov_key, ranges in DEFAULT_SAFE_RANGES.items():
        if mov_key in movement or movement in mov_key:
            if joint in ranges:
                return ranges[joint]

    # Generic defaults
    if "knee" in joint:
        return (140, 175)
    if "hip" in joint:
        return (80, 120)
    if "elbow" in joint:
        return (80, 150)
    if "shoulder" in joint:
        return (60, 120)
    if "ankle" in joint:
        return (80, 120)
    return (100, 170)


def check_angle_safety(
    angle: float, joint: str, sport: str, movement: str
) -> Tuple[str, Optional[str]]:
    """
    Check if angle is within safe range.
    Returns (risk_level, warning_message).
    risk_level: "safe" | "moderate" | "high"
    """
    min_deg, max_deg = get_safe_range(sport, joint, movement)
    if min_deg <= angle <= max_deg:
        return "safe", None

    # Extend bounds slightly for "moderate"
    margin = (max_deg - min_deg) * 0.15
    if min_deg - margin <= angle <= max_deg + margin:
        return "moderate", f"{joint.replace('_', ' ').title()} angle {angle:.0f}° outside ideal range ({min_deg:.0f}-{max_deg:.0f}°)"

    # High risk
    if angle < min_deg:
        msg = f"{joint.replace('_', ' ').title()} too flexed ({angle:.0f}° < {min_deg:.0f}°) - high injury risk"
    else:
        msg = f"{joint.replace('_', ' ').title()} hyperextension risk ({angle:.0f}° > {max_deg:.0f}°)"
    return "high", msg


def compute_injury_risk_score(
    errors: List[str],
    joint_risk_levels: Dict[str, str],
    weights: Optional[Dict[str, float]] = None,
) -> float:
    """
    Compute Injury Risk Score 0-100 (100 = highest risk).
    Based on detected errors and joint risk levels.
    """
    default_weights = {
        "knee_valgus": 25,
        "knee_angle_unsafe": 25,
        "unstable_landing": 20,
        "poor_hip_extension": 15,
        "ankle_instability": 15,
        "shoulder_imbalance": 10,
        "core_instability": 10,
        "limited_rotation": 8,
        "elbow_alignment": 5,
        "elbow_drop": 5,
    }
    w = weights or default_weights

    score = 0.0
    for err in errors:
        err_lower = err.lower().replace(" ", "_")
        for key, weight in w.items():
            if key in err_lower or err_lower in key:
                score += weight
                break
        else:
            score += 5  # Unknown error

    for joint, level in joint_risk_levels.items():
        if level == "high":
            score += 15
        elif level == "moderate":
            score += 5

    return min(100.0, score)


def get_coaching_for_error(error: str) -> Tuple[str, List[str]]:
    """Return (coaching_advice, possible_injuries) for an error."""
    err_lower = error.lower().replace(" ", "_")
    for key, (advice, injuries) in ERROR_COACHING_MAP.items():
        if key in err_lower or err_lower in key:
            return advice, injuries
    return (
        "Focus on correct form and gradual improvement. Practice slow, controlled movements.",
        [],
    )
