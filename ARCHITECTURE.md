# Sport Analysis Platform — Architecture

Professional multi-sport biomechanics analysis platform. Analyzes athlete movement from video using pose tracking and returns structured evaluations suitable for mobile/web integration.

## Overview

```
Video Input → Pose Estimation → Movement Recognition → Sport Profile → Evaluation → Reports
                  ↑                      ↑                   ↑
              MediaPipe              Movement IDs      Registry or Legacy
```

## Key Directories

| Path | Purpose |
|------|---------|
| `backend/sports/` | Sport modules, base classes, schema, registry |
| `backend/analysis/` | Evaluator, sport profiles (legacy + registry integration) |
| `backend/video/` | Processor, overlay, landmark smoothing |
| `backend/models/` | Pose estimator, movement recognizer, object tracker |
| `backend/reports/` | PDF, CSV, JSON exporters |
| `sports/{SportName}/` | Per-sport: videos, models, tests, reports |
| `reports/{SportFolder}/` | Pipeline output (PDF, CSV, JSON, _sources.json) |

## Flow

1. **VideoProcessor** reads frames, runs pose estimation (MediaPipe), movement recognition, object tracking.
2. **get_sport_profile** checks `backend.sports.registry` first; if no module, uses legacy `sport_profiles`.
3. **MovementEvaluator** scores joint angles, alignment, balance; derives injury-risk warnings from errors.
4. **RecommendationEngine** produces coaching feedback.
5. **ReportExporter** writes PDF, CSV, JSON; pipeline exports `_sources.json` for traceability when `EXPORT_DEV_SOURCES_FILE=True`.

## Sport Module Contract

Each sport module extends `SportAnalyzer` and provides:

- `get_movements()` — movement definitions (id, name, key joints)
- `get_key_joints()` — joints used for this sport
- `get_ideal_angles()` — ideal joint angles for movements
- `get_critical_errors()` — error IDs → descriptions
- `get_coaching_tips()` — error → improvement advice
- `get_sources()` — trusted references (federations, research)

## Unified Output Schema

All sports return `SportOutput` (and raw summary dict) with:

- `sport_id`, `sport_name`, `overall_score`, `total_frames`
- `movements`: per-movement score, strengths, errors, improvement advice
- `strengths`, `detected_errors`, `coaching_feedback`, `recommendations`
- `injury_risk_warnings` — derived from poor mechanics
- `report_files`, `output_video_path`

## Per-Sport Testing

```bash
python scripts/run_sport_test.py football
python scripts/run_sport_test.py tennis sports/Tennis/videos/serve_sample.mp4
python scripts/run_sport_test.py basketball --skip-overlay
```

- Uses first `.mp4` in `sports/{SportName}/videos/` if no video given.
- If no sample exists, creates synthetic test video.
- Reports written to `reports/{SportFolder}/`.

## Adding a New Sport

1. Create `backend/sports/{sport}/analyzer.py` extending `SportAnalyzer`.
2. Register in `backend/sports/registry.py` under `IMPLEMENTED_SPORT_MODULES`.
3. Add `SPORT_FOLDERS` entry in `backend/sport_registry.py`.
4. Add profile in `backend/analysis/sport_profiles.py` (fallback).
5. Add sources in `backend/sources.py`.

## Implemented vs Profile-Only Sports

| Type | Sports |
|------|--------|
| **Modular analyzers** | football, tennis, basketball, weightlifting, soccer (alias) |
| **Profile-only** (sport_profiles) | boxing, golf, baseball, volleyball, running, yoga, gymnastics, martial_arts, swimming, hockey, general_fitness |
