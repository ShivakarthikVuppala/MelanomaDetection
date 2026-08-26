"""
Lesion Locator — Independent Bounding Box Estimation
=====================================================

Multi-strategy lesion localization module that generates bounding boxes
for downstream segmentation models. Designed as an independent module that can be
upgraded (e.g., to a learned detector) without modifying downstream wrappers.

Strategies:
    1. Otsu thresholding on grayscale
    2. Adaptive thresholding for uneven illumination
    3. Color-space thresholding (LAB L-channel)

The best candidate is selected by contour area and compactness.
"""

from dataclasses import dataclass
from typing import Optional, List, Tuple

import cv2
import numpy as np


@dataclass
class BoundingBox:
    """Bounding box in pixel coordinates."""
    x_min: int
    y_min: int
    x_max: int
    y_max: int

    def to_list(self) -> list:
        return [self.x_min, self.y_min, self.x_max, self.y_max]

    def area(self) -> int:
        return max(0, self.x_max - self.x_min) * max(0, self.y_max - self.y_min)


class LesionLocator:
    """
    Multi-strategy lesion localization for dermoscopic images.

    Generates candidate bounding boxes using multiple thresholding
    strategies, then selects the best candidate based on contour
    properties (area, compactness, centrality).

    This module is independent of specific segmentation architectures and can be replaced with
    a learned detector (e.g., YOLOv8, DETR) in later phases without
    modifying downstream code.

    Args:
        bbox_padding: Fractional padding around the detected bbox (e.g., 0.10 = 10%).
        min_area_ratio: Minimum lesion area as fraction of total image area.
    """

    def __init__(self, bbox_padding: float = 0.10, min_area_ratio: float = 0.005):
        self.bbox_padding = bbox_padding
        self.min_area_ratio = min_area_ratio

    def locate(self, image: np.ndarray) -> BoundingBox:
        """
        Estimate the lesion bounding box from a dermoscopic image.

        Runs all strategies, scores candidates, and returns the best.

        Args:
            image: RGB image as numpy array (H, W, 3).

        Returns:
            BoundingBox with padded coordinates clamped to image bounds.
        """
        H, W = image.shape[:2]
        min_area = int(H * W * self.min_area_ratio)

        candidates = []

        # Strategy 1: Otsu thresholding on grayscale
        bbox = self._otsu_strategy(image, min_area)
        if bbox:
            candidates.append(("otsu", bbox))

        # Strategy 2: Adaptive thresholding
        bbox = self._adaptive_strategy(image, min_area)
        if bbox:
            candidates.append(("adaptive", bbox))

        # Strategy 3: LAB color-space L-channel
        bbox = self._lab_strategy(image, min_area)
        if bbox:
            candidates.append(("lab", bbox))

        # Select best candidate
        if not candidates:
            # Fallback: use center 80% of image
            pad_x, pad_y = int(W * 0.1), int(H * 0.1)
            best_bbox = BoundingBox(pad_x, pad_y, W - pad_x, H - pad_y)
        else:
            best_bbox = self._select_best(candidates, H, W)

        # Apply padding and clamp
        return self._pad_and_clamp(best_bbox, H, W)

    def _otsu_strategy(self, image: np.ndarray, min_area: int) -> Optional[BoundingBox]:
        """Otsu thresholding on grayscale image."""
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        return self._largest_contour_bbox(binary, min_area)

    def _adaptive_strategy(self, image: np.ndarray, min_area: int) -> Optional[BoundingBox]:
        """Adaptive thresholding for uneven illumination."""
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        binary = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, blockSize=51, C=10,
        )
        # Clean up noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
        return self._largest_contour_bbox(binary, min_area)

    def _lab_strategy(self, image: np.ndarray, min_area: int) -> Optional[BoundingBox]:
        """LAB L-channel thresholding (effective for pigmented lesions)."""
        lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
        l_channel = lab[:, :, 0]
        blurred = cv2.GaussianBlur(l_channel, (5, 5), 0)
        _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        return self._largest_contour_bbox(binary, min_area)

    def _largest_contour_bbox(
        self, binary: np.ndarray, min_area: int
    ) -> Optional[BoundingBox]:
        """Find the largest contour and return its bounding box."""
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        # Filter by minimum area and select largest
        valid = [c for c in contours if cv2.contourArea(c) >= min_area]
        if not valid:
            return None

        largest = max(valid, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest)
        return BoundingBox(x, y, x + w, y + h)

    def _select_best(
        self,
        candidates: List[Tuple[str, BoundingBox]],
        H: int,
        W: int,
    ) -> BoundingBox:
        """
        Score candidates and select the best bounding box.

        Scoring criteria:
            - Area: prefer larger bboxes (more likely to contain entire lesion)
            - Centrality: prefer bboxes closer to image center
            - Aspect ratio: prefer bboxes closer to square (typical for lesions)
        """
        center_x, center_y = W / 2, H / 2
        img_area = H * W
        best_score = -1
        best_bbox = candidates[0][1]

        for _, bbox in candidates:
            # Normalized area score (0-1)
            area_score = bbox.area() / img_area

            # Centrality score (0-1, higher = more centered)
            bbox_cx = (bbox.x_min + bbox.x_max) / 2
            bbox_cy = (bbox.y_min + bbox.y_max) / 2
            dist = ((bbox_cx - center_x) ** 2 + (bbox_cy - center_y) ** 2) ** 0.5
            max_dist = (center_x ** 2 + center_y ** 2) ** 0.5
            centrality_score = 1.0 - (dist / max_dist)

            # Aspect ratio score (1.0 = square)
            bw = max(bbox.x_max - bbox.x_min, 1)
            bh = max(bbox.y_max - bbox.y_min, 1)
            aspect = min(bw, bh) / max(bw, bh)

            # Weighted combination
            score = 0.4 * area_score + 0.35 * centrality_score + 0.25 * aspect

            if score > best_score:
                best_score = score
                best_bbox = bbox

        return best_bbox

    def _pad_and_clamp(self, bbox: BoundingBox, H: int, W: int) -> BoundingBox:
        """Add padding and clamp to image bounds."""
        bw = bbox.x_max - bbox.x_min
        bh = bbox.y_max - bbox.y_min
        pad_x = int(bw * self.bbox_padding)
        pad_y = int(bh * self.bbox_padding)

        return BoundingBox(
            x_min=max(0, bbox.x_min - pad_x),
            y_min=max(0, bbox.y_min - pad_y),
            x_max=min(W, bbox.x_max + pad_x),
            y_max=min(H, bbox.y_max + pad_y),
        )
