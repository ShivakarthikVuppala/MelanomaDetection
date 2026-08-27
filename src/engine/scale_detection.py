"""Reference-object detection and pixel-to-millimetre calibration."""

from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

from .metric_measurement import ReferenceCalibrator
from scipy.signal import find_peaks


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
               reference_key: Optional[str] = None,
               lesion_mask: Optional[np.ndarray] = None,
               aruco_marker_size_mm: Optional[float] = None,
               aruco_marker_id: Optional[int] = None,
               checkerboard_inner_corners: Optional[tuple[int, int]] = None,
               checkerboard_square_size_mm: Optional[float] = None) -> ScaleCalibration:
        method = (method or "none").strip().lower()
        if method in {"none", "off", "disabled"}:
            return ScaleCalibration(method="none", validation_reason="scale calibration disabled")
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
            return self._detect_ruler(image, known_length_mm=known_diameter_mm)

        # Auto mode must not stop at an unknown circle: try the ruler as well.
        unknown_circle = self._detect_circular(
            image, known_diameter_mm,
            reference_type=requested_reference_type,
            lesion_mask=lesion_mask,
        )
        if unknown_circle.detected and unknown_circle.pixels_per_mm:
            return unknown_circle
        ruler = self._detect_ruler(image, known_length_mm=known_diameter_mm)
        if ruler.detected:
            return ruler
        # An unmeasured Hough circle is not evidence that a known reference
        # object exists.  Do not expose an arbitrary artifact/lesion candidate
        # as the selected reference in auto mode.
        return ScaleCalibration(
            method="auto",
            reference_type="none",
            validation_reason=(
                "no verified reference object was found; physical measurement "
                "requires a validated object and known physical size"
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

    def _detect_ruler_geometric(
        self, image: np.ndarray, known_length_mm: Optional[float] = None,
    ) -> ScaleCalibration:
        """Detect the actual ruler plane, then fit its repeated tick lattice.

        The previous implementation searched only narrow image-border strips.
        On dermatoscope images that allowed the circular black frame/skin
        texture to win.  This implementation first finds a long dark ruler
        baseline anywhere in the frame, samples pixels on both sides of that
        line, and accepts ticks only when they form a coherent lattice.
        """
        source = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        source_h, source_w = source.shape[:2]
        scale = min(1.0, 1800.0 / max(source_h, source_w))
        gray = cv2.resize(source, (int(round(source_w * scale)), int(round(source_h * scale))), interpolation=cv2.INTER_AREA) if scale < 1 else source
        h, w = gray.shape[:2]
        edges = cv2.Canny(gray, 35, 110)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180.0, threshold=max(35, int(min(h, w) * 0.035)), minLineLength=max(80, int(max(h, w) * 0.22)), maxLineGap=max(12, int(min(h, w) * 0.012)))
        if lines is None:
            return ScaleCalibration(method="ruler", reference_type="ruler", validation_reason="no ruler baseline detected")

        candidates = []
        # The ruler is printed with near-black ink.  A high adaptive cutoff
        # (the former ``max(80, p08)`` rule) turns dark skin texture into fake
        # marks on this image, producing the 11.9 px double-edge lattice.
        # Cap the ink cutoff so the profile remains tied to printed ruler
        # evidence rather than the overall skin brightness.
        dark_cutoff = max(65, min(95, int(np.percentile(gray, 8))))
        dark = gray < dark_cutoff
        for raw_line in lines.reshape(-1, 4):
            x1, y1, x2, y2 = map(float, raw_line)
            direction = np.array([x2 - x1, y2 - y1], dtype=float)
            length = float(np.linalg.norm(direction))
            if length < max(80, int(max(h, w) * 0.22)):
                continue
            tangent = direction / length
            # Support is measured on the line itself; the true printed ruler
            # baseline has substantially more dark pixels than skin edges.
            samples = np.linspace(0, 1, max(50, int(length)), dtype=float)
            xs = np.clip(np.rint(x1 + samples * direction[0]).astype(int), 0, w - 1)
            ys = np.clip(np.rint(y1 + samples * direction[1]).astype(int), 0, h - 1)
            support = float(dark[ys, xs].mean())
            candidates.append((length * (0.35 + support), length, (x1, y1, x2, y2), tangent))
        if not candidates:
            return ScaleCalibration(method="ruler", reference_type="ruler", validation_reason="no sufficiently long ruler baseline detected")

        # Deduplicate overlapping Hough segments and retain the strongest few.
        # Prefer the longest coherent baseline.  Shorter Hough fragments can
        # have a slightly higher dark-pixel support because they coincide with
        # one printed mark, but they cannot establish the ruler scale.
        candidates.sort(reverse=True, key=lambda item: (item[1], item[0]))
        selected = []
        for candidate in candidates:
            _, length, line, tangent = candidate
            midpoint = np.array([(line[0] + line[2]) / 2, (line[1] + line[3]) / 2])
            if all(np.linalg.norm(midpoint - np.array([(s[2][0] + s[2][2]) / 2, (s[2][1] + s[2][3]) / 2])) > 0.08 * min(h, w) for s in selected):
                selected.append(candidate)
            if len(selected) >= 8:
                break

        best = None
        for _, length, line, tangent in selected:
            p0 = np.array([line[0], line[1]], dtype=float)
            normal = np.array([-tangent[1], tangent[0]], dtype=float)
            u = np.arange(int(round(length)) + 1, dtype=float)
            v = np.arange(-max(8, int(round(length * 0.065))), max(8, int(round(length * 0.065))) + 1, dtype=float)
            points = p0[None, None, :] + u[:, None, None] * tangent[None, None, :] + v[None, :, None] * normal[None, None, :]
            xx = np.clip(np.rint(points[:, :, 0]).astype(int), 0, w - 1)
            yy = np.clip(np.rint(points[:, :, 1]).astype(int), 0, h - 1)
            # Ignore the baseline band itself. Ticks normally extend to one
            # side of the ruler; combining both sides lets skin texture and
            # the ruler label create false peaks, so select the side with the
            # strongest regularity.
            side_profiles = []
            for side_sign in (-1, 1):
                side = (v * side_sign >= 4) & (v * side_sign <= max(8, int(round(length * 0.065))))
                candidate_profile = dark[yy[:, side], xx[:, side]].sum(axis=1).astype(np.float32)
                candidate_profile = cv2.GaussianBlur(candidate_profile.reshape(1, -1), (1, 5), 0).ravel()
                # A printed tick is several pixels wide at the bounded
                # working resolution.  Enforce a separation larger than its
                # two edges so one mark cannot become two lattice points.
                candidate_peaks, _ = find_peaks(candidate_profile, distance=max(6, int(round(length * 0.007))), prominence=max(1.0, float(np.percentile(candidate_profile, 65) * 0.08)), height=max(1.0, float(np.percentile(candidate_profile, 45))))
                candidate_gaps = np.diff(candidate_peaks).astype(float)
                usable_gaps = candidate_gaps[(candidate_gaps >= 3) & (candidate_gaps <= max(30, int(length * 0.08)))]
                if len(usable_gaps):
                    med_gap = float(np.median(usable_gaps))
                    regularity = int(np.sum(np.abs(usable_gaps - med_gap) <= max(1.5, med_gap * 0.20)))
                else:
                    regularity = 0
                side_profiles.append((regularity, candidate_profile, candidate_peaks))
            _, profile, peaks = max(side_profiles, key=lambda item: item[0])
            if len(peaks) < 6:
                continue
            gaps = np.diff(peaks).astype(float)
            gap_values = gaps[(gaps >= 3) & (gaps <= max(30, int(length * 0.08)))]
            if len(gap_values) < 4:
                continue
            # Search the physical interval directly.  Each candidate must
            # explain a unique, monotonic tick index; this prevents a
            # quadratic fit from absorbing arbitrary peaks or a long gap.
            best_inliers, best_fit, best_spacing, best_phase = [], None, None, 0.0
            # At the bounded 1800 px working scale, two physical ruler marks
            # closer than 4.5 px are unresolved edge structure, not separate
            # millimetre ticks. This blocks the old double-edge failure.
            gap_bins = np.arange(2.5, min(31.0, float(gap_values.max()) + 1.5), 0.5)
            gap_hist, gap_edges = np.histogram(gap_values, bins=gap_bins)
            mode_spacing = float((gap_edges[int(np.argmax(gap_hist))] + gap_edges[int(np.argmax(gap_hist)) + 1]) / 2.0)
            lower_spacing = max(4.5, mode_spacing - 1.25)
            upper_spacing = min(25.0, mode_spacing + 1.25)
            for spacing_candidate in np.arange(lower_spacing, upper_spacing + 0.01, 0.25):
                tolerance = max(1.0, spacing_candidate * 0.16)
                for phase in np.linspace(0.0, spacing_candidate, 16, endpoint=False):
                    indices = np.rint((peaks - phase) / spacing_candidate).astype(np.int64)
                    chosen = []
                    for index in np.unique(indices):
                        members = np.where(indices == index)[0]
                        chosen.append(members[np.argmin(np.abs(peaks[members] - (phase + index * spacing_candidate)))])
                    chosen = np.asarray(sorted(chosen), dtype=np.int64)
                    if len(chosen) < 6:
                        continue
                    lattice_index = indices[chosen].astype(float)
                    design = np.column_stack([np.ones(len(chosen)), lattice_index, lattice_index ** 2])
                    coeff, *_ = np.linalg.lstsq(design, peaks[chosen], rcond=None)
                    predicted = design @ coeff
                    residuals = np.abs(peaks[chosen] - predicted)
                    inliers = chosen[residuals <= tolerance]
                    if len(inliers) >= 6 and (len(inliers) > len(best_inliers) or (len(inliers) == len(best_inliers) and spacing_candidate > (best_spacing or 0))):
                        best_inliers, best_fit, best_spacing, best_phase = inliers, coeff, float(spacing_candidate), float(phase)
            if len(best_inliers) < 6 or best_fit is None:
                continue
            spacing = best_spacing
            lattice_index = np.rint((peaks[best_inliers] - best_phase) / spacing).astype(float)
            design = np.column_stack([np.ones(len(best_inliers)), lattice_index, lattice_index ** 2])
            fitted = design @ best_fit
            residual = float(np.sqrt(np.mean((peaks[best_inliers] - fitted) ** 2)))
            score = len(best_inliers) * (1.0 - min(residual / max(spacing, 1.0), 1.0))
            if best is None or score > best[0]:
                best = (score, spacing, residual, p0, tangent, normal, peaks[best_inliers], xx, yy, profile)
        if best is None:
            return ScaleCalibration(method="ruler", reference_type="ruler", validation_reason="no coherent ruler tick lattice detected")

        _, spacing, residual, p0, tangent, normal, ticks, xx, yy, profile = best
        # A metric ruler has 1 mm minor divisions only when that convention
        # is explicitly accepted. Unknown spacing is measured, never guessed
        # from image resolution.
        interval_mm = float(known_length_mm) if known_length_mm is not None else 1.0
        axis0 = p0 / scale
        axis1 = (p0 + tangent * (len(profile) - 1)) / scale
        tick_points = tuple(tuple(map(float, (p0 + tangent * float(t) - normal * 2.0) / scale)) for t in ticks)
        intervals = np.diff(ticks).astype(float)
        interval_multipliers = np.maximum(1.0, np.rint(intervals / max(spacing, 1e-9)))
        # Remove the quarter-pixel search-grid quantization.  Estimate the
        # base interval from the observed intervals after accounting for
        # legitimately missing marks.
        spacing = float(np.median(intervals / interval_multipliers))
        if abs(spacing - round(spacing)) <= 0.30:
            spacing = float(round(spacing))
        spacing_source = float(spacing / scale)
        interval_residuals = intervals - interval_multipliers * spacing
        # A valid calibration must explain the *individual* intervals, not
        # merely fit a few points after assigning arbitrary large gaps to
        # integer multiples.  Keep this tolerance below one sixth of a tick
        # so double edges and skin-texture peaks cannot become a metric scale.
        interval_tolerance = max(1.5, spacing * 0.15)
        interval_coverage = float(np.mean(np.abs(interval_residuals) <= interval_tolerance)) if len(interval_residuals) else 0.0
        interval_rms = float(np.sqrt(np.mean(interval_residuals ** 2))) if len(interval_residuals) else float("inf")
        expected_tick_count = max(1.0, (float(ticks[-1]) - float(ticks[0])) / max(spacing, 1e-9) + 1.0)
        tick_density = float(len(ticks) / expected_tick_count)
        bbox_x = int(max(0, np.min([p[0] for p in tick_points]) - 20))
        bbox_y = int(max(0, np.min([p[1] for p in tick_points]) - 40))
        bbox_x1 = int(min(source_w, np.max([p[0] for p in tick_points]) + 40))
        bbox_y1 = int(min(source_h, np.max([p[1] for p in tick_points]) + 40))
        confidence = float(np.clip((len(ticks) / 30.0) * (1.0 - residual / max(spacing, 1.0)) * interval_coverage * min(1.0, tick_density / 0.75), 0.0, 0.95))
        valid = bool(
            len(ticks) >= 6
            and spacing_source >= 5.0
            and residual <= max(1.5, spacing * 0.15)
            and interval_coverage >= 0.85
            and interval_rms <= max(1.5, spacing * 0.15)
            and tick_density >= 0.75
        )
        if not valid:
            confidence = min(confidence, 0.49)
        return ScaleCalibration(
            pixels_per_mm=spacing_source / interval_mm if valid else None,
            method="ruler", reference_type="ruler", confidence=confidence,
            reference_length_px=spacing_source, reference_length_mm=interval_mm,
            reference_bbox_px=(bbox_x, bbox_y, bbox_x1 - bbox_x, bbox_y1 - bbox_y),
            orientation="horizontal" if abs(tangent[0]) >= abs(tangent[1]) else "vertical",
            angle_degrees=float(np.degrees(np.arctan2(tangent[1], tangent[0]))),
            interval_mm=interval_mm, tick_positions_px=tuple(float((t / scale)) for t in ticks),
            tick_spacing_px=spacing_source, validated_tick_count=len(ticks),
            reference_points_px=tick_points, axis_endpoints_px=(tuple(map(float, axis0)), tuple(map(float, axis1))),
            tick_points_px=tick_points, reprojection_error_px=round(residual / max(scale, 1e-9), 4),
            calibration_uncertainty=round(min(1.0, residual / max(spacing, 1.0)), 5),
            interval_residuals_px=tuple(float(value / scale) for value in interval_residuals),
            detected=True, calibration_valid=bool(valid),
            validation_reason="valid ruler baseline and tick lattice" if valid else "ruler evidence is sparse/inconsistent; physical measurement withheld",
            warnings=("metric interval assumed as 1 mm from ruler minor divisions" if known_length_mm is None else "",),
        )

    def _detect_ruler(
        self,
        image: np.ndarray,
        known_length_mm: Optional[float] = None,
    ) -> ScaleCalibration:
        """Detect repeated ruler marks without assuming their physical spacing.

        Ruler ticks are better represented by a one-dimensional dark-pixel
        profile than by the most common Hough-line angle: hair and glare often
        produce more Hough lines than the ruler itself.  The profile is still
        constrained to border regions, and requires a repeated spacing pattern.
        When no interval is supplied, a validated metric ruler is interpreted
        using its 1 mm minor division; the conversion is still derived from
        the measured tick spacing in this image.
        """
        return self._detect_ruler_geometric(image, known_length_mm)

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
        height, width = gray.shape[:2]
        # Use thinner border strips (1/5) to reduce hair contamination
        strip_h = max(40, height // 5)
        strip_w = max(40, width // 5)
        strips = [
            (gray[:strip_h, :], (0, 0)),
            (gray[-strip_h:, :], (0, height - strip_h)),
            (gray[:, :strip_w], (0, 0)),
            (gray[:, -strip_w:], (width - strip_w, 0)),
        ]
        best = None
        for strip, (offset_x, offset_y) in strips:
            # Suppress hairs with morphological opening (horizontal kernel)
            # before thresholding so thin curved hairs are removed but short
            # straight ruler ticks survive.
            hair_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 7))
            cleaned = cv2.morphologyEx(strip, cv2.MORPH_OPEN, hair_kernel)
            # Also try adaptive threshold which handles varied backgrounds
            _, otsu_thresh = cv2.threshold(
                cleaned, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
            )
            adapt_thresh = cv2.adaptiveThreshold(
                cleaned, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV, 31, 8
            )
            # Combine: use whichever has less noise (fewer dark pixels)
            otsu_count = int((otsu_thresh > 0).sum())
            adapt_count = int((adapt_thresh > 0).sum())
            thresholded = otsu_thresh if otsu_count <= adapt_count else adapt_thresh
            dark = thresholded > 0
            row_counts = dark.sum(axis=1)
            col_counts = dark.sum(axis=0)
            horizontal_band_y = int(np.argmax(row_counts))
            vertical_band_x = int(np.argmax(col_counts))
            band_half = max(12, min(50, int(round(min(strip.shape) * 0.12))))
            profile_masks = (
                dark[max(0, horizontal_band_y - band_half):min(strip.shape[0], horizontal_band_y + band_half + 1), :],
                dark[:, max(0, vertical_band_x - band_half):min(strip.shape[1], vertical_band_x + band_half + 1)],
            )
            profile_offsets = (
                (0, max(0, horizontal_band_y - band_half)),
                (max(0, vertical_band_x - band_half), 0),
            )
            profiles = (profile_masks[0].sum(axis=0), profile_masks[1].sum(axis=1))
            for axis, profile in enumerate(profiles):
                profile_dark = profile_masks[axis]
                profile_offset_x, profile_offset_y = profile_offsets[axis]
                profile = profile.astype(np.float32)
                if profile.size < 20 or float(profile.max()) < 4.0:
                    continue
                profile = cv2.GaussianBlur(profile.reshape(1, -1), (1, 5), 0).ravel() if axis == 0 else cv2.GaussianBlur(profile.reshape(-1, 1), (5, 1), 0).ravel()
                # A ruler baseline can be dark across every column/row.  Only
                # retain peaks that rise materially above that baseline so its
                # two edges are not mistaken for repeated ticks.
                peak_floor = max(5.0, float(np.percentile(profile, 75)) * 1.25)
                # Suppress the two/three-pixel edges of one printed mark; a
                # true adjacent ruler mark must be farther apart than that.
                min_distance = max(5, int(round(min(height, width) * 0.003)))
                candidates = [
                    i for i in range(1, len(profile) - 1)
                    if profile[i] >= peak_floor
                    and profile[i] >= profile[i - 1]
                    and profile[i] >= profile[i + 1]
                ]
                selected = []
                for index in sorted(candidates, key=lambda i: profile[i], reverse=True):
                    if all(abs(index - previous) >= min_distance for previous in selected):
                        selected.append(index)
                selected = np.asarray(sorted(selected), dtype=np.float32)
                if selected.size < 4:
                    continue
                # Background hairs create isolated peaks.  Search for a
                # contiguous run of marks before measuring spacing so distant
                # unrelated peaks cannot inflate the variance.
                all_spacings = np.diff(selected)
                # Major ruler marks can be separated by several centimetres
                # in a downsampled phone image.  Keep a generous gap limit;
                # the spacing-consistency test below still rejects isolated
                # background peaks.
                run_boundaries = [0] + (np.where(all_spacings > 100.0)[0] + 1).tolist() + [selected.size]
                best_run = None
                for run_start, run_end in zip(run_boundaries[:-1], run_boundaries[1:]):
                    run_positions = selected[run_start:run_end]
                    if run_positions.size < 4:
                        continue
                    run_spacings = np.diff(run_positions)
                    run_median = float(np.median(run_spacings))
                    spacing_mad = float(np.median(np.abs(run_spacings - run_median)))
                    spacing_tolerance = max(
                        2.0,
                        min(run_median * 0.25, 3.0 * 1.4826 * spacing_mad),
                    )
                    run_close = np.abs(run_spacings - run_median) <= spacing_tolerance
                    run_consistency = float(run_close.mean()) * (
                        1.0 - min(float(np.std(run_spacings[run_close])) / max(run_median, 1.0), 1.0)
                    ) if np.any(run_close) else 0.0
                    run_score = int(run_close.sum()) * run_consistency
                    if best_run is None or run_score > best_run[0]:
                        best_run = (run_score, run_positions, run_spacings, run_close, run_median, run_consistency)
                if best_run is None:
                    continue
                _, selected, _, _, spacing_median, _ = best_run
                if not 3.0 <= spacing_median <= min(100.0, max(height, width) * 0.25):
                    continue
                spacing_mad = float(np.median(np.abs(np.diff(selected) - spacing_median)))
                spacing_tolerance = max(
                    2.0,
                    min(spacing_median * 0.25, 3.0 * 1.4826 * spacing_mad),
                )
                spacings = np.diff(selected)
                close = np.abs(spacings - spacing_median) <= spacing_tolerance
                if int(close.sum()) < 3:
                    continue
                consistency = float(close.mean()) * (
                    1.0 - min(float(np.std(spacings[close])) / max(spacing_median, 1.0), 1.0)
                )
                span = float(selected[-1] - selected[0])
                if consistency < 0.50 or span < max(3.0 * spacing_median, 15.0):
                    continue
                if axis == 0:
                    x0, x1 = max(0, int(selected[0]) - 2), min(strip.shape[1], int(selected[-1]) + 3)
                    ys, xs = np.where(profile_dark[:, x0:x1])
                    bbox_work = (x0 + offset_x, int(ys.min()) + offset_y + profile_offset_y,
                                 max(1, x1 - x0), max(1, int(ys.max() - ys.min() + 1))) if len(ys) else None
                else:
                    y0, y1 = max(0, int(selected[0]) - 2), min(strip.shape[0], int(selected[-1]) + 3)
                    ys, xs = np.where(profile_dark[y0:y1, :])
                    bbox_work = (int(xs.min()) + offset_x + profile_offset_x, y0 + offset_y,
                                 max(1, int(xs.max() - xs.min() + 1)), max(1, y1 - y0)) if len(xs) else None
                if bbox_work is None:
                    continue
                bx, by, bw, bh = bbox_work
                long_side, short_side = max(bw, bh), min(bw, bh)
                # Dermoscopic rulers typically sit flush against the image
                # border.  Only reject if the ruler is too small or not
                # elongated; do NOT reject for touching the border.
                if (
                    long_side < max(20, int(round(min(height, width) * 0.05)))
                    or short_side <= 0
                    or long_side / short_side < 2.0
                ):
                    continue
                score = int(close.sum()) * consistency
                # Fit a regular tick lattice to the inlier spacing.  The
                # lattice gives consumers a clean, validated list even when
                # a few individual marks are obscured by hair/glare.
                validated_ticks = np.asarray([], dtype=np.float32)
                for phase_source in selected:
                    phase = float((phase_source - selected[0]) % spacing_median)
                    first = float(selected[0] + phase)
                    grid = first + np.arange(
                        int(np.floor((selected[-1] - first) / spacing_median)) + 1,
                        dtype=np.float32,
                    ) * float(spacing_median)
                    matched = []
                    for grid_position in grid:
                        if np.min(np.abs(selected - grid_position)) <= spacing_tolerance:
                            matched.append(float(grid_position))
                    if len(matched) > len(validated_ticks):
                        validated_ticks = np.asarray(matched, dtype=np.float32)
                if validated_ticks.size < 4:
                    validated_ticks = selected.copy()
                if best is None or score > best[0]:
                    best = (
                        score, spacing_median, int(close.sum()), bbox_work,
                        consistency, axis,
                        offset_x if axis == 0 else offset_y,
                        validated_ticks.copy(),
                    )
        if best is None:
            return ScaleCalibration(method="ruler", reference_type="ruler", validation_reason="no repeated ruler marks detected")
        _, spacing, count, bbox_work, consistency, axis, tick_origin, selected_ticks = best
        spacing_source = float(spacing / resize_scale)
        tick_positions_source = tuple(
            float((position + tick_origin) / resize_scale)
            for position in selected_ticks
        )
        bbox = tuple(int(round(value / resize_scale)) for value in bbox_work)
        bbox = (
            max(0, bbox[0]), max(0, bbox[1]),
            min(source_width - max(0, bbox[0]), bbox[2]),
            min(source_height - max(0, bbox[1]), bbox[3]),
        )
        # A metric ruler normally has ten equally spaced minor divisions per
        # centimetre.  The detected spacing is therefore a *measured* 1 mm
        # interval, not a pixels-per-mm constant.  If a caller supplies a
        # different interval (for example a 5 mm reference bar), use that
        # explicitly instead.
        interval_mm = float(known_length_mm) if known_length_mm is not None else 1.0
        orientation = "horizontal" if axis == 0 else "vertical"
        angle_degrees = 0.0 if orientation == "horizontal" else 90.0
        # Estimate the long ruler axis locally.  Projection profiles still
        # work for small rotations, but correcting the measured spacing by
        # the cosine of this angle preserves physical accuracy and makes the
        # orientation explicit to callers.
        bx, by, bw, bh = bbox_work
        roi = gray[max(0, by - 3):min(height, by + bh + 4), max(0, bx - 3):min(width, bx + bw + 4)]
        edges = cv2.Canny(roi, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180.0, threshold=max(10, int(min(roi.shape) * 0.15)),
                                minLineLength=max(15, int(max(roi.shape) * 0.25)), maxLineGap=8)
        if lines is not None:
            line_angles = []
            for line in np.asarray(lines).reshape(-1, 4):
                x1, y1, x2, y2 = [float(value) for value in line]
                length = float(np.hypot(x2 - x1, y2 - y1))
                raw_angle = float(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
                normalized = ((raw_angle + 90.0) % 180.0) - 90.0
                if (axis == 0 and abs(normalized) <= 30.0) or (axis == 1 and abs(abs(normalized) - 90.0) <= 30.0):
                    line_angles.append((length, normalized))
            if line_angles:
                angle_degrees = max(line_angles, key=lambda item: item[0])[1]
                axis_delta = abs(angle_degrees) if axis == 0 else abs(abs(angle_degrees) - 90.0)
                spacing_source = float(spacing_source / max(float(np.cos(np.deg2rad(axis_delta))), 1e-6))
        orientation = "horizontal" if axis == 0 else "vertical"
        if known_length_mm is None:
            return ScaleCalibration(
                method="ruler", reference_type="ruler", reference_length_px=spacing_source,
                reference_length_mm=interval_mm, interval_mm=interval_mm,
                reference_bbox_px=bbox, confidence=min(count / 15.0, 0.80) * consistency,
                orientation=orientation, angle_degrees=angle_degrees,
                tick_positions_px=tick_positions_source, tick_spacing_px=spacing_source,
                validated_tick_count=len(tick_positions_source),
                detected=True, calibration_valid=True,
                pixels_per_mm=spacing_source / interval_mm,
                validation_reason=(
                    "metric ruler minor-tick interval inferred as 1 mm from repeated, "
                    "uniform subdivisions; confirm the physical ruler markings when precision is critical"
                ),
            )
        valid = spacing_source >= 5.0 and count >= 3 and consistency >= 0.50 and known_length_mm > 0
        return ScaleCalibration(
            pixels_per_mm=spacing_source / known_length_mm if valid else None,
            method="ruler", confidence=min(count / 15.0, 0.80) * consistency,
            reference_type="ruler", reference_length_px=spacing_source,
            reference_length_mm=known_length_mm, interval_mm=known_length_mm,
            reference_bbox_px=bbox, orientation=orientation,
            angle_degrees=angle_degrees,
            tick_positions_px=tick_positions_source, tick_spacing_px=spacing_source,
            validated_tick_count=len(tick_positions_source),
            detected=True, calibration_valid=bool(valid),
            validation_reason=(
                "valid ruler interval calibration"
                if valid else "ruler interval was too small or inconsistent to calibrate reliably"
            ),
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
