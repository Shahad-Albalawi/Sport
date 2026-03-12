"""Sport inference from pose + movement + object detection.

Combines movement type and detected objects to infer the sport.
Uses priority: (movement+object) > object_only > movement_only.
"""

import logging
from typing import List, Tuple

logger = logging.getLogger("sport_analysis.inferencer")

# (movement, object) -> (sport, confidence)
MOVEMENT_OBJECT_TO_SPORT = {
    ("kick", "ball"): ("football", 0.9),
    ("kick", "sports_ball"): ("football", 0.9),
    ("sprint", "ball"): ("football", 0.75),
    ("sprint", "sports_ball"): ("football", 0.75),
    ("swing", "racket"): ("tennis", 0.9),
    ("swing", "tennis_racket"): ("tennis", 0.9),
    ("swing", "ball"): ("golf", 0.8),
    ("swing", "sports_ball"): ("golf", 0.8),
    ("swing",): ("tennis", 0.55),
    ("throw", "ball"): ("baseball", 0.75),
    ("throw", "sports_ball"): ("basketball", 0.7),
    ("throw", "bat"): ("baseball", 0.9),
    ("throw", "baseball_bat"): ("baseball", 0.9),
    ("throw",): ("baseball", 0.6),
    ("punch",): ("boxing", 0.85),
    ("squat", "barbell"): ("weightlifting", 0.9),
    ("squat",): ("weightlifting", 0.7),
    ("rotation", "stick"): ("hockey", 0.85),
    ("lunge",): ("running", 0.65),
    ("jump", "ball"): ("volleyball", 0.7),
    ("jump", "sports_ball"): ("basketball", 0.7),
    ("jump",): ("basketball", 0.6),
    ("rotation", "racket"): ("tennis", 0.85),
    ("rotation", "tennis_racket"): ("tennis", 0.85),
    ("rotation",): ("tennis", 0.5),
}

# Movement-only fallbacks (sport, confidence)
MOVEMENT_TO_SPORT = {
    "kick": ("football", 0.75),
    "sprint": ("running", 0.7),
    "swing": ("tennis", 0.6),
    "throw": ("baseball", 0.65),
    "punch": ("boxing", 0.8),
    "squat": ("weightlifting", 0.7),
    "lunge": ("running", 0.6),
    "jump": ("basketball", 0.6),
    "rotation": ("tennis", 0.5),
}

# Object-only hints when no clear movement
OBJECT_TO_SPORT = {
    "ball": "football",
    "sports_ball": "football",
    "racket": "tennis",
    "tennis_racket": "tennis",
    "bat": "baseball",
    "baseball_bat": "baseball",
}

OBJECT_ALIASES = {
    "sports_ball": "ball",
    "orange_basketball": "ball",
    "yellow_tennis": "ball",
    "white_ball": "ball",
    "green_ball": "ball",
    "tennis_racket": "racket",
    "baseball_bat": "bat",
    "barbell": "barbell",
    "stick": "stick",
}


def _normalize_object(label: str) -> str:
    lbl = label.lower().replace(" ", "_")
    return OBJECT_ALIASES.get(lbl, lbl)


def infer_sport(movement: str, objects: List[str]) -> Tuple[str, float]:
    """
    Infer sport from movement + detected objects.
    Priority: (movement+object) > movement_only > object_only.
    Returns (sport_name, confidence).
    """
    objs = list({_normalize_object(o) for o in (objects or [])})
    movement = (movement or "").lower()
    if movement == "unknown":
        movement = ""

    best_sport = "unknown"
    best_conf = 0.0

    # 1. Try (movement, object) pairs - highest confidence
    for obj in objs:
        key = (movement, obj)
        if key in MOVEMENT_OBJECT_TO_SPORT:
            sport, conf = MOVEMENT_OBJECT_TO_SPORT[key]
            if conf > best_conf:
                best_sport = sport
                best_conf = conf

    # 2. Try (movement,) with no object
    if movement:
        key = (movement,)
        if key in MOVEMENT_OBJECT_TO_SPORT:
            sport, conf = MOVEMENT_OBJECT_TO_SPORT[key]
            if conf > best_conf:
                best_sport = sport
                best_conf = conf

    # 3. Movement-only fallback
    if movement and movement in MOVEMENT_TO_SPORT:
        sport, conf = MOVEMENT_TO_SPORT[movement]
        if conf > best_conf:
            best_sport = sport
            best_conf = conf

    # 4. Object-only hint when movement unclear
    if best_conf < 0.5 and objs:
        for obj in objs:
            if obj in OBJECT_TO_SPORT:
                sport = OBJECT_TO_SPORT[obj]
                conf = 0.45
                if conf > best_conf:
                    best_sport = sport
                    best_conf = conf
                break

    return best_sport, best_conf
