"""Deterministic input validation and image usability checks.

These checks are deliberately limited to detecting technically unusable input.
They are not a diagnostic model and do not infer lesion risk.
"""

from dataclasses import dataclass, field
from typing import List

import cv2
import numpy as np


@dataclass
class ImageQualityResult:
    accepted: bool
    reason: str = ""
    warnings: List[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)


def check_image_quality(
    image: np.ndarray,
    *,
    min_width: int = 256,
    min_height: int = 256,
    max_aspect_ratio: float = 4.0,
    min_laplacian_variance: float = 5.0,
    max_extreme_pixel_ratio: float = 0.98,
) -> ImageQualityResult:
    """Check image readability, dimensions, exposure and severe blur.

    The default blur value is a conservative engineering baseline for the
    variance-of-Laplacian metric, not a clinical cutoff. It should be
    calibrated against the application's validation set before deployment.
    The extreme-pixel limit is intended only to reject nearly blank frames.
    """
    if not isinstance(image, np.ndarray) or image.ndim != 3 or image.shape[2] != 3:
        return ImageQualityResult(False, "The image could not be read as a color image.")

    height, width = image.shape[:2]
    if width < min_width or height < min_height:
        return ImageQualityResult(
            False,
            "Image resolution is too low for reliable analysis. Please upload a clearer image.",
            metrics={"width": width, "height": height},
        )

    aspect = max(width / max(height, 1), height / max(width, 1))
    if aspect > max_aspect_ratio:
        return ImageQualityResult(
            False,
            "The image shape is too extreme for reliable analysis. Please upload a closer, well-framed image.",
            metrics={"width": width, "height": height, "aspect_ratio": round(aspect, 3)},
        )

    if not np.isfinite(image).all():
        return ImageQualityResult(False, "The image contains unreadable data. Please choose another image.")

    image_u8 = np.asarray(np.clip(image, 0, 255), dtype=np.uint8)
    gray = cv2.cvtColor(image_u8, cv2.COLOR_RGB2GRAY)
    laplacian_variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    # Whole-frame Laplacian variance is easily depressed by a large smooth
    # skin background even when the lesion itself is sharp.  Use a robust
    # local edge signal as a second condition for rejection.
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    edge_strength_p95 = float(np.percentile(cv2.magnitude(gx, gy), 95))
    dark_ratio = float(np.mean(gray <= 5))
    bright_ratio = float(np.mean(gray >= 250))
    extreme_ratio = max(dark_ratio, bright_ratio)

    metrics = {
        "width": width,
        "height": height,
        "aspect_ratio": round(aspect, 3),
        "laplacian_variance": round(laplacian_variance, 3),
        "edge_strength_p95": round(edge_strength_p95, 3),
        "dark_pixel_ratio": round(dark_ratio, 4),
        "bright_pixel_ratio": round(bright_ratio, 4),
    }

    if extreme_ratio >= max_extreme_pixel_ratio:
        return ImageQualityResult(
            False,
            "The image is almost completely dark or overexposed. Please retake it using even lighting.",
            metrics=metrics,
        )
    if laplacian_variance < min_laplacian_variance and edge_strength_p95 < 12.0:
        return ImageQualityResult(
            False,
            "The image appears too blurry for reliable analysis. Please keep the lesion sharply focused and retake it.",
            metrics=metrics,
        )

    warnings = []
    if dark_ratio > 0.20 or bright_ratio > 0.20:
        warnings.append("Lighting is uneven; measurements may be less reliable.")
    return ImageQualityResult(True, "Image accepted.", warnings=warnings, metrics=metrics)
