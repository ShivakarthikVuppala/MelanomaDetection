"""Reference-object detection and pixel-to-millimetre calibration."""

from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np


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
               lesion_mask: Optional[np.ndarray] = None) -> ScaleCalibration:
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
