# AI Sports Movement Analysis

**Professional AI-powered sports coach** that analyzes player movements from video (real-time or uploaded), scores performance (0–10), and generates detailed coaching feedback and reports.

---

## Overview
AI Sports Movement Analysis is a production-ready system that evaluates athletic performance using computer vision and biomechanical analysis.

It provides:
- Real-time movement tracking
- Per-movement scoring (0–10)
- Error detection & strengths analysis
- Actionable coaching recommendations
- Exportable performance reports

---

## Key Features

### AI & Analysis
- Pose estimation using MediaPipe (33 landmarks)
- Object tracking with YOLO (ball, racket, barbell, etc.)
- Sport auto-detection using movement + object inference
- Biomechanics-based evaluation (not user-level dependent)

### Performance Evaluation
- Score each movement (0–10)
- Detect errors (e.g., knee valgus, poor alignment)
- Identify strengths and mastered skills
- Generate personalized improvement plans

### Real-Time Processing
- Live skeleton & joint overlay
- Object interaction tracking
- Progress tracking (0–100%)
- Works with camera or uploaded videos

---

## Reports & Export
- PDF report with full analysis
- CSV / JSON export
- Video output with overlay
- Reports match real-time results exactly

---

## API (REST)

| Endpoint | Method | Description |
|----------|--------|------------|
| /api/upload | POST | Upload video |
| /start/video | POST | Start video analysis |
| /start/camera | POST | Start live analysis |
| /progress/{job_id} | GET | Track progress |
| /report/{job_id} | GET | Get report |
| /api/status/{job_id} | GET | Full results |

---

## System Architecture

- Modular backend design
- Clear separation:
  - Models (AI)
  - Video processing
  - Analysis engine
  - API layer
  - Reporting

Easily extensible to support new sports and movements.

---

## Quality & Reliability

- 140+ tests (full coverage)
- Strong error handling system
- Production-ready architecture
- Optimized performance (2–3× faster with fast mode)

---

## Performance Optimization

Enable fast processing mode:

```bash
FAST_PROCESSING=1 python main.py --serve
