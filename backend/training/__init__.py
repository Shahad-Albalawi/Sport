"""
Sport-specific training, testing, and continuous improvement.

Each sport module is trained and tested independently on real-world videos.
- Data collection: features, scores, errors per frame/movement
- Improvement engine: adjust safe ranges, injury risk weights, coaching advice
- Reports: per-sport training reports with updates
"""

from backend.training.data_store import TrainingDataStore, load_sport_training_data
from backend.training.batch_processor import SportBatchProcessor
from backend.training.improvement import ImprovementEngine
from backend.training.report import TrainingReportExporter

__all__ = [
    "TrainingDataStore",
    "load_sport_training_data",
    "SportBatchProcessor",
    "ImprovementEngine",
    "TrainingReportExporter",
]
