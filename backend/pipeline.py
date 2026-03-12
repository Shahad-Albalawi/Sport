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
from backend.utils import joint_score_to_dict
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

        exporter = ReportExporter(output_dir=self.reports_dir)
        base_name = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        report_files = {}

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
                "errors": "; ".join(summary.get("errors", [])),
            }
            report_files["csv"] = str(exporter.export_csv(
                frames_data, summary=csv_summary, filename=f"{base_name}.csv"
            ).name)

        development_plan = summary.get("development_plan", [])

        # PDF (professional report: sport, movements, scores 0-10, errors, coaching feedback)
        if export_pdf:
            report_files["pdf"] = str(exporter.export_pdf(
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
                filename=f"{base_name}.pdf",
            ).name)

        if export_json:
            report_files["json"] = str(exporter.export_json(summary, filename=f"{base_name}.json").name)

        summary["report_files"] = report_files
        summary.setdefault("output_filename", Path(summary.get("output_video_path", "")).name if summary.get("output_video_path") else None)
        return summary

    def stop_analysis(self):
        """Stop running analysis."""
        if self._processor:
            self._processor.stop()
