"""
Trusted sources and references for coaching advice.

All advice and evaluations are based on:
- Scientific research (biomechanics, sports science)
- Official sports federations (FIFA, ITF, FIBA, etc.)
- Recognized coaching academies and institutions
"""

from typing import Dict, List, Optional

# Source citations by category
SOURCES: Dict[str, List[Dict[str, str]]] = {
    "general_biomechanics": [
        {
            "name": "Biomechanics of Sport and Exercise",
            "author": "Peter M. McGinnis",
            "publisher": "Human Kinetics",
            "url": "https://us.humankinetics.com/",
            "note": "Standard reference for joint angles and movement analysis.",
        },
        {
            "name": "Sports Biomechanics",
            "author": "Roger Bartlett",
            "publisher": "Routledge",
            "note": "Scientific basis for performance evaluation.",
        },
    ],
    "football_soccer": [
        {
            "name": "FIFA Football Medicine Manual",
            "org": "FIFA",
            "url": "https://www.fifa.com/",
            "note": "Official guidelines for football technique and injury prevention.",
        },
        {
            "name": "Knee Valgus in Football",
            "source": "British Journal of Sports Medicine",
            "note": "Knee alignment research for striking and landing.",
        },
    ],
    "tennis": [
        {
            "name": "ITF Coaching Beginner to Advanced",
            "org": "International Tennis Federation",
            "url": "https://www.itftennis.com/",
            "note": "Official tennis stroke mechanics and progression.",
        },
        {
            "name": "USTA Player Development",
            "org": "United States Tennis Association",
            "note": "Serve, forehand, backhand biomechanics.",
        },
    ],
    "basketball": [
        {
            "name": "FIBA Coaching Manual",
            "org": "International Basketball Federation",
            "url": "https://www.fiba.basketball/",
            "note": "Shooting, passing, and defensive fundamentals.",
        },
        {
            "name": "Jump Landing Mechanics",
            "source": "Journal of Athletic Training",
            "note": "Safe landing patterns and knee protection.",
        },
    ],
    "volleyball": [
        {
            "name": "FIVB Coaching Guidelines",
            "org": "Federation Internationale de Volleyball",
            "url": "https://www.fivb.com/",
            "note": "Spiking, blocking, and serving technique.",
        },
    ],
    "weightlifting": [
        {
            "name": "IWF Technical Rules",
            "org": "International Weightlifting Federation",
            "url": "https://www.iwf.net/",
            "note": "Snatch and clean & jerk standards.",
        },
        {
            "name": "USA Weightlifting Coaching",
            "org": "USA Weightlifting",
            "note": "Barbell path and joint angles.",
        },
    ],
    "running_track": [
        {
            "name": "World Athletics Coaching",
            "org": "World Athletics (IAAF)",
            "url": "https://worldathletics.org/",
            "note": "Sprint mechanics and stride analysis.",
        },
    ],
    "boxing": [
        {
            "name": "AIBA Technical Rules",
            "org": "International Boxing Association",
            "note": "Punch mechanics and stance.",
        },
    ],
    "gymnastics": [
        {
            "name": "FIG Technical Regulations",
            "org": "Federation Internationale de Gymnastique",
            "url": "https://www.gymnastics.sport/",
            "note": "Landing mechanics and body alignment.",
        },
    ],
    "golf": [
        {
            "name": "PGA Teaching Manual",
            "org": "Professional Golfers' Association",
            "note": "Swing plane and rotation.",
        },
    ],
    "swimming": [
        {
            "name": "FINA Coaching Guidelines",
            "org": "Federation Internationale de Natation",
            "url": "https://www.fina.org/",
            "note": "Stroke mechanics and body position.",
        },
    ],
    "baseball": [
        {
            "name": "USA Baseball Coaching Development",
            "org": "USA Baseball",
            "url": "https://www.usabaseball.com/",
            "note": "Throwing mechanics and batting technique.",
        },
        {
            "name": "Little League Coaching Guide",
            "org": "Little League International",
            "note": "Fundamental throwing and hitting mechanics.",
        },
    ],
    "yoga": [
        {
            "name": "Yoga Alliance Standards",
            "org": "Yoga Alliance",
            "url": "https://www.yogaalliance.org/",
            "note": "Alignment and safety in yoga poses.",
        },
    ],
    "martial_arts": [
        {
            "name": "Martial Arts Biomechanics",
            "source": "Journal of Sports Sciences",
            "note": "Strike mechanics and power generation.",
        },
    ],
    "hockey": [
        {
            "name": "IIHF Development Program",
            "org": "International Ice Hockey Federation",
            "url": "https://www.iihf.com/",
            "note": "Skating and shooting technique.",
        },
    ],
}


# Error type -> official source for injury warnings & coaching advice
# Based on: FIFA Medicine, BJSM, JAT, NASM, ACSM, federation guidelines
ERROR_OFFICIAL_SOURCES: Dict[str, Dict[str, str]] = {
    "knee_valgus": {
        "name": "FIFA Football Medicine Manual / British Journal of Sports Medicine",
        "org": "FIFA / BJSM",
        "url": "https://www.fifa.com/",
        "note": "Knee alignment research for striking and landing.",
    },
    "knee_angle_unsafe": {
        "name": "Jump Landing Mechanics",
        "org": "Journal of Athletic Training (NATA)",
        "url": "https://www.nata.org/",
        "note": "Safe landing patterns and ACL risk.",
    },
    "poor_hip_extension": {
        "name": "Sports Biomechanics",
        "org": "Routledge / Human Kinetics",
        "note": "Hip drive and power generation.",
    },
    "ankle_instability": {
        "name": "ACSM Guidelines for Exercise Testing",
        "org": "American College of Sports Medicine",
        "url": "https://www.acsm.org/",
        "note": "Balance and ankle stability.",
    },
    "unstable_landing": {
        "name": "FIG Technical Regulations / NATA",
        "org": "Federation Internationale de Gymnastique",
        "note": "Landing mechanics and knee protection.",
    },
    "shoulder_imbalance": {
        "name": "NASM Corrective Exercise",
        "org": "National Academy of Sports Medicine",
        "url": "https://www.nasm.org/",
        "note": "Rotator cuff and shoulder symmetry.",
    },
    "limited_rotation": {
        "name": "ITF Coaching / Biomechanics of Sport",
        "org": "International Tennis Federation",
        "note": "Hip-shoulder separation and rotation.",
    },
    "elbow_alignment": {
        "name": "USTA Player Development / ITF",
        "org": "United States Tennis Association",
        "note": "Elbow positioning in strokes.",
    },
    "elbow_drop": {
        "name": "AIBA Technical Rules",
        "org": "International Boxing Association",
        "note": "Guard position and elbow mechanics.",
    },
    "core_instability": {
        "name": "ACSM Core Training Guidelines",
        "org": "American College of Sports Medicine",
        "note": "Core engagement and bracing.",
    },
    "unstable_posture": {
        "name": "Biomechanics of Sport and Exercise",
        "org": "Human Kinetics",
        "note": "Postural alignment.",
    },
}

# Default source for unknown errors
DEFAULT_ERROR_SOURCE = {
    "name": "Biomechanics of Sport and Exercise",
    "org": "Human Kinetics",
    "note": "General movement analysis.",
}


def get_source_for_error(error_key: str) -> Dict[str, str]:
    """Return official source reference for an error type."""
    key = (error_key or "").lower().strip().replace(" ", "_")
    for err_key, src in ERROR_OFFICIAL_SOURCES.items():
        if err_key in key or key in err_key:
            return dict(src)
    return dict(DEFAULT_ERROR_SOURCE)


def format_source_short(source: Optional[Dict[str, str]]) -> str:
    """Format source as short citation: 'Name (Org)'."""
    if not source:
        return ""
    name = source.get("name", "")
    org = source.get("org", "")
    if name and org:
        return f"{name} ({org})"
    return name or org or ""


def get_sources_for_sport(sport_id: str) -> List[Dict[str, str]]:
    """Return source references for a sport."""
    key = (sport_id or "unknown").lower().strip()
    sport_key = key.replace(" ", "_")
    # Map common IDs to source keys
    key_map = {
        "football": "football_soccer",
        "soccer": "football_soccer",
        "running": "running_track",
        "track": "running_track",
    }
    ref_key = key_map.get(sport_key, sport_key)
    out = list(SOURCES.get(ref_key, []))
    out.extend(SOURCES.get("general_biomechanics", []))
    return out


def format_sources_for_report(sport_id: str) -> str:
    """Format sources as citation text for reports."""
    srcs = get_sources_for_sport(sport_id)
    lines = []
    for s in srcs[:5]:  # Top 5
        name = s.get("name", "")
        org = s.get("org", s.get("author", ""))
        note = s.get("note", "")
        line = f"• {name}"
        if org:
            line += f" ({org})"
        if note:
            line += f" – {note}"
        lines.append(line)
    return "\n".join(lines) if lines else "Sources: General sports biomechanics and federation guidelines."
