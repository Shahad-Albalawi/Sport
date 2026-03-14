"""
Main analysis pipeline orchestration.

Orchestrates full flow: video input -> VideoProcessor (pose, movement, evaluation)
-> ReportExporter (CSV, PDF, JSON). Supports progress callbacks and live overlay streaming.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from backend.config import REPORTS_DIR, OUTPUT_DIR
from backend.sport_registry import get_sport_folder
from backend.sources import get_sources_for_sport
from backend.reports.exporters import ReportExporter
from backend.video.processor import VideoProcessor

logger = logging.getLogger("sport_analysis.pipeline")


class AnalysisPipeline:
    """Orchestrate full analysis: video -> reports (PDF focus)."""

    def __init__(
        self,
        reports_dir: Optional[Path] = None,
        on_progress: Optional[Callable[[int, int, str], None]] = None,
        on_frame: Optional[Callable[[int, int, str, float, str], None]] = None,
    ):
        self.reports_dir = reports_dir or REPORTS_DIR
        self.on_progress = on_progress
        self.on_frame = on_frame
        self._processor: Optional[VideoProcessor] = None

    def run_analysis(
        self,
        source: str,
        sport: str,
        export_csv: bool = True,
        export_pdf: bool = True,
        export_json: bool = True,
        skip_overlay: bool = False,
        on_progress: Optional[Callable[[int, int, str], None]] = None,
        on_frame: Optional[Callable[[int, int, str, float, str], None]] = None,
    ) -> Dict[str, Any]:
        """
        Run full pipeline: process video, generate reports.
        source: path to video file
        sport: user-selected sport (required)
        """
        sport = (sport or "unknown").lower().strip()
        proc_on_frame = on_frame or self.on_frame
        # Store reports under REPORTS_DIR/sport_folder/ so API can serve them
        sport_folder = get_sport_folder(sport)
        reports_dir = (self.reports_dir or REPORTS_DIR) / sport_folder
        reports_dir.mkdir(parents=True, exist_ok=True)

        self._processor = VideoProcessor(
            output_dir=OUTPUT_DIR,
            on_progress=on_progress or self.on_progress,
            on_frame=proc_on_frame,
        )

        try:
            summary = self._processor.process_video(source, sport=sport, skip_overlay=skip_overlay)
        except Exception as e:
            logger.exception("Pipeline failed: %s", e)
            raise

        exporter = ReportExporter(output_dir=reports_dir)
        base_name = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        report_files = {}
        # Relative path from REPORTS_DIR for API download (e.g. "Football/report_xxx.pdf")
        report_prefix = f"{sport_folder}/"

        # CSV
        if export_csv:
            frames_data = [
                {
                    "overall_score": e.get("overall_score", 0),
                    "movement": e.get("movement", ""),
                    "errors": "; ".join(e.get("errors", []) or []),
                }
                for e in summary.get("frame_evaluations", [])
            ]
            if not frames_data:
                frames_data = [{"overall_score": 0, "movement": "", "errors": ""}]
            csv_summary = {
                "sport": summary.get("sport_name_en", sport),
                "total_frames": summary.get("total_frames", 0),
                "overall_score": summary.get("overall_score", 0),
                "errors": summary.get("errors", []),
                "video_fps": summary.get("video_fps"),
                "processing_time_sec": summary.get("processing_time_sec"),
                "strengths": summary.get("strengths", []),
                "movements_analyzed": summary.get("movements_analyzed", []),
                "coaching_feedback": summary.get("coaching_feedback", []),
                "injury_risk_score": summary.get("injury_risk_score"),
                "injury_risk_warnings": summary.get("injury_risk_warnings", []),
                "possible_injuries": summary.get("possible_injuries", []),
            }
            report_files["csv"] = report_prefix + str(exporter.export_csv(
                frames_data, summary=csv_summary, filename=f"{base_name}.csv", sport=sport
            ).name)

        development_plan = summary.get("development_plan", [])

        # PDF (professional report: sport, movements, scores 0-10, errors, coaching feedback)
        if export_pdf:
            report_files["pdf"] = report_prefix + str(exporter.export_pdf(
                sport=summary.get("sport", sport),
                sport_name=summary.get("sport_name_en") or summary.get("sport_name", sport),
                movements_analyzed=summary.get("movements_analyzed", []),
                overall_score=summary.get("overall_score", 0),
                errors=summary.get("errors", []),
                coaching_feedback=summary.get("coaching_feedback", []),
                recommendations=summary.get("recommendations", []),
                development_plan=development_plan,
                joint_scores=summary.get("joint_scores"),
                strengths=summary.get("strengths", []),
                object_tracking=summary.get("object_tracking", []),
                injury_risk_warnings=summary.get("injury_risk_warnings", []),
                injury_risk_score=summary.get("injury_risk_score"),
                possible_injuries=summary.get("possible_injuries", []),
                injury_risk_with_corrections=summary.get("injury_risk_with_corrections", []),
                total_frames=summary.get("total_frames"),
                video_fps=summary.get("video_fps"),
                processing_time_sec=summary.get("processing_time_sec"),
                filename=f"{base_name}.pdf",
            ).name)

        if export_json:
            report_files["json"] = report_prefix + str(exporter.export_json(summary, filename=f"{base_name}.json").name)

        # Internal references (traceability) - always stored, separate from user-facing report
        from backend.config import EXPORT_DEV_SOURCES_FILE
        sources = get_sources_for_sport(sport)
        summary["internal_references"] = sources
        if EXPORT_DEV_SOURCES_FILE:
            import json
            from backend.utils import strip_arabic_fields, to_json_safe
            src_path = reports_dir / f"{base_name}_sources.json"
            with open(src_path, "w", encoding="utf-8") as f:
                json.dump(strip_arabic_fields(to_json_safe({"sport": sport, "sources": sources})), f, indent=2, ensure_ascii=False)
            report_files["sources"] = report_prefix + src_path.name

        summary["report_files"] = report_files
        summary.setdefault("output_filename", Path(summary.get("output_video_path", "")).name if summary.get("output_video_path") else None)
        return summary

    def stop_analysis(self):
        """Stop running analysis."""
        if self._processor:
            self._processor.stop()
