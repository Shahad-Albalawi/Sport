"""Object tracking for sports equipment.

Professional detection pipeline:
- YOLO (when available): ball, racket, bat
- Color-based fallback: orange/yellow/white/green balls
- Contour-based: barbell, stick (hockey)
"""

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger("sport_analysis.object_tracker")

# COCO class indices for sports equipment
COCO_SPORTS = {
    32: "sports_ball",
    37: "tennis_racket",
    39: "baseball_bat",
}
COCO_CLASS_IDS = set(COCO_SPORTS.keys())

try:
    from ultralytics import YOLO
    HAS_YOLO = True
except ImportError:
    HAS_YOLO = False


@dataclass
class TrackedObject:
    """A detected/tracked object."""

    label: str
    bbox: Tuple[float, float, float, float]  # x, y, w, h (normalized 0-1)
    confidence: float
    frame_idx: int


class ObjectTracker:
    """
    Object tracking using YOLO (when available) and color-based detection
    for sports equipment: ball, racket, bat, barbell.
    """

    BALL_COLORS = {
        "orange_basketball": ((5, 100, 100), (25, 255, 255)),
        "yellow_tennis": ((20, 100, 100), (35, 255, 255)),
        "white_ball": ((0, 0, 200), (180, 30, 255)),
        "green_ball": ((35, 50, 50), (85, 255, 255)),
    }
    # Barbell/weights: dark gray metallic (HSV: low sat, mid value)
    BARBELL_HSV = ((0, 0, 40), (180, 60, 120))
    # Elongated object aspect ratio for stick-like (hockey, etc.)
    STICK_MIN_ASPECT = 3.0

    def __init__(self, min_contour_area: int = 50):
        self.min_contour_area = min_contour_area
        self.tracked_objects: List[TrackedObject] = []
        self._yolo = None
        if HAS_YOLO:
            try:
                self._yolo = YOLO("yolov8s.pt")
                logger.info("YOLO loaded for object detection (yolov8s - higher accuracy)")
            except Exception as e:
                logger.warning("YOLO init failed, using color detection: %s", e)
                self._yolo = None

    def _detect_yolo(
        self, frame: np.ndarray, frame_idx: int
    ) -> List[TrackedObject]:
        """Detect sports equipment using YOLO."""
        if not self._yolo:
            return []
        out = []
        try:
            results = self._yolo(frame, verbose=False)[0]
            h, w = frame.shape[:2]
            if results.boxes is None:
                return []
            for box in results.boxes:
                cls_id = int(box.cls[0])
                if cls_id not in COCO_SPORTS:
                    continue
                conf = float(box.conf[0])
                if conf < 0.25:
                    continue
                xyxy = box.xyxy[0]
                x1, y1, x2, y2 = xyxy[0], xyxy[1], xyxy[2], xyxy[3]
                nx = float(x1 / w)
                ny = float(y1 / h)
                nw = float((x2 - x1) / w)
                nh = float((y2 - y1) / h)
                label = COCO_SPORTS[cls_id]
                out.append(
                    TrackedObject(
                        label=label,
                        bbox=(nx, ny, nw, nh),
                        confidence=conf,
                        frame_idx=frame_idx,
                    )
                )
        except Exception as e:
            logger.debug("YOLO detection failed: %s", e)
        return out

    def _detect_by_color(
        self, frame: np.ndarray, hsv_lower: np.ndarray, hsv_upper: np.ndarray
    ) -> List[Tuple[Tuple[int, int, int, int], float]]:
        """Detect blobs by HSV color range."""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, hsv_lower, hsv_upper)
        mask = cv2.erode(mask, None, iterations=1)
        mask = cv2.dilate(mask, None, iterations=2)
        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        detections = []
        h, w = frame.shape[:2]
        for c in contours:
            area = cv2.contourArea(c)
            if area < self.min_contour_area:
                continue
            x, y, cw, ch = cv2.boundingRect(c)
            if cw > 0 and ch > 0:
                ar = max(cw, ch) / min(cw, ch)
                if ar < 2.0:
                    nx = x / w
                    ny = y / h
                    nw = cw / w
                    nh = ch / h
                    conf = min(1.0, area / (w * h * 0.01))
                    detections.append(((nx, ny, nw, nh), conf))
        return detections

    def detect_objects(
        self,
        frame: np.ndarray,
        frame_idx: int,
    ) -> List[TrackedObject]:
        """
        Detect sports objects: ball, racket, bat.
        YOLO first, then color-based fallback.
        """
        self.tracked_objects.clear()
        h, w = frame.shape[:2]
        seen_labels = set()

        # YOLO detection
        yolo_dets = self._detect_yolo(frame, frame_idx)
        for o in yolo_dets:
            self.tracked_objects.append(o)
            seen_labels.add(o.label)

        # Color-based ball detection (fallback if no ball from YOLO)
        if "sports_ball" not in seen_labels:
            for label, (lower, upper) in self.BALL_COLORS.items():
                lower_np = np.array(lower)
                upper_np = np.array(upper)
                dets = self._detect_by_color(frame, lower_np, upper_np)
                for (nx, ny, nw, nh), conf in dets[:2]:
                    self.tracked_objects.append(
                        TrackedObject(
                            label=label,
                            bbox=(float(nx), float(ny), float(nw), float(nh)),
                            confidence=float(conf),
                            frame_idx=frame_idx,
                        )
                    )

        # Barbell/weights: dark elongated contours (bar shape)
        barbell_dets = self._detect_barbell(frame, frame_idx)
        for o in barbell_dets:
            self.tracked_objects.append(o)
            seen_labels.add("barbell")

        # Hockey stick: elongated contours (aspect > 3)
        stick_dets = self._detect_elongated(frame, frame_idx, "stick")
        for o in stick_dets[:2]:
            self.tracked_objects.append(o)
            seen_labels.add("stick")

        self.tracked_objects.sort(key=lambda o: o.confidence, reverse=True)
        return self.tracked_objects[:10]

    def _detect_barbell(
        self, frame: np.ndarray, frame_idx: int
    ) -> List[TrackedObject]:
        """Detect barbell/weight bar via dark elongated contours."""
        out = []
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 80, 255, cv2.THRESH_BINARY_INV)
            contours, _ = cv2.findContours(
                thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            h, w = frame.shape[:2]
            for c in contours:
                area = cv2.contourArea(c)
                if area < 200 or area > w * h * 0.15:
                    continue
                x, y, cw, ch = cv2.boundingRect(c)
                if cw == 0 or ch == 0:
                    continue
                ar = max(cw, ch) / min(cw, ch)
                if ar < 2.0:  # Bar is elongated (length >> width)
                    continue
                nx, ny = x / w, y / h
                nw, nh = cw / w, ch / h
                conf = min(0.8, area / (w * h * 0.02))
                out.append(
                    TrackedObject(
                        label="barbell",
                        bbox=(float(nx), float(ny), float(nw), float(nh)),
                        confidence=conf,
                        frame_idx=frame_idx,
                    )
                )
        except (cv2.error, ValueError, TypeError) as e:
            logger.debug("Barbell detection failed: %s", e)
        return out[:2]

    def _detect_elongated(
        self, frame: np.ndarray, frame_idx: int, label: str = "stick"
    ) -> List[TrackedObject]:
        """Detect elongated stick-like objects (hockey stick, etc.)."""
        out = []
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(
                edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            h, w = frame.shape[:2]
            for c in contours:
                area = cv2.contourArea(c)
                if area < 150:
                    continue
                x, y, cw, ch = cv2.boundingRect(c)
                if cw == 0 or ch == 0:
                    continue
                ar = max(cw, ch) / min(cw, ch)
                if ar < self.STICK_MIN_ASPECT:
                    continue
                nx, ny = x / w, y / h
                nw, nh = cw / w, ch / h
                conf = min(0.6, area / (w * h * 0.01))
                out.append(
                    TrackedObject(
                        label=label,
                        bbox=(float(nx), float(ny), float(nw), float(nh)),
                        confidence=conf,
                        frame_idx=frame_idx,
                    )
                )
        except (cv2.error, ValueError, TypeError) as e:
            logger.debug("Elongated object detection failed: %s", e)
        return out[:2]
