# Sport-Specific Structure

Each sport has its own independent folder with standardized subdirectories.

## Structure (per sport)

```
{SportName}/
├── videos/     Raw videos for analysis
├── models/     Sport-specific AI/ML models (optional overrides)
├── tests/      Test data, sample movements, exercises
└── reports/    Analysis results (PDF, CSV, JSON)
```

## Supported Sports

| Folder | Sport ID | Movements |
|--------|----------|-----------|
| Tennis | tennis | Serve, Forehand, Backhand, Volley |
| Basketball | basketball | Shooting, Dribbling, Layup, Rebound |
| Football | football | Ball Striking, Passing, Shooting, Sprinting |
| Soccer | soccer | Same as Football |
| Volleyball | volleyball | Spike, Block, Serve, Pass |
| Swimming | swimming | Stroke, Kick, Breathing |
| Gymnastics | gymnastics | Floor, Beam, Vault, Tumbling |
| Track | running/track | Sprint Start, Acceleration, Stride |
| Baseball | baseball | Throwing, Batting |
| Golf | golf | Full Swing, Chip, Putt |
| Weightlifting | weightlifting | Snatch, Clean & Jerk, Squat |
| Boxing | boxing | Punches, Defense, Footwork |
| Yoga | yoga | Poses, Balance, Alignment |
| Hockey | hockey | Skating, Shooting, Passing |
| Martial_Arts | martial_arts | Strikes, Kicks, Defense |

## Adding a New Sport

1. Create folder: `sports/{NewSport}/`
2. Add subdirs: `videos/`, `models/`, `tests/`, `reports/`
3. Register in `backend/sport_registry.py` → `SPORT_FOLDERS`
4. Add profile in `backend/analysis/sport_profiles.py`
5. Add sources in `backend/sources.py`

## Reports

Reports are saved to `reports/{SportFolder}/` (e.g. `reports/Football/`) and served by the API.
Each report includes:
- Video highlights of analyzed movements
- Numerical/textual assessment per skill
- Corrective guidance and improvement tips
- Injury-risk warnings when poor mechanics detected
- Internal references (stored in `*_sources.json` for traceability)

## Per-Sport Test Runner

Run analysis for a specific sport:

```bash
python scripts/run_sport_test.py SPORT [VIDEO_PATH]
```

- `SPORT`: football, tennis, basketball, weightlifting, soccer, etc.
- `VIDEO_PATH`: optional. If omitted, uses first video from `sports/{SportName}/videos/` or creates a synthetic test video.

Examples:
```bash
python scripts/run_sport_test.py football
python scripts/run_sport_test.py tennis sports/Tennis/videos/serve_sample.mp4
python scripts/run_sport_test.py basketball --skip-overlay
```

## Sample Videos

Place test videos in `sports/{SportName}/videos/` (e.g. `sports/Football/videos/kick.mp4`).
Supported formats: `.mp4`, `.avi`, `.mov`.
