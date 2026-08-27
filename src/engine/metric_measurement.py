"""Measurement primitives with explicit calibration provenance.

This module deliberately separates calibration error from segmentation error.
It never converts pixels to millimetres unless a physical reference has been
measured and validated.  The existing ScaleDetector remains the classical-CV
fallback; this layer adds higher-confidence planar references and a stable
machine-readable contract around every estimate.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Sequence

import cv2
import numpy as np


@dataclass
class MetricCalibration:
    reference_type: str = "none"
    valid: bool = False
    confidence: float = 0.0
    pixels_per_mm: Optional[float] = None
    local_transform: Optional[np.ndarray] = None
    reference_points_px: tuple[tuple[float, float], ...] = ()
    reference_points_mm: tuple[tuple[float, float], ...] = ()
    reprojection_error_px: Optional[float] = None
    relative_uncertainty: Optional[float] = None
    warning: str = "no trustworthy physical reference was found"
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "reference_type": self.reference_type,
            "valid": self.valid,
            "confidence": round(float(self.confidence), 4),
            "pixels_per_mm": round(float(self.pixels_per_mm), 5) if self.pixels_per_mm else None,
            "reference_points_px": [list(map(float, p)) for p in self.reference_points_px],
            "reference_points_mm": [list(map(float, p)) for p in self.reference_points_mm],
            "reprojection_error_px": self.reprojection_error_px,
            "relative_uncertainty": self.relative_uncertainty,
            "warning": self.warning,
            "metadata": self.metadata,
            "homography_available": self.local_transform is not None,
        }


def _order_quad(points: np.ndarray) -> np.ndarray:
    points = np.asarray(points, dtype=np.float32).reshape(-1, 2)
    sums, diffs = points.sum(axis=1), np.diff(points, axis=1).ravel()
    return np.array([points[np.argmin(sums)], points[np.argmin(diffs)],
                     points[np.argmax(sums)], points[np.argmax(diffs)]], dtype=np.float32)


def _planar_calibration(
    image_points: np.ndarray,
    world_points_mm: np.ndarray,
    reference_type: str,
    metadata: Optional[dict] = None,
) -> MetricCalibration:
    image_points = np.asarray(image_points, dtype=np.float32).reshape(-1, 2)
    world_points_mm = np.asarray(world_points_mm, dtype=np.float32).reshape(-1, 2)
    if len(image_points) < 4 or len(world_points_mm) != len(image_points):
        return MetricCalibration(reference_type=reference_type, warning="insufficient reference points")
    homography, inliers = cv2.findHomography(image_points, world_points_mm, cv2.RANSAC, 2.0)
    if homography is None:
        return MetricCalibration(reference_type=reference_type, warning="homography estimation failed")
    projected = cv2.perspectiveTransform(image_points[None], homography)[0]
    error = float(np.sqrt(np.mean(np.sum((projected - world_points_mm) ** 2, axis=1))))
    # Local scale is evaluated at the reference centre from the Jacobian of
    # the pixel-to-mm homography.  This is more accurate than a global ppm
    # when a ruler/card is viewed obliquely.
    centre = image_points.mean(axis=0).astype(np.float32)
    eps = 1.0
    probes = np.array([[centre[0], centre[1]], [centre[0] + eps, centre[1]],
                       [centre[0], centre[1] + eps]], dtype=np.float32)[None]
    mapped = cv2.perspectiveTransform(probes, homography)[0]
    sx = float(np.linalg.norm(mapped[1] - mapped[0]))
    sy = float(np.linalg.norm(mapped[2] - mapped[0]))
    ppm = 2.0 / max(sx + sy, 1e-9)
    relative_uncertainty = min(1.0, error / max(float(np.linalg.norm(np.ptp(world_points_mm, axis=0))), 1.0))
    valid = bool(np.isfinite(ppm) and ppm > 0 and error <= 3.0 and np.all(np.asarray(inliers).ravel() > 0))
    return MetricCalibration(
        reference_type=reference_type, valid=valid,
        confidence=float(np.clip(0.98 - error / 10.0, 0.0, 0.98)) if valid else 0.0,
        pixels_per_mm=ppm if valid else None, local_transform=homography,
        reference_points_px=tuple(tuple(map(float, p)) for p in image_points),
        reference_points_mm=tuple(tuple(map(float, p)) for p in world_points_mm),
        reprojection_error_px=round(error, 4),
        relative_uncertainty=round(relative_uncertainty, 5),
        warning="valid planar calibration" if valid else "planar reference reprojection error is too high",
        metadata=metadata or {},
    )


class ReferenceCalibrator:
    """High-confidence reference calibration methods in priority order."""

    def aruco(
        self, image_rgb: np.ndarray, marker_size_mm: float,
        marker_id: Optional[int] = None,
    ) -> MetricCalibration:
        if not marker_size_mm or not hasattr(cv2, "aruco"):
            return MetricCalibration(reference_type="aruco", warning="ArUco support or marker size is unavailable")
        gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)
        aruco = cv2.aruco
        dictionary = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
        parameters = aruco.DetectorParameters()
        corners, ids, _ = aruco.detectMarkers(gray, dictionary, parameters=parameters)
        if ids is None:
            return MetricCalibration(reference_type="aruco", warning="no ArUco marker detected")
        for corner, ident in zip(corners, ids.ravel()):
            if marker_id is not None and int(ident) != int(marker_id):
                continue
            quad = _order_quad(corner.reshape(4, 2))
            half = float(marker_size_mm) / 2.0
            world = np.array([[-half, -half], [half, -half], [half, half], [-half, half]], dtype=np.float32)
            return _planar_calibration(quad, world, "aruco", {"marker_id": int(ident), "marker_size_mm": marker_size_mm})
        return MetricCalibration(reference_type="aruco", warning="requested ArUco marker id was not detected")

    def checkerboard(
        self, image_rgb: np.ndarray, inner_corners: tuple[int, int], square_size_mm: float,
    ) -> MetricCalibration:
        if square_size_mm <= 0:
            return MetricCalibration(reference_type="checkerboard", warning="checkerboard square size is unavailable")
        gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)
        pattern = tuple(map(int, inner_corners))
        if not hasattr(cv2, "findChessboardCornersSB"):
            return MetricCalibration(reference_type="checkerboard", warning="OpenCV checkerboard detector is unavailable")
        found, corners = cv2.findChessboardCornersSB(gray, pattern, flags=cv2.CALIB_CB_EXHAUSTIVE)
        if not found:
            return MetricCalibration(reference_type="checkerboard", warning="no checkerboard detected")
        # Four outermost detected corners define the usable planar extent.
        pts = corners.reshape(-1, 2)
        quad = _order_quad(np.array([pts[0], pts[pattern[0] - 1], pts[-1], pts[-pattern[0]]]))
        world = np.array([[0, 0], [(pattern[0] - 1) * square_size_mm, 0],
                          [(pattern[0] - 1) * square_size_mm, (pattern[1] - 1) * square_size_mm],
                          [0, (pattern[1] - 1) * square_size_mm]], dtype=np.float32)
        return _planar_calibration(quad, world, "checkerboard", {"inner_corners": pattern, "square_size_mm": square_size_mm})

    @staticmethod
    def fuse(calibrations: Sequence[MetricCalibration]) -> MetricCalibration:
        valid = [c for c in calibrations if c.valid and c.pixels_per_mm]
        if not valid:
            return min(calibrations, key=lambda c: c.confidence) if calibrations else MetricCalibration()
        values = np.asarray([c.pixels_per_mm for c in valid], dtype=float)
        median = float(np.median(values))
        relative_spread = float(np.max(np.abs(values - median)) / max(median, 1e-9))
        if relative_spread > 0.10:
            return MetricCalibration(reference_type="conflict", warning="valid references disagree by more than 10%", metadata={"candidate_scales": values.tolist()})
        best = max(valid, key=lambda c: c.confidence)
        best.metadata = {**best.metadata, "fused_reference_count": len(valid), "relative_spread": relative_spread}
        best.pixels_per_mm = median
        best.confidence = min(best.confidence, max(0.0, 1.0 - relative_spread * 4.0))
        return best


def save_debug_panel(
    image_rgb: np.ndarray, raw_mask: np.ndarray, final_mask: np.ndarray,
    output_path: str | Path, calibration: MetricCalibration,
    feret_endpoints: Optional[tuple[float, float, float, float]] = None,
    diameter_text: Optional[str] = None,
) -> str:
    """Save a compact visual audit artifact for calibration/segmentation QA."""
    canvas = cv2.cvtColor(image_rgb.copy(), cv2.COLOR_RGB2BGR)
    raw = np.asarray(raw_mask) > 0
    final = np.asarray(final_mask) > 0
    canvas[raw & ~final] = (0, 0, 255)
    canvas[final] = (0, 180, 0)
    if feret_endpoints:
        x1, y1, x2, y2 = map(int, feret_endpoints)
        cv2.line(canvas, (x1, y1), (x2, y2), (255, 0, 255), 3, cv2.LINE_AA)
    if calibration.reference_points_px:
        pts = np.asarray(calibration.reference_points_px, dtype=np.int32).reshape(-1, 1, 2)
        cv2.polylines(canvas, [pts], True, (255, 200, 0), 3)
    label = diameter_text or "diameter unavailable"
    cv2.putText(canvas, f"{calibration.reference_type}: {label}", (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(canvas, f"cal={calibration.confidence:.2f} err={calibration.reprojection_error_px or 0:.2f}px", (15, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), canvas)
    return str(path)
