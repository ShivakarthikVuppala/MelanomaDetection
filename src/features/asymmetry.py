"""
Asymmetry Feature Extractor
=============================

Measures the symmetry of the lesion by splitting along principal
axes and computing the overlap difference.
"""

import numpy as np
import cv2

from .base import FeatureExtractor, FeatureResult, register_feature


@register_feature("asymmetry")
class AsymmetryExtractor(FeatureExtractor):
    """
    Computes lesion asymmetry using PCA-aligned axis splitting.

    Process:
        1. Compute centroid from mask moments
        2. PCA on mask pixel coordinates to find principal axes
        3. Rotate mask to align principal axis horizontally
        4. Split along major and minor axes
        5. XOR area / total area → asymmetry index (0–1)

    Args:
        low_threshold: Below this, asymmetry is "Low".
        high_threshold: Above this, asymmetry is "High".
    """

    def __init__(self, low_threshold: float = 0.15, high_threshold: float = 0.35):
        self.low_threshold = low_threshold
        self.high_threshold = high_threshold

    def extract(self, image: np.ndarray, mask: np.ndarray) -> FeatureResult:
        # Ensure binary mask
        binary = (mask > 0).astype(np.uint8)

        if binary.sum() == 0:
            return FeatureResult(
                name="asymmetry",
                score_numeric=0.0,
                score_label="Unknown",
                details={"error": "Empty mask"},
            )

        # 1. Compute centroid
        moments = cv2.moments(binary)
        cx = int(moments["m10"] / max(moments["m00"], 1e-8))
        cy = int(moments["m01"] / max(moments["m00"], 1e-8))

        # 2. PCA on mask coordinates
        coords = np.column_stack(np.where(binary > 0))  # (N, 2) — (row, col)
        coords_centered = coords - np.array([cy, cx])

        if len(coords) < 10:
            return FeatureResult(
                name="asymmetry",
                score_numeric=0.0,
                score_label="Unknown",
                details={"error": "Too few lesion pixels"},
            )

        cov = np.cov(coords_centered.T)
        eigenvalues, eigenvectors = np.linalg.eigh(cov)

        # Principal axis angle
        angle = np.degrees(np.arctan2(eigenvectors[1, 1], eigenvectors[0, 1]))

        # 3. Rotate mask to align principal axis
        H, W = binary.shape
        rotation_matrix = cv2.getRotationMatrix2D((cx, cy), angle, 1.0)
        rotated = cv2.warpAffine(binary, rotation_matrix, (W, H), flags=cv2.INTER_NEAREST)

        # 4. Split and compute asymmetry for both axes
        # Major axis (horizontal split through centroid)
        top_half = rotated[:cy, :]
        bottom_half = rotated[cy:, :]

        # Make same height for comparison
        min_h = min(top_half.shape[0], bottom_half.shape[0])
        if min_h > 0:
            top_cropped = top_half[-min_h:, :]
            bottom_cropped = bottom_half[:min_h, :]
            # Flip top half for comparison
            top_flipped = np.flipud(top_cropped)
            xor_major = np.logical_xor(top_flipped, bottom_cropped).sum()
            union_major = np.logical_or(top_flipped, bottom_cropped).sum()
            asym_major = xor_major / max(union_major, 1)
        else:
            asym_major = 0.0

        # Minor axis (vertical split through centroid)
        left_half = rotated[:, :cx]
        right_half = rotated[:, cx:]

        min_w = min(left_half.shape[1], right_half.shape[1])
        if min_w > 0:
            left_cropped = left_half[:, -min_w:]
            right_cropped = right_half[:, :min_w]
            left_flipped = np.fliplr(left_cropped)
            xor_minor = np.logical_xor(left_flipped, right_cropped).sum()
            union_minor = np.logical_or(left_flipped, right_cropped).sum()
            asym_minor = xor_minor / max(union_minor, 1)
        else:
            asym_minor = 0.0

        # 5. Average asymmetry
        asym_index = float((asym_major + asym_minor) / 2.0)

        # 6. Classify
        if asym_index < self.low_threshold:
            label = "Low"
        elif asym_index < self.high_threshold:
            label = "Moderate"
        else:
            label = "High"

        return FeatureResult(
            name="asymmetry",
            score_numeric=round(asym_index, 4),
            score_label=label,
            details={
                "asymmetry_major_axis": round(float(asym_major), 4),
                "asymmetry_minor_axis": round(float(asym_minor), 4),
                "principal_angle_deg": round(float(angle), 2),
                "centroid": [cx, cy],
            },
        )
