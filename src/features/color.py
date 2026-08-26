"""
Color Feature Extractor
========================

Analyzes color diversity within the lesion using LAB color space
K-Means clustering and dermatological color detection.
"""

import numpy as np
import cv2
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from .base import FeatureExtractor, FeatureResult, register_feature


@register_feature("color")
class ColorExtractor(FeatureExtractor):
    """
    Computes color diversity within the lesion region.

    Process:
        1. Mask out background → extract lesion pixels
        2. Convert to LAB color space
        3. K-Means clustering with silhouette-based k selection
        4. Count dominant clusters (>min_ratio representation)
        5. Detect dermatological colors

    Args:
        min_cluster_ratio: Minimum fraction of pixels for a cluster to count.
        max_clusters: Maximum number of clusters to try.
    """

    def __init__(self, min_cluster_ratio: float = 0.05, max_clusters: int = 6):
        self.min_cluster_ratio = min_cluster_ratio
        self.max_clusters = max_clusters

    # Standard dermatological color ranges in LAB space
    DERM_COLORS = {
        "light_brown": {"L": (40, 70), "A": (5, 25), "B": (15, 40)},
        "dark_brown": {"L": (15, 45), "A": (5, 25), "B": (10, 35)},
        "black": {"L": (0, 25), "A": (-10, 10), "B": (-10, 10)},
        "blue_gray": {"L": (30, 60), "A": (-10, 5), "B": (-20, -2)},
        "red": {"L": (30, 60), "A": (20, 50), "B": (5, 30)},
        "white": {"L": (75, 100), "A": (-5, 5), "B": (-5, 5)},
    }

    def extract(self, image: np.ndarray, mask: np.ndarray) -> FeatureResult:
        binary = (mask > 0).astype(np.uint8)

        if binary.sum() == 0:
            return FeatureResult(
                name="color",
                score_numeric=0.0,
                score_label="Unknown",
                details={"error": "Empty mask"},
            )

        # 1. Extract lesion pixels
        lesion_pixels = image[binary > 0]  # (N, 3) in RGB

        if len(lesion_pixels) < 50:
            return FeatureResult(
                name="color",
                score_numeric=0.0,
                score_label="Unknown",
                details={"error": "Too few lesion pixels"},
            )

        # 2. Convert to LAB
        # Reshape for cv2 color conversion (use float32 to get true CIELAB scale)
        pixels_rgb = lesion_pixels.reshape(1, -1, 3).astype(np.float32) / 255.0
        pixels_lab = cv2.cvtColor(pixels_rgb, cv2.COLOR_RGB2LAB)
        pixels_lab = pixels_lab.reshape(-1, 3).astype(np.float64)

        # 3. K-Means with optimal k via silhouette score
        best_k = 2
        best_silhouette = -1
        best_labels = None
        best_centers = None

        # Subsample for efficiency if >5000 pixels
        if len(pixels_lab) > 5000:
            indices = np.random.RandomState(42).choice(
                len(pixels_lab), 5000, replace=False
            )
            sample = pixels_lab[indices]
        else:
            sample = pixels_lab

        # K-Means requires at least k samples and k distinct observations.
        # Small or nearly uniform lesions are valid inputs, so cap the search
        # instead of allowing an avoidable exception to abort diagnosis.
        unique_count = len(np.unique(sample, axis=0))
        max_k = min(self.max_clusters, len(sample), unique_count)
        for k in range(2, max_k + 1):
            kmeans = KMeans(n_clusters=k, n_init=5, random_state=42, max_iter=100)
            labels = kmeans.fit_predict(sample)

            if len(set(labels)) < 2:
                continue

            if len(sample) <= k:
                continue
            sil = silhouette_score(sample, labels, sample_size=min(1000, len(sample)))

            if sil > best_silhouette:
                best_silhouette = sil
                best_k = k
                best_labels = labels
                best_centers = kmeans.cluster_centers_

        # 4. Count dominant clusters
        if best_labels is None:
            dominant_count = 1
        else:
            cluster_sizes = np.bincount(best_labels, minlength=best_k)
            cluster_ratios = cluster_sizes / cluster_sizes.sum()
            dominant_count = int((cluster_ratios >= self.min_cluster_ratio).sum())

        # 5. Color variance
        color_std = float(pixels_lab.std(axis=0).mean())

        # 6. Detect dermatological colors
        detected_colors = self._detect_derm_colors(best_centers if best_centers is not None else pixels_lab[:1])

        # 7. Classify
        if dominant_count <= 1:
            label = "Uniform"
            score = 0.0
        elif dominant_count == 2:
            label = "Dual Color"
            score = 0.4
        else:
            label = "Multiple Colors"
            score = min(1.0, dominant_count / max(self.max_clusters, 1))

        return FeatureResult(
            name="color",
            score_numeric=round(score, 4),
            score_label=label,
            details={
                "dominant_clusters": dominant_count,
                "optimal_k": best_k,
                "silhouette_score": round(float(best_silhouette), 4),
                "color_std_lab": round(color_std, 2),
                "detected_derm_colors": detected_colors,
            },
        )

    def _detect_derm_colors(self, centers: np.ndarray) -> list:
        """Check cluster centers against standard dermatological color ranges."""
        detected = []
        for color_name, ranges in self.DERM_COLORS.items():
            for center in centers:
                L, A, B = center
                if (ranges["L"][0] <= L <= ranges["L"][1] and
                    ranges["A"][0] <= A <= ranges["A"][1] and
                    ranges["B"][0] <= B <= ranges["B"][1]):
                    if color_name not in detected:
                        detected.append(color_name)
                    break
        return detected
