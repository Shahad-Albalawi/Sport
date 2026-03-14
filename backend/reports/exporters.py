"""Export reports to CSV, PDF, and JSON."""

import csv
import json
import logging
from dataclasses import asdict
from datetime import datetime

from backend.utils import joint_score_to_dict, to_json_safe, strip_arabic_fields
from pathlib import Path
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from backend.config import REPORTS_DIR, INCLUDE_REFERENCES_IN_USER_REPORTS
from backend.sources import get_sources_for_sport

logger = logging.getLogger("sport_analysis.reports")


class ReportExporter:
    """Export analysis results to CSV, PDF, and JSON."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = Path(output_dir) if output_dir else REPORTS_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _serialize_obj(self, obj: Any) -> Any:
        """Convert objects to JSON-serializable form (numpy, dataclasses, bool)."""
        return to_json_safe(obj)

    def export_json(self, data: Dict[str, Any], filename: Optional[str] = None) -> Path:
        """Export structured JSON report (English-only: strips name_ar). Consumer-friendly layout."""
        fname = filename or f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        path = self.output_dir / fname
        raw = strip_arabic_fields(self._serialize_obj(data))
        # Build structured report for API consumers
        structured: Dict[str, Any] = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "report_version": "1.0",
                "sport": raw.get("sport", ""),
                "sport_name": raw.get("sport_name_en") or raw.get("sport_name", ""),
            },
            "summary": {
                "overall_score": raw.get("overall_score"),
                "overall_score_100": raw.get("overall_score_100"),
                "total_frames": raw.get("total_frames"),
                "video_fps": raw.get("video_fps"),
                "video_width": raw.get("video_width"),
                "video_height": raw.get("video_height"),
                "processing_time_sec": raw.get("processing_time_sec"),
            },
            "movements": raw.get("movements_analyzed", []),
            "feedback": {
                "strengths": raw.get("strengths", []),
                "errors": raw.get("errors", []),
                "coaching_feedback": raw.get("coaching_feedback", []),
                "recommendations": raw.get("recommendations", []),
                "development_plan": raw.get("development_plan", []),
            },
            "injury_risk": {
                "score": raw.get("injury_risk_score"),
                "warnings": raw.get("injury_risk_warnings", []),
                "possible_injuries": raw.get("possible_injuries", []),
            },
        }
        # Add frame_evaluations if present (for detailed analysis)
        if raw.get("frame_evaluations"):
            structured["frames"] = raw["frame_evaluations"]
        # Add object_tracking summary (unique labels)
        if raw.get("object_tracking"):
            obj_labels = list(dict.fromkeys(
                o.get("label", "") for o in raw["object_tracking"][:50] if o.get("label")
            ))
            structured["object_interaction"] = {"detected_labels": obj_labels}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(structured, f, indent=2, ensure_ascii=False)
        logger.info("Exported JSON: %s", path)
        return path

    def export_csv(
        self,
        frames_data: List[Dict],
        summary: Optional[Dict] = None,
        filename: Optional[str] = None,
        sport: Optional[str] = None,
    ) -> Path:
        """Export structured CSV: metadata, movements, strengths, errors, feedback, frame data, sources."""
        fname = filename or f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path = self.output_dir / fname
        summary = summary or {}
        sport_key = sport or summary.get("sport", "unknown")

        def _w(writer: csv.writer, *rows):
            for r in rows:
                writer.writerow(r if isinstance(r[0], (list, tuple)) else [r])

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # 1. Report metadata
            writer.writerow(["=== AI Sports Movement Analysis Report ==="])
            writer.writerow(["Generated", datetime.now().strftime("%Y-%m-%d %H:%M")])
            writer.writerow(["Sport", summary.get("sport", sport_key)])
            writer.writerow(["Total Frames", summary.get("total_frames", 0)])
            writer.writerow(["Overall Score (0-10)", summary.get("overall_score", 0)])
            if summary.get("video_fps"):
                writer.writerow(["Video FPS", summary["video_fps"]])
            if summary.get("processing_time_sec") is not None:
                writer.writerow(["Processing Time (sec)", f"{summary['processing_time_sec']:.1f}"])
            writer.writerow([])

            # 2. Movements summary
            movements = summary.get("movements_analyzed", [])
            if movements:
                writer.writerow(["--- Movements Summary ---"])
                writer.writerow(["Movement", "Score (0-10)", "Frames", "Feedback"])
                for m in movements:
                    name = m.get("name_en", m.get("name", m.get("id", "-")))
                    writer.writerow([name, f"{m.get('score', 0):.1f}", m.get("frames_count", 0), m.get("feedback", "")])
                writer.writerow([])

            # 3. Strengths
            strengths = summary.get("strengths", [])
            if strengths:
                writer.writerow(["--- Points of Strength ---"])
                for s in strengths:
                    writer.writerow([s])
                writer.writerow([])

            # 4. Errors
            errors = summary.get("errors", [])
            if isinstance(errors, str):
                errors = [e.strip() for e in errors.split(";")] if errors else []
            if errors:
                writer.writerow(["--- Detected Errors ---"])
                for e in errors:
                    writer.writerow([e])
                writer.writerow([])

            # 5. Injury risk
            if summary.get("injury_risk_score") is not None or summary.get("injury_risk_warnings") or summary.get("possible_injuries"):
                writer.writerow(["--- Injury Risk ---"])
                if summary.get("injury_risk_score") is not None:
                    writer.writerow(["Injury Risk Score (0-100)", f"{summary['injury_risk_score']:.0f}"])
                for w in summary.get("injury_risk_warnings", []):
                    writer.writerow(["Warning", w])
                for inj in summary.get("possible_injuries", []):
                    writer.writerow(["Possible Injury", inj])
                writer.writerow([])

            # 6. Coaching feedback
            coaching = summary.get("coaching_feedback", [])
            if coaching:
                writer.writerow(["--- Coaching Feedback ---"])
                writer.writerow(["Error", "Feedback"])
                for cf in coaching:
                    writer.writerow([cf.get("error", ""), cf.get("feedback", "")])
                writer.writerow([])

            # 7. Frame-by-frame
            if frames_data:
                writer.writerow(["--- Frame-by-Frame Analysis ---"])
                headers = list(frames_data[0].keys()) if frames_data else []
                writer.writerow(["Frame"] + headers)
                for i, row in enumerate(frames_data):
                    vals = [row.get(h, "") for h in headers]
                    writer.writerow([i] + [str(v) for v in vals])
                writer.writerow([])

            # 8. References (when enabled)
            if INCLUDE_REFERENCES_IN_USER_REPORTS:
                writer.writerow(["--- References & Sources ---"])
                writer.writerow(["Note", "All evaluations are based on scientific research and official federations.", ""])
                srcs = get_sources_for_sport(sport_key)
                for i, s in enumerate(srcs[:8], 1):
                    name = s.get("name", "")
                    org = s.get("org", s.get("author", s.get("publisher", "")))
                    note = s.get("note", "")
                    line = f"{name}" + (f" ({org})" if org else "") + (f" – {note}" if note else "")
                    writer.writerow([f"Source {i}", line, ""])

        logger.info("Exported CSV: %s", path)
        return path

    def export_pdf(
        self,
        sport: str,
        sport_name: str,
        movements_analyzed: List[Dict],
        overall_score: float,
        errors: List[str],
        coaching_feedback: List[Dict],
        recommendations: List[Dict],
        development_plan: Optional[List[str]] = None,
        filename: Optional[str] = None,
        joint_scores: Optional[List[Dict]] = None,
        strengths: Optional[List[str]] = None,
        object_tracking: Optional[List[Dict]] = None,
        injury_risk_warnings: Optional[List[str]] = None,
        injury_risk_score: Optional[float] = None,
        possible_injuries: Optional[List[str]] = None,
        injury_risk_with_corrections: Optional[List[Dict]] = None,
        total_frames: Optional[int] = None,
        video_fps: Optional[float] = None,
        processing_time_sec: Optional[float] = None,
    ) -> Path:
        """
        Export professional PDF report with executive summary and structured layout.
        """
        fname = filename or f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        path = self.output_dir / fname

        doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=0.75*inch, leftMargin=0.75*inch)
        styles = getSampleStyleSheet()
        # Custom styles for professional look
        styles.add(ParagraphStyle(name="ReportTitle", fontSize=18, spaceAfter=6, textColor=colors.HexColor("#1a5f2a")))
        styles.add(ParagraphStyle(name="SectionHeader", fontSize=12, spaceBefore=12, spaceAfter=6, textColor=colors.HexColor("#2d3748")))
        styles.add(ParagraphStyle(name="SummaryBox", backColor=colors.HexColor("#f0f9f4"), borderPadding=8, spaceAfter=10))
        story = []

        # === Report Header ===
        story.append(Paragraph("<b>AI Sports Movement Analysis Report</b>", styles["ReportTitle"]))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d at %H:%M')}", styles["Normal"]))
        story.append(Spacer(1, 0.25 * inch))

        # === Executive Summary ===
        score_color = "#16a34a" if overall_score >= 7 else "#ca8a04" if overall_score >= 5 else "#dc2626"
        total_frames_val = total_frames or 0
        duration_sec = (total_frames_val / (video_fps or 30)) if video_fps else 0
        summary_text = (
            f"<b>Sport:</b> {sport_name} | "
            f"<b>Overall Score:</b> <font color='{score_color}'>{overall_score:.1f}/10</font> | "
            f"<b>Frames analyzed:</b> {total_frames_val} | "
        )
        if processing_time_sec:
            summary_text += f"<b>Analysis time:</b> {processing_time_sec:.1f}s | "
        if duration_sec > 0:
            summary_text += f"<b>Video duration:</b> ~{duration_sec:.1f}s"
        story.append(Paragraph(summary_text, styles["Normal"]))
        story.append(Spacer(1, 0.2 * inch))

        # Movements Analyzed (scores 0-10) - per-movement strengths, weaknesses, improvement
        story.append(Paragraph("<b>Per-Movement Analysis</b>", styles["Heading2"]))
        if movements_analyzed:
            for m in movements_analyzed:
                name = m.get("name_en", m.get("name", m.get("id", "-")))
                score = m.get("score", 0)
                frames = m.get("frames_count", 0)
                fb = m.get("feedback", "")
                mov_strengths = m.get("strengths", [])
                weaknesses = m.get("weaknesses", [])
                imp = m.get("improvement_note", "")
                story.append(Paragraph(f"<b>{name}</b> – Score: {score:.1f}/10 (frames: {frames})", styles["Normal"]))
                story.append(Paragraph(f"Feedback: {fb}", styles["Normal"]))
                if mov_strengths:
                    story.append(Paragraph("Strengths: " + "; ".join(mov_strengths), styles["Normal"]))
                if weaknesses:
                    story.append(Paragraph("Areas to improve: " + "; ".join(weaknesses), styles["Normal"]))
                if imp:
                    story.append(Paragraph(f"Recommendation: {imp}", styles["Normal"]))
                story.append(Spacer(1, 0.15 * inch))
        # Compact table for quick reference
        if movements_analyzed:
            table_data = [["Movement", "Score (0-10)", "Frames"]]
            for m in movements_analyzed:
                name = m.get("name_en", m.get("name", m.get("id", "-")))
                score = m.get("score", 0)
                frames = m.get("frames_count", 0)
                table_data.append([name, f"{score:.1f}", str(frames)])
            t = Table(table_data, colWidths=[3*inch, 1.2*inch, 0.8*inch])
            tbl_styles = [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d3748")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, (0.8, 0.8, 0.8)),
            ]
            for r in range(1, len(table_data)):
                if r % 2 == 0:
                    tbl_styles.append(("BACKGROUND", (0, r), (-1, r), colors.HexColor("#f8fafc")))
            t.setStyle(TableStyle(tbl_styles))
            story.append(t)
        else:
            story.append(Paragraph("No movements detected in video.", styles["Normal"]))
        story.append(Spacer(1, 0.3 * inch))

        # Points of Strength
        strengths = strengths or []
        if strengths:
            story.append(Paragraph("<b>Points of Strength</b>", styles["Heading2"]))
            for s in strengths:
                story.append(Paragraph(f"✓ {s}", styles["Normal"]))
            story.append(Spacer(1, 0.2 * inch))

        # Injury Risk (single consolidated section)
        injury_risk_warnings = injury_risk_warnings or []
        possible_injuries = possible_injuries or []
        if injury_risk_score is not None or injury_risk_warnings or possible_injuries:
            story.append(Paragraph("<b>Injury Risk & Biomechanics</b>", styles["Heading2"]))
            if injury_risk_score is not None:
                risk_pct = min(100, max(0, injury_risk_score))
                risk_label = "High" if risk_pct >= 50 else "Moderate" if risk_pct >= 25 else "Low"
                story.append(Paragraph(f"Injury Risk Score: {risk_pct:.0f}/100 ({risk_label})", styles["Normal"]))
                story.append(Spacer(1, 0.1 * inch))
            injury_with_corrections = injury_risk_with_corrections or []
            if injury_with_corrections:
                story.append(Paragraph("Poor mechanics detected — explanation and how to correct:", styles["Normal"]))
                for item in injury_with_corrections:
                    w = item.get("warning", "")
                    c = item.get("correction", "")
                    story.append(Paragraph(f"⚠ <b>{w}</b>", styles["Normal"]))
                    if c:
                        story.append(Paragraph(f"   → Correction: {c}", styles["Normal"]))
                story.append(Spacer(1, 0.08 * inch))
            elif injury_risk_warnings:
                story.append(Paragraph("Poor mechanics detected — address these to reduce injury risk:", styles["Normal"]))
                for w in injury_risk_warnings:
                    story.append(Paragraph(f"⚠ {w}", styles["Normal"]))
                story.append(Spacer(1, 0.08 * inch))
            if possible_injuries:
                story.append(Paragraph("Possible injuries to address (if form not improved):", styles["Normal"]))
                for inj in possible_injuries[:8]:
                    story.append(Paragraph(f"• {inj}", styles["Normal"]))
            story.append(Spacer(1, 0.2 * inch))

        # Detected Errors
        story.append(Paragraph("<b>Detected Errors</b>", styles["Heading2"]))
        if errors:
            for e in errors:
                story.append(Paragraph(f"• {e}", styles["Normal"]))
        else:
            story.append(Paragraph("None detected.", styles["Normal"]))
        story.append(Spacer(1, 0.2 * inch))

        # Object Interaction Summary
        object_tracking = object_tracking or []
        if object_tracking:
            obj_labels = list(dict.fromkeys(o.get("label", "") for o in object_tracking[:20] if o.get("label")))
            if obj_labels:
                story.append(Paragraph("<b>Object Interaction Summary</b>", styles["Heading2"]))
                story.append(Paragraph(f"Detected: {', '.join(obj_labels)}", styles["Normal"]))
                story.append(Spacer(1, 0.2 * inch))

        # Coaching Feedback (per error)
        if coaching_feedback:
            story.append(Paragraph("<b>Coaching Feedback & Improvement Tips</b>", styles["Heading2"]))
            for cf in coaching_feedback:
                err = cf.get("error", "")
                fb = cf.get("feedback", "")
                story.append(Paragraph(f"<b>{err}</b>", styles["Normal"]))
                story.append(Paragraph(f"→ {fb}", styles["Normal"]))
                story.append(Spacer(1, 0.08 * inch))
            story.append(Spacer(1, 0.2 * inch))

        # Recommendations
        story.append(Paragraph("<b>Recommended Exercises</b>", styles["Heading2"]))
        if recommendations:
            for rec in recommendations:
                rec_d = rec if isinstance(rec, dict) else (asdict(rec) if hasattr(rec, "__dataclass_fields__") else {})
                name = rec_d.get("name", "")
                desc = rec_d.get("description", "")
                target = rec_d.get("target_joint", "")
                reps = rec_d.get("reps_sets", "")
                story.append(Paragraph(f"<b>{name}</b>", styles["Normal"]))
                story.append(Paragraph(desc, styles["Normal"]))
                story.append(Paragraph(f"Target: {target} | {reps}", styles["Normal"]))
                story.append(Spacer(1, 0.05 * inch))
        else:
            story.append(Paragraph("No recommendations.", styles["Normal"]))
        story.append(Spacer(1, 0.2 * inch))

        # Development Plan
        if development_plan:
            story.append(Paragraph("<b>Development Plan</b>", styles["Heading2"]))
            for item in development_plan:
                story.append(Paragraph(f"• {item}", styles["Normal"]))
            story.append(Spacer(1, 0.2 * inch))

        # References & Sources (only when config enables for user-facing reports)
        if INCLUDE_REFERENCES_IN_USER_REPORTS:
            srcs = get_sources_for_sport(sport)
            story.append(Paragraph("<b>References & Sources</b>", styles["Heading2"]))
            story.append(Paragraph(
                "All evaluations, advice, and corrective guidance are based on scientific research, "
                "official sports federations (FIFA, ITF, FIBA, etc.), and recognized coaching institutions.",
                styles["Normal"],
            ))
            for s in (srcs or [])[:8]:
                name = s.get("name", "")
                org = s.get("org", s.get("author", s.get("publisher", "")))
                note = s.get("note", "")
                line = f"• {name}"
                if org:
                    line += f" ({org})"
                if note:
                    line += f" – {note}"
                story.append(Paragraph(line, styles["Normal"]))
            story.append(Spacer(1, 0.1 * inch))

        doc.build(story)
        logger.info("Exported PDF: %s", path)
        return path
