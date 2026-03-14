"""
Sport-specific directory registry and path helpers.

Maps internal sport IDs to professional folder structure:
  sports/{SportName}/
    videos/   - raw videos for analysis
    models/   - sport-specific AI/ML models (optional overrides)
    tests/    - test data, sample movements, exercises
    reports/  - analysis results (PDF, CSV, JSON)
"""

from pathlib import Path
from typing import Dict, List, Optional

from backend.config import BASE_DIR, SPORTS_ROOT

# Internal sport ID -> folder name (PascalCase for professional appearance)
SPORT_FOLDERS: Dict[str, str] = {
    "tennis": "Tennis",
    "basketball": "Basketball",
    "football": "Football",
    "soccer": "Soccer",
    "volleyball": "Volleyball",
    "swimming": "Swimming",
    "gymnastics": "Gymnastics",
    "running": "Track",
    "track": "Track",
    "baseball": "Baseball",
    "golf": "Golf",
    "weightlifting": "Weightlifting",
    "boxing": "Boxing",
    "yoga": "Yoga",
    "hockey": "Hockey",
    "martial_arts": "Martial_Arts",
    "general_fitness": "General_Fitness",
    "unknown": "Unknown",
}


def get_sport_folder(sport_id: str) -> str:
    """Get folder name for sport. Returns PascalCase folder name."""
    key = (sport_id or "unknown").lower().strip()
    return SPORT_FOLDERS.get(key, key.replace("_", " ").title().replace(" ", "_"))


def get_sport_dir(sport_id: str) -> Path:
    """Get root directory for a sport. Creates structure if missing."""
    folder = get_sport_folder(sport_id)
    path = SPORTS_ROOT / folder
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_sport_videos_dir(sport_id: str) -> Path:
    """Get videos directory for a sport."""
    path = get_sport_dir(sport_id) / "videos"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_sport_models_dir(sport_id: str) -> Path:
    """Get models directory for a sport."""
    path = get_sport_dir(sport_id) / "models"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_sport_tests_dir(sport_id: str) -> Path:
    """Get tests directory for a sport (sample movements, exercises)."""
    path = get_sport_dir(sport_id) / "tests"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_sport_reports_dir(sport_id: str) -> Path:
    """Get reports directory for a sport."""
    path = get_sport_dir(sport_id) / "reports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def list_sports() -> List[str]:
    """List all configured sport IDs."""
    return list(SPORT_FOLDERS.keys())


def ensure_sport_structure(sport_id: str) -> Dict[str, Path]:
    """Ensure full structure exists. Returns dict of subdir paths."""
    root = get_sport_dir(sport_id)
    subdirs = ["videos", "models", "tests", "reports"]
    paths = {}
    for sub in subdirs:
        p = root / sub
        p.mkdir(parents=True, exist_ok=True)
        paths[sub] = p
    return paths
