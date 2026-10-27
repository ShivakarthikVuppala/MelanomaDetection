"""Reference-object detection and pixel-to-millimetre calibration.

Auto mode measures repeated dark ruler ticks on the original image. The
acquisition device supplies their physical interval (1 mm for this dataset),
so no practitioner entry or object-detector bounding box sets the scale.
"""

from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

from .metric_measurement import ReferenceCalibrator
from .ruler_ticks import find_tick_lattices


KNOWN_REFERENCES = {
    "us_penny": 19.05,
    "us_quarter": 24.26,
    "us_dime": 17.91,
    "euro_1": 23.25,
    "euro_2": 25.75,
    "inr_1": 21.50,
    "inr_2": 25.00,
    "inr_5": 23.00,
    "gbp_1p": 20.30,
    "gbp_1": 22.50,
    "sticker_25mm": 25.00,
    "sticker_20mm": 20.00,
}


@dataclass
class ScaleCalibration:
    pixels_per_mm: Optional[float] = None
    method: str = "none"
    confidence: float = 0.0
    reference_type: str = "none"
    reference_diameter_px: Optional[float] = None
    reference_diameter_mm: Optional[float] = None
    reference_length_px: Optional[float] = None
    reference_length_mm: Optional[float] = None
    reference_center_px: Optional[tuple[float, float]] = None
    reference_bbox_px: Optional[tuple[int, int, int, int]] = None
    orientation: str = "unknown"
    angle_degrees: Optional[float] = None
    interval_mm: Optional[float] = None
    tick_positions_px: Optional[tuple[float, ...]] = None
    tick_spacing_px: Optional[float] = None
    validated_tick_count: int = 0
    reference_points_px: Optional[tuple[tuple[float, float], ...]] = None
    reprojection_error_px: Optional[float] = None
    calibration_uncertainty: Optional[float] = None
    warnings: tuple[str, ...] = ()
    homography: Optional[tuple[tuple[float, ...], ...]] = None
    axis_endpoints_px: Optional[tuple[tuple[float, float], tuple[float, float]]] = None
    tick_points_px: Optional[tuple[tuple[float, float], ...]] = None
    interval_residuals_px: Optional[tuple[float, ...]] = None
    detected: bool = False
    calibration_valid: bool = False
    validation_reason: str = "reference calibration not available"

    def to_dict(self) -> dict:
        return {
            "pixels_per_mm": round(self.pixels_per_mm, 4) if self.pixels_per_mm else None,
            "method": self.method,
            "confidence": round(float(self.confidence), 4),
            "scale_confidence": round(float(self.confidence), 4),
            "reference_type": self.reference_type,
            "reference_diameter_px": round(self.reference_diameter_px, 2) if self.reference_diameter_px else None,
            "reference_diameter_mm": self.reference_diameter_mm,
            "reference_length_px": round(self.reference_length_px, 2) if self.reference_length_px else None,
            "reference_length_mm": self.reference_length_mm,
            "reference_center_px": tuple(round(v, 2) for v in self.reference_center_px) if self.reference_center_px else None,
            "reference_bbox_px": self.reference_bbox_px,
            "scale_region": (
                {
                    "x": int(self.reference_bbox_px[0]),
                    "y": int(self.reference_bbox_px[1]),
                    "width": int(self.reference_bbox_px[2]),
                    "height": int(self.reference_bbox_px[3]),
                }
                if self.reference_bbox_px is not None else None
            ),
            "orientation": self.orientation,
            "angle_degrees": round(self.angle_degrees, 3) if self.angle_degrees is not None else None,
            "interval_mm": self.interval_mm,
            "tick_positions_px": (
                [round(float(value), 2) for value in self.tick_positions_px]
                if self.tick_positions_px is not None else None
            ),
            "tick_spacing_px": round(float(self.tick_spacing_px), 3) if self.tick_spacing_px is not None else None,
            "validated_tick_count": int(self.validated_tick_count),
            "reference_points_px": self.reference_points_px,
            "reprojection_error_px": self.reprojection_error_px,
            "calibration_uncertainty": self.calibration_uncertainty,
            "warnings": list(self.warnings),
            "homography": self.homography,
            "axis_endpoints_px": self.axis_endpoints_px,
            "tick_points_px": self.tick_points_px,
            "interval_residuals_px": self.interval_residuals_px,
            "detected": self.detected,
            "scale_detected": bool(self.detected and self.calibration_valid),
            "calibration_valid": self.calibration_valid,
            "calibration_confidence": round(float(self.confidence), 4),
            "calibration_method": self.method,
            "calibration_reason": self.validation_reason,
            "validation_reason": self.validation_reason,
        }


class ScaleDetector:
    """Detect a known circular marker or a metric ruler in the current image.

    Circular references still require a known physical diameter. For a ruler,
    the pixel interval is measured from repeated tick positions and a metric
    1 mm minor division is accepted only after the repeated-spacing structure
    passes validation; no fixed pixels-per-mm value is used.
    """

    def __init__(self, min_circle_radius: int = 30, max_circle_radius: int = 300,
                 hough_param1: float = 100, hough_param2: float = 40):
        self.min_r = min_circle_radius
        self.max_r = max_circle_radius
        self.param1 = hough_param1
        self.param2 = hough_param2

    def detect(self, image: np.ndarray, method: str = "auto",
               known_diameter_mm: Optional[float] = None,
               known_object_px: Optional[float] = None,
               known_object_mm: Optional[float] = None,
               line_length_mm: Optional[float] = None,
               reference_key: Optional[str] = None,
               lesion_mask: Optional[np.ndarray] = None,
               aruco_marker_size_mm: Optional[float] = None,
               aruco_marker_id: Optional[int] = None,
               charuco_squares_x: Optional[int] = None,
               charuco_squares_y: Optional[int] = None,
               charuco_square_length_mm: Optional[float] = None,
               charuco_marker_length_mm: Optional[float] = None,
               charuco_dictionary_id: int = 0,
               checkerboard_inner_corners: Optional[tuple[int, int]] = None,
               checkerboard_square_size_mm: Optional[float] = None,
               ruler_tick_interval_mm: Optional[float] = 1.0) -> ScaleCalibration:
        method = (method or "none").strip().lower()
        if method in {"none", "off", "disabled"}:
            return ScaleCalibration(pixels_per_mm=0.0, method="none", validation_reason="scale calibration disabled; diameter (D) not calculated", calibration_valid=False)
        if method in {"coin", "sticker"}:
            method = "circle"
        requested_reference_type = None
        if reference_key in KNOWN_REFERENCES:
            known_diameter_mm = KNOWN_REFERENCES[reference_key]
            requested_reference_type = "sticker" if reference_key.startswith("sticker_") else "coin"
        if known_diameter_mm is not None and known_diameter_mm <= 0:
            return ScaleCalibration(method=method)

        # Planar references have priority because homography corrects local
        # perspective instead of assuming one global pixels/mm value.
        calibrator = ReferenceCalibrator()
        planar = []
        # ChArUco gives more accurate sub-pixel corners than a bare ArUco
        # marker while still tolerating partial board views.  It is therefore
        # the preferred planar reference when a board is configured.
        if all(value is not None for value in (
            charuco_squares_x, charuco_squares_y, charuco_square_length_mm,
            charuco_marker_length_mm,
        )):
            planar.append(calibrator.charuco(
                image, int(charuco_squares_x), int(charuco_squares_y),
                float(charuco_square_length_mm), float(charuco_marker_length_mm),
                int(charuco_dictionary_id),
            ))
        if aruco_marker_size_mm:
            planar.append(calibrator.aruco(image, aruco_marker_size_mm, aruco_marker_id))
        if checkerboard_inner_corners and checkerboard_square_size_mm:
            planar.append(calibrator.checkerboard(image, checkerboard_inner_corners, checkerboard_square_size_mm))
        valid_planar = [c for c in planar if c.valid]
        if valid_planar:
            selected = calibrator.fuse(valid_planar)
            return ScaleCalibration(
                pixels_per_mm=selected.pixels_per_mm, method=selected.reference_type,
                confidence=selected.confidence, reference_type=selected.reference_type,
                reference_length_px=(1.0 / selected.pixels_per_mm if selected.pixels_per_mm else None),
                reference_length_mm=1.0, detected=True, calibration_valid=True,
                validation_reason=selected.warning,
                reference_points_px=selected.reference_points_px,
                reprojection_error_px=selected.reprojection_error_px,
                calibration_uncertainty=selected.relative_uncertainty,
                warnings=(selected.warning,),
                homography=tuple(tuple(float(v) for v in row) for row in selected.local_transform) if selected.local_transform is not None else None,
            )

        if method == "manual":
            if known_object_px is not None:
                return self._from_manual(known_object_px, known_object_mm)
            # The current UI supplies the physical diameter and asks us to
            # locate that circular object in the uploaded image.
            return self._detect_circular(
                image, known_object_mm or known_diameter_mm, "manual", lesion_mask
            )
        if method == "circle":
            return self._detect_circular(
                image, known_diameter_mm,
                reference_type=requested_reference_type,
                lesion_mask=lesion_mask,
            )
        if method == "ruler":
            return self._detect_ruler(
                image, known_length_mm=known_diameter_mm, lesion_mask=lesion_mask,
                tick_interval_mm=ruler_tick_interval_mm,
            )
        if method in {"line", "scale_bar", "scale-bar", "stroke", "mark", "marker_line"}:
            return self._detect_line(
                image,
                known_length_mm=known_object_mm or known_diameter_mm or line_length_mm,
                lesion_mask=lesion_mask,
            )

        # Measure the actual tick interval before considering other references.
        # A ruler bounding box has no known physical length, especially when
        # the scale is cropped or consists only of short marks on the skin.
        ruler = self._detect_ruler(
            image, lesion_mask=lesion_mask, tick_interval_mm=ruler_tick_interval_mm,
        )
        if ruler.detected:
            return ruler
        if known_diameter_mm is not None:
            circle = self._detect_circular(
                image, known_diameter_mm, reference_type=requested_reference_type,
                lesion_mask=lesion_mask,
            )
            if circle.calibration_valid:
                return circle
        known_line_mm = known_object_mm or line_length_mm
        if known_line_mm is not None:
            line = self._detect_line(image, known_length_mm=known_line_mm, lesion_mask=lesion_mask)
            if line.calibration_valid:
                return line
        return ScaleCalibration(
            method="auto",
            validation_reason=(
                "no reliable repeated ruler ticks or known-size reference were found; "
                "physical diameter is unavailable"
            ),
        )

    @staticmethod
    def _refine_circle_radius(gray: np.ndarray, cx: float, cy: float, radius: float) -> tuple[float, float]:
        """Refine a Hough radius from robust radial edge evidence.

        HoughCircles is useful for proposing candidates but its radius is
        quantized and can lock onto an inner highlight.  For each angle we
        search the original-resolution gradient along a narrow radial band,
        then use a robust median of the supported edge locations.  This is
        equivalent to measuring the visible reference boundary rather than
        trusting a single detector parameterization.
        """
        h, w = gray.shape[:2]
        angles = np.linspace(0.0, 2.0 * np.pi, 180, endpoint=False)
        radii = np.linspace(max(2.0, radius * 0.72), radius * 1.28, 45)
        gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        gradient = cv2.magnitude(gx, gy)
        samples = []
        for angle in angles:
            xs = np.clip(np.rint(cx + radii * np.cos(angle)).astype(int), 0, w - 1)
            ys = np.clip(np.rint(cy + radii * np.sin(angle)).astype(int), 0, h - 1)
            response = gradient[ys, xs]
            index = int(np.argmax(response))
            if float(response[index]) >= max(8.0, float(np.percentile(response, 60))):
                samples.append(float(radii[index]))
        if len(samples) < 40:
            return float(radius), 0.0
        refined = float(np.median(samples))
        mad = float(np.median(np.abs(np.asarray(samples) - refined)))
        support = float(np.mean(np.abs(np.asarray(samples) - refined) <= max(2.0, 2.5 * mad)))
        return refined, support

    def _detect_circular(
        self,
        image: np.ndarray,
        known_diameter_mm: Optional[float] = None,
        reference_type: Optional[str] = None,
        lesion_mask: Optional[np.ndarray] = None,
    ) -> ScaleCalibration:
        """Find the most plausible reference circle, not simply the first Hough circle."""
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        source_height, source_width = gray.shape[:2]
        resize_scale = min(1.0, 1600.0 / max(source_height, source_width))
        if resize_scale < 1.0:
            gray = cv2.resize(
                gray,
                (max(1, int(round(source_width * resize_scale))),
                 max(1, int(round(source_height * resize_scale)))),
                interpolation=cv2.INTER_AREA,
            )
        blurred = cv2.GaussianBlur(gray, (9, 9), 2)
        height, width = gray.shape[:2]
        min_dim = min(height, width)
        min_radius = max(8, min(self.min_r, min_dim // 10))
        max_radius = min(self.max_r, max(min_radius + 2, min_dim // 3))
        candidates = []
        for param2 in (self.param2, max(24.0, self.param2 - 8.0), self.param2 + 8.0):
            circles = cv2.HoughCircles(
                blurred, cv2.HOUGH_GRADIENT, dp=1.2,
                minDist=max(20, int(min_dim * 0.08)),
                param1=self.param1, param2=param2,
                minRadius=min_radius, maxRadius=max_radius,
            )
            if circles is not None:
                candidates.extend(circles[0])
        if not candidates:
            return ScaleCalibration()

        gradient = cv2.Laplacian(gray, cv2.CV_32F)
        gradient_cutoff = np.percentile(np.abs(gradient), 70)
        yy, xx = np.ogrid[:height, :width]
        lesion_binary = None
        largest_lesion_label = None
        lesion_labels = None
        if lesion_mask is not None:
            lesion_array = np.asarray(lesion_mask)
            if lesion_array.shape == (source_height, source_width) and resize_scale < 1.0:
                lesion_array = cv2.resize(
                    lesion_array.astype(np.uint8),
                    (width, height),
                    interpolation=cv2.INTER_NEAREST,
                )
            if lesion_array.shape == gray.shape:
                lesion_binary = (lesion_array > 0).astype(np.uint8)
        if lesion_binary is not None:
            count, lesion_labels, stats, _ = cv2.connectedComponentsWithStats(lesion_binary, 8)
            if count > 1:
                largest_lesion_label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        best = None
        best_score = -1.0
        for cx, cy, radius in candidates:
            edge_dist = min(cx, cy, width - cx, height - cy)
            # A partial circle touching an image border is evidence against a
            # reference.  The old inverted score made border artifacts win.
            edge_score = min(edge_dist / max(min_dim * 0.35, 1.0), 1.0)
            size_ratio = (2.0 * radius) / max(min_dim, 1)
            size_score = 1.0 if 0.03 <= size_ratio <= 0.30 else max(0.0, 1.0 - abs(size_ratio - 0.16) / 0.30)
            angles = np.linspace(0, 2 * np.pi, 96, endpoint=False)
            xs = np.clip(np.round(cx + radius * np.cos(angles)).astype(int), 1, width - 2)
            ys = np.clip(np.round(cy + radius * np.sin(angles)).astype(int), 1, height - 2)
            edge_support = float(np.mean(np.abs(gradient[ys, xs]) > gradient_cutoff))
            inner_radius = max(2, int(radius * 0.55))
            inner = (xx - cx) ** 2 + (yy - cy) ** 2 <= inner_radius ** 2
            interior_std = float(np.std(gray[inner])) if np.any(inner) else 255.0
            uniformity = 1.0 - min(interior_std / 80.0, 1.0)
            score = 0.45 * edge_score + 0.25 * edge_support + 0.20 * size_score + 0.10 * uniformity
            if lesion_binary is not None:
                circle_region = (xx - cx) ** 2 + (yy - cy) ** 2 <= radius ** 2
                lesion_fraction = float(lesion_binary[circle_region].mean()) if np.any(circle_region) else 0.0
                center_x = int(np.clip(round(cx), 0, width - 1))
                center_y = int(np.clip(round(cy), 0, height - 1))
                center_label = int(lesion_labels[center_y, center_x]) if lesion_labels is not None else 0
                # A lesion-shaped circle is not a scale reference. Prefer a
                # candidate outside the dominant segmented lesion and reject
                # candidates whose disk is mostly covered by that lesion.
                if center_label == largest_lesion_label or lesion_fraction >= 0.60:
                    score *= 0.12
            if size_ratio > 0.40:
                score *= 0.1
            if score > best_score:
                best_score, best = score, (cx, cy, radius)
        minimum_score = 0.45 if known_diameter_mm is not None else 0.30
        if best is None or best_score < minimum_score:
            return ScaleCalibration(
                method="circle",
                reference_type=reference_type or "circle",
                validation_reason="no circular reference met the confidence threshold",
            )

        center_x, center_y, radius = best
        # Refine on the detector's working image.  The result is converted
        # back below when the detector used a bounded resize.
        refined_radius, radial_support = self._refine_circle_radius(
            gray, float(center_x), float(center_y), float(radius)
        )
        if radial_support >= 0.55:
            radius = refined_radius
            best_score = min(1.0, best_score + 0.05 * radial_support)
        diameter_px = float(radius * 2.0 / resize_scale)
        center_x_source = float(center_x / resize_scale)
        center_y_source = float(center_y / resize_scale)
        bbox = (
            int(round(center_x_source - diameter_px / 2.0)),
            int(round(center_y_source - diameter_px / 2.0)),
            int(round(diameter_px)),
            int(round(diameter_px)),
        )
        common_type = "circle"
        bbox_valid = (
            bbox[2] >= 10 and bbox[3] >= 10
            and bbox[0] >= 0 and bbox[1] >= 0
            and bbox[0] + bbox[2] <= source_width and bbox[1] + bbox[3] <= source_height
        )
        selected_lesion_fraction = 0.0
        if lesion_binary is not None:
            selected_region = (xx - center_x) ** 2 + (yy - center_y) ** 2 <= radius ** 2
            selected_lesion_fraction = float(lesion_binary[selected_region].mean()) if np.any(selected_region) else 1.0
        if known_diameter_mm is None:
            return ScaleCalibration(
                method="circle", reference_type="circle_unknown",
                reference_diameter_px=diameter_px,
                reference_center_px=(center_x_source, center_y_source),
                reference_bbox_px=bbox, detected=True,
                confidence=float(round(float(min(best_score, 0.5)), 4)),
                calibration_valid=False,
                validation_reason="physical diameter for the circular reference was not supplied",
            )
        valid = (
            bbox_valid
            and diameter_px >= 10.0
            and selected_lesion_fraction < 0.30
            and best_score >= 0.45
        )
        return ScaleCalibration(
            pixels_per_mm=diameter_px / known_diameter_mm if valid else None,
            method="circle", confidence=float(round(float(min(best_score * 0.95, 0.95)), 4)),
            reference_type=reference_type or common_type,
            reference_diameter_px=diameter_px,
            reference_diameter_mm=known_diameter_mm,
            reference_center_px=(center_x_source, center_y_source),
            reference_bbox_px=bbox, detected=True,
            calibration_valid=bool(valid),
            validation_reason=(
                "valid circular reference calibration"
                if valid else "circular reference geometry or segmentation overlap was unreliable"
            ),
        )

    def _detect_line(
        self,
        image: np.ndarray,
        known_length_mm: Optional[float] = None,
        lesion_mask: Optional[np.ndarray] = None,
    ) -> ScaleCalibration:
        """Detect a single hand-drawn straight black line and measure its span.

        Dermoscopic images in this workflow often carry only a black ink
        marking rather than a coin or a printed metric ruler.  Such a stroke
        has no circular boundary and no repeated tick lattice, so both the
        circle and ruler detectors reject it.  This detector instead isolates
        near-black ink and keeps the most line-like connected component — long,
        thin and straight — then fits its principal axis and reports the drawn
        pixel span and endpoints.

        A pixel span alone is not a scale: converting it to millimetres still
        requires the physical length of the stroke.  When that length is not
        supplied the stroke is reported as detected but uncalibrated, exactly
        like a circle of unknown diameter.
        """
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        source_h, source_w = gray.shape[:2]
        scale = min(1.0, 1800.0 / max(source_h, source_w))
        if scale < 1.0:
            gray = cv2.resize(
                gray,
                (max(1, int(round(source_w * scale))), max(1, int(round(source_h * scale)))),
                interpolation=cv2.INTER_AREA,
            )
        h, w = gray.shape[:2]
        min_dim = min(h, w)

        # Black marker ink is far darker than skin.  Tie the cutoff to the dark
        # tail of the histogram but clamp it, so a dark frame does not turn the
        # whole image into "ink" and a bright frame still finds the stroke.
        dark_cutoff = int(np.clip(np.percentile(gray, 4), 45, 110))
        dark = (gray < dark_cutoff).astype(np.uint8)
        # Open removes isolated speckle and thin hair fragments; close bridges
        # the small gaps a marker leaves where it skips over pores.
        dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
        dark = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))

        lesion_binary = None
        if lesion_mask is not None:
            mask_array = np.asarray(lesion_mask)
            if mask_array.size and mask_array.shape != gray.shape:
                mask_array = cv2.resize(
                    mask_array.astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST,
                )
            if mask_array.shape == gray.shape:
                lesion_binary = (mask_array > 0).astype(np.uint8)

        count, labels, stats, _ = cv2.connectedComponentsWithStats(dark, 8)
        best = None
        best_score = -1.0
        for label in range(1, count):
            area = int(stats[label, cv2.CC_STAT_AREA])
            if area < max(40, int(min_dim * 0.02)):
                continue
            ys, xs = np.where(labels == label)
            points = np.column_stack([xs, ys]).astype(np.float32)
            mean, eigenvectors = cv2.PCACompute(points, mean=None)
            axis = eigenvectors[0]
            perpendicular = eigenvectors[1]
            projections = (points - mean[0]) @ axis
            span = float(projections.max() - projections.min())
            if span < max(30.0, min_dim * 0.08):
                continue
            # A drawn stroke is thin: its area divided by its length is the
            # average width.  This rejects filled blobs, vignette rings and
            # dark background regions, which are broad rather than stroke-like.
            thickness = float(area) / max(span, 1.0)
            if not 1.5 <= thickness <= max(12.0, min_dim * 0.04):
                continue
            # Straightness: the perpendicular spread about the principal axis.
            # A straight line keeps this near the half-width; a curved hair or
            # a blob spreads much further.
            residual = float(np.sqrt(np.mean(((points - mean[0]) @ perpendicular) ** 2)))
            if residual > max(3.0, thickness * 1.2):
                continue

            length_fraction = span / max(min_dim, 1)
            straightness = 1.0 - min(residual / max(thickness, 1.0), 1.0)
            darkness = 1.0 - min(float(gray[ys, xs].mean()) / max(dark_cutoff, 1), 1.0)
            score = (
                0.40 * min(length_fraction / 0.5, 1.0)
                + 0.25 * straightness
                + 0.20 * min(span / max(4.0 * residual, 1.0) / 20.0, 1.0)
                + 0.15 * darkness
            )
            if lesion_binary is not None:
                # A stroke lying inside the segmented lesion is a clinical mark,
                # not a scale reference.
                if float(lesion_binary[ys, xs].mean()) >= 0.5:
                    score *= 0.2
            if score > best_score:
                best_score = score
                best = (span, mean[0], axis, points, projections, residual)

        if best is None or best_score < 0.45:
            return ScaleCalibration(
                method="line", reference_type="line",
                validation_reason="no straight black reference line met the confidence threshold",
            )

        span, center, axis, points, projections, _ = best
        start = points[int(np.argmin(projections))]
        end = points[int(np.argmax(projections))]
        span_source = float(span / max(scale, 1e-9))
        start_source = (float(start[0] / scale), float(start[1] / scale))
        end_source = (float(end[0] / scale), float(end[1] / scale))
        center_source = (float(center[0] / scale), float(center[1] / scale))
        xs_source, ys_source = points[:, 0] / scale, points[:, 1] / scale
        bbox = (
            int(max(0, xs_source.min() - 4)),
            int(max(0, ys_source.min() - 4)),
            int(xs_source.max() - xs_source.min() + 9),
            int(ys_source.max() - ys_source.min() + 9),
        )
        angle = float(np.degrees(np.arctan2(axis[1], axis[0])))
        orientation = "horizontal" if abs(axis[0]) >= abs(axis[1]) else "vertical"
        confidence = float(np.clip(best_score * 0.9, 0.0, 0.9))

        if known_length_mm is None or known_length_mm <= 0:
            return ScaleCalibration(
                pixels_per_mm=0.0,
                method="line",
                reference_type="line_unknown",
                confidence=float(round(min(confidence, 0.5), 4)),
                reference_length_px=span_source,
                reference_length_mm=0.0,
                reference_center_px=center_source,
                reference_bbox_px=bbox,
                axis_endpoints_px=(start_source, end_source),
                orientation=orientation,
                angle_degrees=angle,
                detected=True,
                calibration_valid=False,
                validation_reason="physical length of the black line was not supplied; diameter (D) not calculated",
            )

        valid = span_source >= 20.0 and best_score >= 0.45 and known_length_mm > 0
        return ScaleCalibration(
            pixels_per_mm=span_source / known_length_mm if valid else 0.0,
            method="line",
            reference_type="line",
            confidence=float(round(confidence, 4)),
            reference_length_px=span_source,
            reference_length_mm=known_length_mm,
            reference_center_px=center_source,
            reference_bbox_px=bbox,
            axis_endpoints_px=(start_source, end_source),
            orientation=orientation,
            angle_degrees=angle,
            detected=True,
            calibration_valid=bool(valid),
            validation_reason=(
                "valid black-line reference calibration"
                if valid else "black-line span or geometry was unreliable"
            ),
        )

    def _detect_ruler(
        self, image: np.ndarray, known_length_mm: Optional[float] = None,
        lesion_mask: Optional[np.ndarray] = None,
        tick_interval_mm: Optional[float] = 1.0,
    ) -> ScaleCalibration:
        """Calibrate from repeated strokes and the device's minor-tick interval.

        ``known_length_mm`` retains the explicit ruler-mode interval override.
        Auto mode never reuses a coin diameter as the ruler's tick interval.
        """
        rows = find_tick_lattices(image, lesion_mask)
        if not rows:
            return ScaleCalibration(
                method="ruler", reference_type="ruler",
                validation_reason="fewer than six reliable, aligned, regularly spaced ruler ticks",
            )
        best = rows[0]
        interval = known_length_mm if known_length_mm is not None else tick_interval_mm
        valid_interval = interval is not None and np.isfinite(interval) and interval > 0
        # Strong independent rows should agree. Do not hide perspective or
        # conflicting scales by selecting whichever produces a plausible size.
        conflict = any(
            len(row.positions) >= max(6, 0.75 * len(best.positions))
            and abs(row.spacing / best.spacing - 1.0) > 0.10
            for row in rows[1:]
        )
        valid = bool(valid_interval and not conflict)
        if conflict:
            reason = "visible ruler rows disagree on tick spacing; physical measurement withheld"
        elif not valid_interval:
            reason = "ruler ticks detected but their physical interval is not configured"
        else:
            reason = (f"{len(best.positions)} validated ruler ticks; {best.spacing:.3f} pixels "
                      f"per configured {interval:g} mm division")
        points = tuple(tuple(float(value) for value in point) for point in best.points)
        angle = float(np.degrees(np.arctan2(best.tangent[1], best.tangent[0])))
        return ScaleCalibration(
            pixels_per_mm=best.spacing / float(interval) if valid else None,
            method="ruler", reference_type="ruler", detected=True,
            confidence=best.confidence if valid else min(best.confidence, 0.49),
            calibration_valid=valid, validation_reason=reason,
            reference_length_px=best.spacing,
            reference_length_mm=float(interval) if valid_interval else None,
            reference_bbox_px=best.bbox,
            reference_center_px=tuple(float(value) for value in best.points.mean(axis=0)),
            orientation="horizontal" if abs(best.tangent[0]) >= abs(best.tangent[1]) else "vertical",
            angle_degrees=angle, interval_mm=float(interval) if valid_interval else None,
            tick_positions_px=tuple(float(value) for value in best.positions),
            tick_spacing_px=best.spacing, validated_tick_count=len(best.positions),
            reference_points_px=points, tick_points_px=points,
            axis_endpoints_px=(points[0], points[-1]),
            reprojection_error_px=best.residual,
            interval_residuals_px=tuple(float(value) for value in best.interval_residuals),
            calibration_uncertainty=best.uncertainty,
            warnings=("Ruler calibration assumes the marks and lesion share the same image plane.",),
        )

    @staticmethod
    def _from_manual(known_object_px: Optional[float], known_object_mm: Optional[float]) -> ScaleCalibration:
        if not known_object_px or not known_object_mm or known_object_mm <= 0:
            return ScaleCalibration(method="manual")
        valid = bool(known_object_px >= 10.0)
        return ScaleCalibration(
            pixels_per_mm=known_object_px / known_object_mm if valid else None,
            method="manual", confidence=0.99,
            reference_type="manual", reference_diameter_px=known_object_px,
            reference_diameter_mm=known_object_mm, detected=True,
            calibration_valid=valid,
            validation_reason=(
                "valid manually supplied reference measurement"
                if known_object_px >= 10.0 else "manual reference is below the minimum measurable pixel size"
            ),
        )
