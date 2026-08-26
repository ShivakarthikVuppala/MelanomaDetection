"""
Border Feature Extractor
=========================

Measures the irregularity of the lesion boundary using circularity
and radial distance variance.
"""

import numpy as np
import cv2

from .base import FeatureExtractor, FeatureResult, register_feature


@register_feature("border")
class BorderExtractor(FeatureExtractor):
    """
    Computes border irregularity using contour analysis.

    Metrics:
        - Circularity: 4πA / P² (1.0 = perfect circle)
        - Edge roughness: std of radial distances from centroid

    Args:
        smooth_threshold: Above this circularity, border is "Smooth".
        irregular_threshold: Below this, border is "Highly Irregular".
    """

    def __init__(
        self,
        smooth_threshold: float = 0.85,
        irregular_threshold: float = 0.65,
    ):
        self.smooth_threshold = smooth_threshold
        self.irregular_threshold = irregular_threshold

    def extract(self, image: np.ndarray, mask: np.ndarray) -> FeatureResult:
        binary = (mask > 0).astype(np.uint8)

        if binary.sum() == 0:
            return FeatureResult(
                name="border",
                score_numeric=0.0,
                score_label="Unknown",
                details={"error": "Empty mask"},
            )

        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if not contours:
            return FeatureResult(
                name="border",
                score_numeric=0.0,
                score_label="Unknown",
                details={"error": "No contours found"},
            )

        # Use the largest contour
        contour = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour, closed=True)

        if perimeter == 0 or area == 0:
            return FeatureResult(
                name="border",
                score_numeric=0.0,
                score_label="Unknown",
                details={"error": "Degenerate contour"},
            )

        # Circularity: 4πA / P²
        circularity = (4.0 * np.pi * area) / (perimeter ** 2)
        circularity = min(circularity, 1.0)  # clamp numerical errors

        # Compactness: P² / A
        compactness = (perimeter ** 2) / area

        # Radial distance variance
        moments = cv2.moments(binary)
        cx = moments["m10"] / max(moments["m00"], 1e-8)
        cy = moments["m01"] / max(moments["m00"], 1e-8)

        contour_pts = contour.reshape(-1, 2).astype(np.float64)
        distances = np.sqrt((contour_pts[:, 0] - cx) ** 2 + (contour_pts[:, 1] - cy) ** 2)

        mean_radius = distances.mean()
        if mean_radius > 0:
            # Normalized roughness (coefficient of variation)
            roughness = float(distances.std() / mean_radius)
        else:
            roughness = 0.0

        # Classify based on circularity
        if circularity > self.smooth_threshold:
            label = "Smooth"
        elif circularity > self.irregular_threshold:
            label = "Moderately Irregular"
        else:
            label = "Highly Irregular"

        # Score: invert circularity so higher = more irregular (0-1)
        irregularity_score = 1.0 - circularity

        return FeatureResult(
            name="border",
            score_numeric=round(irregularity_score, 4),
            score_label=label,
            details={
                "circularity": round(float(circularity), 4),
                "compactness": round(float(compactness), 2),
                "edge_roughness": round(roughness, 4),
                "perimeter_px": round(float(perimeter), 1),
                "area_px": int(area),
            },
        )
