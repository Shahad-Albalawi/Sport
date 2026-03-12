"""Export reports to CSV, PDF, and JSON."""

import csv
import json
import logging
from dataclasses import asdict
from datetime import datetime

from backend.utils import joint_score_to_dict, to_json_safe, strip_arabic_fields
from pathlib import Path
from typing import Any, Dict, List, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from backend.config import REPORTS_DIR

logger = logging.getLogger("sport_analysis.reports")


class ReportExporter:
    """Export analysis results to CSV, PDF, and JSON."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or REPORTS_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _serialize_obj(self, obj: Any) -> Any:
        """Convert objects to JSON-serializable form (numpy, dataclasses, bool)."""
        return to_json_safe(obj)

    def export_json(self, data: Dict[str, Any], filename: Optional[str] = None) -> Path:
        """Export to JSON file (English-only: strips name_ar and Arabic fields)."""
        fname = filename or f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        path = self.output_dir / fname
        clean = strip_arabic_fields(self._serialize_obj(data))
        with open(path, "w", encoding="utf-8") as f:
            json.dump(clean, f, indent=2, ensure_ascii=False)
        logger.info("Exported JSON: %s", path)
        return path

    def export_csv(
        self,
        frames_data: List[Dict],
        summary: Optional[Dict] = None,
        filename: Optional[str] = None,
    ) -> Path:
        """Export frame-by-frame and summary to CSV."""
        fname = filename or f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path = self.output_dir / fname
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if summary:
                writer.writerow(["Section", "Key", "Value"])
                for k, v in summary.items():
                    writer.writerow(["Summary", k, str(v)])
                writer.writerow([])
            if frames_data:
                headers = list(frames_data[0].keys()) if frames_data else []
                writer.writerow(["Frame"] + headers)
                for i, row in enumerate(frames_data):
                    vals = [row.get(h, "") for h in headers]
                    writer.writerow([i] + [str(v) for v in vals])
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
    ) -> Path:
        """
        Export professional PDF report.
        Sport, movements, scores, errors, strengths, object interaction, recommendations.
        """
        fname = filename or f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        path = self.output_dir / fname

        doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=inch, leftMargin=inch)
        styles = getSampleStyleSheet()
        story = []

        # Title
        story.append(Paragraph("<b>AI Sports Movement Analysis Report</b>", styles["Heading1"]))
        story.append(Spacer(1, 0.2 * inch))

        # Sport & Overall
        story.append(Paragraph(f"<b>Sport:</b> {sport_name} ({sport})", styles["Normal"]))
        story.append(Paragraph(f"<b>Overall Score:</b> {overall_score:.1f}/10", styles["Normal"]))
        story.append(Paragraph(f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["Normal"]))
        story.append(Spacer(1, 0.3 * inch))

        # Movements Analyzed (scores 0-10) - per-movement strengths, weaknesses, improvement
        story.append(Paragraph("<b>Per-Movement Analysis</b>", styles["Heading2"]))
        if movements_analyzed:
            for m in movements_analyzed:
                name = m.get("name_en", m.get("name", m.get("id", "-")))
                score = m.get("score", 0)
                frames = m.get("frames_count", 0)
                fb = m.get("feedback", "")
                strengths = m.get("strengths", [])
                weaknesses = m.get("weaknesses", [])
                imp = m.get("improvement_note", "")
                story.append(Paragraph(f"<b>{name}</b> – Score: {score:.1f}/10 (frames: {frames})", styles["Normal"]))
                story.append(Paragraph(f"Feedback: {fb}", styles["Normal"]))
                if strengths:
                    story.append(Paragraph("Strengths: " + "; ".join(strengths), styles["Normal"]))
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
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), (0.7, 0.7, 0.7)),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, (0.5, 0.5, 0.5)),
            ]))
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

        doc.build(story)
        logger.info("Exported PDF: %s", path)
        return path
