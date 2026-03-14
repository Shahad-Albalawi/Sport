"""
Training and improvement reports per sport module.

Exports PDF, CSV, JSON with:
- Movement Score per movement
- Injury Risk Score per movement
- Detected biomechanical issues
- Applied Coaching Advice
- Updates to Safe Ranges or Injury Risk weights
"""

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.config import REPORTS_DIR
from backend.sport_registry import get_sport_folder
from backend.training.data_store import load_sport_training_data

logger = logging.getLogger("sport_analysis.training")


class TrainingReportExporter:
    """Export per-sport training and improvement reports."""

    def __init__(self, sport_id: str, output_dir: Optional[Path] = None):
        self.sport_id = (sport_id or "unknown").lower().strip()
        folder = get_sport_folder(self.sport_id)
        self.output_dir = Path(output_dir) if output_dir else REPORTS_DIR / "training" / folder
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_all(
        self,
        batch_summary: Optional[Dict[str, Any]] = None,
        improvements: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """Export PDF, CSV, JSON. Returns paths."""
        data = load_sport_training_data(self.sport_id)
        if batch_summary:
            data["last_batch"] = batch_summary
        if improvements:
            data["last_improvements"] = improvements

        base = f"training_report_{self.sport_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        paths = {}
        paths["json"] = str(self.export_json(data, f"{base}.json"))
        paths["csv"] = str(self.export_csv(data, f"{base}.csv"))
        paths["pdf"] = str(self.export_pdf(data, f"{base}.pdf"))
        return paths

    def export_json(self, data: Dict[str, Any], filename: Optional[str] = None) -> Path:
        path = self.output_dir / (filename or f"training_{self.sport_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info("Exported training JSON: %s", path)
        return path

    def export_csv(self, data: Dict[str, Any], filename: Optional[str] = None) -> Path:
        path = self.output_dir / (filename or f"training_{self.sport_id}.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Section", "Key", "Value"])
            w.writerow(["Sport", "id", self.sport_id])
            w.writerow(["Videos Processed", "", str(data.get("videos_processed", 0))])
            w.writerow(["Updated At", "", str(data.get("updated_at", ""))])
            w.writerow([])

            movements = data.get("movements", {})
            w.writerow(["Movement", "Avg Score", "Avg Injury Risk", "Frames", "Error Count"])
            for mov_id, m in movements.items():
                scores = m.get("scores", [])
                risks = m.get("injury_risks", [])
                w.writerow([
                    mov_id,
                    f"{sum(scores) / len(scores):.2f}" if scores else "",
                    f"{sum(risks) / len(risks):.1f}" if risks else "",
                    str(m.get("frames", 0)),
                    str(len(m.get("errors", []))),
                ])
            w.writerow([])

            w.writerow(["Error", "Count"])
            for err, cnt in data.get("error_counts", {}).items():
                w.writerow([err, str(cnt)])
            w.writerow([])

            overrides = data.get("safe_ranges_overrides", {})
            w.writerow(["Safe Range Override", "Min", "Max"])
            for key, v in overrides.items():
                w.writerow([key, str(v.get("min", "")), str(v.get("max", ""))])

        logger.info("Exported training CSV: %s", path)
        return path

    def export_pdf(self, data: Dict[str, Any], filename: Optional[str] = None) -> Path:
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import inch
            from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        except ImportError:
            logger.warning("reportlab not installed - skipping PDF export")
            return self.output_dir / (filename or "report.pdf")

        path = self.output_dir / (filename or f"training_{self.sport_id}.pdf")
        doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=inch, leftMargin=inch)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph(
            f"<b>Sport Module Training Report: {self.sport_id.title()}</b>",
            styles["Heading1"],
        ))
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(f"<b>Sport:</b> {self.sport_id}", styles["Normal"]))
        story.append(Paragraph(f"<b>Videos Processed:</b> {data.get('videos_processed', 0)}", styles["Normal"]))
        story.append(Paragraph(f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["Normal"]))
        story.append(Spacer(1, 0.3 * inch))

        story.append(Paragraph("<b>Movement Analysis</b>", styles["Heading2"]))
        movements = data.get("movements", {})
        if movements:
            table_data = [["Movement", "Avg Score (0-10)", "Injury Risk", "Frames"]]
            for mov_id, m in movements.items():
                scores = m.get("scores", [])
                risks = m.get("injury_risks", [])
                table_data.append([
                    mov_id,
                    f"{sum(scores) / len(scores):.1f}" if scores else "-",
                    f"{sum(risks) / len(risks):.0f}" if risks else "-",
                    str(m.get("frames", 0)),
                ])
            t = Table(table_data, colWidths=[2*inch, 1.5*inch, 1.2*inch, 0.8*inch])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), (0.7, 0.7, 0.7)),
                ("GRID", (0, 0), (-1, -1), 0.5, (0.5, 0.5, 0.5)),
            ]))
            story.append(t)
        else:
            story.append(Paragraph("No movement data yet.", styles["Normal"]))
        story.append(Spacer(1, 0.3 * inch))

        story.append(Paragraph("<b>Detected Biomechanical Issues (Error Counts)</b>", styles["Heading2"]))
        for err, cnt in sorted(data.get("error_counts", {}).items(), key=lambda x: -x[1]):
            story.append(Paragraph(f"• {err}: {cnt}", styles["Normal"]))
        story.append(Spacer(1, 0.2 * inch))

        imp = data.get("last_improvements", {})
        if imp:
            story.append(Paragraph("<b>Applied Improvements</b>", styles["Heading2"]))
            for u in imp.get("safe_ranges_updated", []):
                story.append(Paragraph(
                    f"Safe range: {u.get('movement')}/{u.get('joint')} → ({u.get('min'):.0f}°, {u.get('max'):.0f}°)",
                    styles["Normal"],
                ))
            if imp.get("weights_updated"):
                story.append(Paragraph("Injury risk weights updated based on error frequency.", styles["Normal"]))
            for c in imp.get("coaching_additions", []):
                story.append(Paragraph(f"New coaching advice for: {c.get('error', '')}", styles["Normal"]))
        story.append(Spacer(1, 0.2 * inch))

        doc.build(story)
        logger.info("Exported training PDF: %s", path)
        return path
