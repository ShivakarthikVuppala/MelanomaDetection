"""Measure repeated ruler strokes in image coordinates, without object models.

Physical units deliberately do not enter this module. A row of marks supplies
a pixel interval; its millimetre interval belongs to the acquisition device.
"""

from dataclasses import dataclass

import cv2
import numpy as np
from scipy.signal import find_peaks


@dataclass
class TickLattice:
    spacing: float
    positions: np.ndarray
    points: np.ndarray
    bbox: tuple[int, int, int, int]
    tangent: np.ndarray
    residual: float
    interval_residuals: np.ndarray
    confidence: float
    uncertainty: float


def _ink_image(image: np.ndarray, lesion_mask: np.ndarray | None):
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY) if image.ndim == 3 else image
    source_h, source_w = gray.shape
    ratio = min(1.0, 1600.0 / max(source_h, source_w))
    size = (max(1, round(source_w * ratio)), max(1, round(source_h * ratio)))
    gray = cv2.resize(gray, size, interpolation=cv2.INTER_AREA)
    # Local background subtraction preserves faint ink on different skin tones.
    # It also removes broad shadows and the filled interior of a lesion.
    kernel_size = max(9, int(round(min(size) * 0.025)) | 1)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    ink = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, kernel)
    high_pass = gray.astype(float) - cv2.GaussianBlur(gray, (3, 3), 0).astype(float)
    noise = float(np.median(np.abs(high_pass)))
    ink[ink < max(4.0, 4.0 * noise)] = 0

    if lesion_mask is not None:
        binary = (np.asarray(lesion_mask) > 0).astype(np.uint8)
        if binary.ndim != 2:
            raise ValueError("lesion_mask must be a two-dimensional mask")
        binary = cv2.resize(binary, size, interpolation=cv2.INTER_NEAREST)
        count, labels, stats, _ = cv2.connectedComponentsWithStats(binary, 8)
        if count > 1:
            # A raw model mask may also contain disconnected ruler ticks.
            # Exclude the lesion component, not every segmented object.
            largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
            if stats[largest, cv2.CC_STAT_AREA] < binary.size * 0.85:
                exclusion = (labels == largest).astype(np.uint8)
                exclusion = cv2.dilate(exclusion, np.ones((3, 3), np.uint8))
                ink[exclusion > 0] = 0
    return ink, np.array([source_w / size[0], source_h / size[1]], dtype=float)


def _row_proposals(ink: np.ndarray):
    """Use short parallel line segments to propose rows, even without a baseline.

    Segment edges only locate candidate strips. They are never treated as
    individual tick centres, which would count a thick stroke twice.
    """
    lines = cv2.createLineSegmentDetector(cv2.LSD_REFINE_STD).detect(ink)[0]
    if lines is None:
        return []
    lines = lines.reshape(-1, 2, 2).astype(float)
    vectors = lines[:, 1] - lines[:, 0]
    lengths = np.linalg.norm(vectors, axis=1)
    minimum = max(4.0, min(ink.shape) * 0.009)
    keep = (lengths >= minimum) & (lengths <= min(ink.shape) * 0.20)
    lines, vectors, lengths = lines[keep], vectors[keep], lengths[keep]
    angles = np.arctan2(vectors[:, 1], vectors[:, 0]) % np.pi
    tolerance = max(2.0, min(ink.shape) * 0.004)
    proposals = []
    rng = np.random.default_rng(0)

    for seed_angle in np.arange(0.0, np.pi, np.pi / 12):
        selected = np.abs(np.sin(angles - seed_angle)) <= np.sin(np.deg2rad(9))
        group = lines[selected]
        if len(group) < 6:
            continue
        group_lengths = lengths[selected]
        # Bound texture-heavy images without changing random state elsewhere.
        if len(group) > 400:
            indices = np.linspace(0, len(group) - 1, 400, dtype=int)
            group, group_lengths = group[indices], group_lengths[indices]
        group_angles = np.arctan2(group[:, 1, 1] - group[:, 0, 1], group[:, 1, 0] - group[:, 0, 0])
        angle = 0.5 * np.arctan2(np.mean(np.sin(2 * group_angles)), np.mean(np.cos(2 * group_angles)))
        normal = np.array([np.cos(angle), np.sin(angle)])
        tangent = np.array([normal[1], -normal[0]])
        endpoints = group.reshape(-1, 2)
        seeds = np.linspace(0, len(endpoints) - 1, min(32, len(endpoints)), dtype=int)
        hypotheses = [(endpoints[i], tangent) for i in seeds]
        # Pair endpoints to tolerate slight rotation/skew of the ruler axis
        # relative to its ticks. Requiring near-perpendicular ticks rejects
        # parallel hairs that happen to cross the same image region.
        for first, second in rng.integers(0, len(endpoints), size=(100, 2)):
            delta = endpoints[second] - endpoints[first]
            distance = float(np.linalg.norm(delta))
            if distance < max(30, minimum * 6):
                continue
            axis = delta / distance
            if abs(float(axis @ normal)) <= 0.16:
                hypotheses.append((endpoints[first], axis))

        for origin, axis in hypotheses:
            perpendicular = np.array([-axis[1], axis[0]])
            distances = np.abs((group - origin) @ perpendicular)
            supporting = np.min(distances, axis=1) <= tolerance
            if np.count_nonzero(supporting) < 6:
                continue
            supported = group[supporting]
            nearest = np.argmin(distances[supporting], axis=1)
            aligned = supported[np.arange(len(supported)), nearest]
            centre = np.mean(aligned, axis=0)
            _, _, vh = np.linalg.svd(aligned - centre, full_matrices=False)
            fitted_axis = vh[0]
            if fitted_axis[0] < 0 or (abs(fitted_axis[0]) < 1e-6 and fitted_axis[1] < 0):
                fitted_axis = -fitted_axis
            if abs(float(fitted_axis @ normal)) > 0.20:
                continue
            coordinates = np.sort((aligned - centre) @ fitted_axis)
            unique_count = 1 + int(np.sum(np.diff(coordinates) > 3.0))
            span = float(np.ptp(coordinates))
            if unique_count < 6 or span < max(25, minimum * 5):
                continue
            depth = float(np.median(group_lengths[supporting]))
            proposals.append((unique_count, centre, fitted_axis, coordinates[0], coordinates[-1], depth))

    proposals.sort(key=lambda item: item[0], reverse=True)
    selected = []
    for proposal in proposals:
        _, centre, axis, low, high, depth = proposal
        duplicate = False
        for _, other_centre, other_axis, other_low, other_high, other_depth in selected:
            perpendicular = np.array([-axis[1], axis[0]])
            along = float((other_centre - centre) @ axis)
            if (abs(float(axis @ other_axis)) > 0.998
                    and abs(float((other_centre - centre) @ perpendicular)) < max(3, min(depth, other_depth) * 0.45)
                    and min(high, other_high + along) > max(low, other_low + along)):
                duplicate = True
                break
        if not duplicate:
            selected.append(proposal)
        if len(selected) >= 24:
            break
    return selected


def _baseline_proposals(ink: np.ndarray):
    """Also sample long baselines when crossing hairs obscure tick endpoints."""
    binary = (ink >= 8).astype(np.uint8) * 255
    minimum = max(45, round(min(ink.shape) * 0.20))
    lines = cv2.HoughLinesP(binary, 1, np.pi / 720, threshold=max(30, minimum // 3),
                            minLineLength=minimum, maxLineGap=max(3, round(min(ink.shape) * 0.005)))
    if lines is None:
        return []
    lines = lines.reshape(-1, 2, 2).astype(float)
    lengths = np.linalg.norm(lines[:, 1] - lines[:, 0], axis=1)
    selected = []
    for index in np.argsort(lengths)[::-1]:
        line, length = lines[index], lengths[index]
        centre = line.mean(axis=0)
        axis = (line[1] - line[0]) / length
        if axis[0] < 0 or (abs(axis[0]) < 1e-6 and axis[1] < 0):
            axis = -axis
        normal = np.array([-axis[1], axis[0]])
        if any(abs(float(axis @ other[2])) > 0.998
               and abs(float((centre - other[1]) @ normal)) < 5 for other in selected):
            continue
        # Stay close to the baseline so short minor ticks remain visible even
        # when taller marks and oblique hairs cross the ruler.
        depth = max(6, min(ink.shape) * 0.008)
        selected.append((0, centre, axis, -length / 2, length / 2, depth))
        if len(selected) >= 10:
            break
    return selected


def _fit_lattice(positions: np.ndarray):
    """Fit an affine tick lattice with missing marks and a small outlier budget.

    Seeds come from observed gaps. Most fitted gaps must be adjacent divisions;
    a sparse harmonic or an arbitrary subset of texture cannot set the scale.
    """
    if len(positions) < 6:
        return None
    gaps = np.diff(positions)
    seeds = np.unique(np.round(gaps[(gaps >= 4) & (gaps <= np.ptp(positions) / 5)], 1))
    best = None
    for seed in seeds:
        tolerance = max(0.8, seed * 0.10)
        for phase in positions[:24]:
            indices = np.rint((positions - phase) / seed).astype(int)
            residuals = np.abs(positions - (phase + indices * seed))
            chosen = np.where(residuals <= tolerance)[0]
            if len(chosen) < 6:
                continue
            # Only one profile peak can represent a particular physical mark.
            unique_peaks = []
            for index in np.unique(indices[chosen]):
                members = chosen[indices[chosen] == index]
                unique_peaks.append(members[np.argmin(residuals[members])])
            chosen = np.asarray(unique_peaks, dtype=int)
            if len(chosen) < 6:
                continue
            spacing, intercept = np.polyfit(indices[chosen], positions[chosen], 1)
            error = positions[chosen] - (intercept + indices[chosen] * spacing)
            chosen = chosen[np.abs(error) <= tolerance]
            if len(chosen) < 6 or len(chosen) / len(positions) < 0.80:
                continue
            spacing, intercept = np.polyfit(indices[chosen], positions[chosen], 1)
            ticks = positions[chosen]
            tick_indices = indices[chosen]
            steps = np.diff(tick_indices)
            density = len(ticks) / (tick_indices[-1] - tick_indices[0] + 1)
            if (spacing < 4 or abs(spacing / seed - 1) > 0.15 or density < 0.75
                    or np.any(steps > 3) or np.mean(steps == 1) < 0.60):
                continue
            residual = float(np.sqrt(np.mean((ticks - (intercept + tick_indices * spacing)) ** 2)))
            interval_residuals = np.diff(ticks) - steps * spacing
            interval_rms = float(np.sqrt(np.mean(interval_residuals ** 2)))
            unit_gaps = np.diff(ticks) / steps
            # A single scalar cannot correct visible perspective distortion.
            if (residual > max(0.65, spacing * 0.065)
                    or interval_rms > max(1.0, spacing * 0.10)
                    or abs(np.mean(unit_gaps[:3]) - np.mean(unit_gaps[-3:])) > spacing * 0.12):
                continue
            score = len(ticks) * (1.0 - residual / spacing) * density
            if best is None or score > best[0]:
                best = (score, spacing, ticks, residual, interval_residuals, len(chosen) / len(positions))
    return best


def find_tick_lattices(image: np.ndarray, lesion_mask: np.ndarray | None = None) -> list[TickLattice]:
    """Return independently validated rows in original-image pixel coordinates."""
    ink, source_scale = _ink_image(image, lesion_mask)
    lattices = []
    proposals = _baseline_proposals(ink) + _row_proposals(ink)
    for _, origin, tangent, low, high, depth in proposals:
        normal = np.array([-tangent[1], tangent[0]])
        along = np.arange(np.floor(low) - 5, np.ceil(high) + 6, dtype=float)
        across = np.arange(2, max(6, round(depth)) + 1, dtype=float)
        for side in (-1, 1):
            points = (origin + along[None, :, None] * tangent
                      + (side * across[:, None, None]) * normal)
            sampled = cv2.remap(ink, points[:, :, 0].astype(np.float32), points[:, :, 1].astype(np.float32),
                                cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
            profile = np.mean(sampled, axis=0).astype(np.float32)
            profile = cv2.GaussianBlur(profile[None, :], (3, 1), 0.6).ravel()
            floor = float(np.percentile(profile, 20))
            amplitude = float(np.percentile(profile, 95)) - floor
            if amplitude < 5:
                continue
            peaks, _ = find_peaks(profile, distance=3, prominence=max(3, amplitude * 0.22),
                                  height=floor + max(4, amplitude * 0.22), width=0.6)
            positions = peaks.astype(float)
            # Sub-pixel centres of the intensity peaks, not their two edges.
            for index, peak in enumerate(peaks):
                left, centre, right = map(float, profile[peak - 1:peak + 2])
                denominator = left - 2 * centre + right
                if abs(denominator) > 1e-6:
                    positions[index] += np.clip(0.5 * (left - right) / denominator, -0.5, 0.5)
            fit = _fit_lattice(positions + along[0])
            if fit is None:
                continue
            _, spacing, ticks, residual, interval_residuals, coverage = fit
            axis_scale = float(np.linalg.norm(tangent * source_scale))
            tick_points = (origin + ticks[:, None] * tangent + side * depth / 2 * normal) * source_scale
            corners = np.array([origin + u * tangent + v * normal
                                for u in (ticks[0] - 3, ticks[-1] + 3)
                                for v in (-2 * side, (depth + 2) * side)]) * source_scale
            start = np.maximum(0, np.floor(np.min(corners, axis=0))).astype(int)
            end = np.minimum([image.shape[1], image.shape[0]], np.ceil(np.max(corners, axis=0))).astype(int)
            confidence = min(0.97, 0.55 + 0.025 * len(ticks)) * (1 - residual / spacing) * coverage
            lattices.append(TickLattice(
                spacing=float(spacing * axis_scale), positions=(ticks - ticks[0]) * axis_scale,
                points=tick_points, bbox=(int(start[0]), int(start[1]), int(end[0] - start[0]), int(end[1] - start[1])),
                tangent=tangent * source_scale / axis_scale, residual=residual * axis_scale,
                interval_residuals=interval_residuals * axis_scale, confidence=float(confidence),
                uncertainty=float(max(0.5, residual) / spacing),
            ))

    lattices.sort(key=lambda item: (len(item.positions), item.confidence), reverse=True)
    return lattices
