"""
Unified Feature Extractor
==========================

Composes all registered feature extractors (ABC) and provides
a single interface to extract all features from a lesion.
"""

from typing import Dict

import numpy as np

from .base import FeatureResult, get_registered_extractors

# Import feature modules to trigger @register_feature decorators
from . import asymmetry  # noqa: F401
from . import border     # noqa: F401
from . import color      # noqa: F401


class ABCFeatureExtractor:
    """
    Unified extractor that runs all registered feature extractors.

    Automatically discovers extractors registered via @register_feature.
    In later phases, D/E features will appear here without code changes.

    Args:
        config: Optional dict of feature-specific configuration.
               Keys should match registered feature names.
    """

    def __init__(self, config: dict = None):
        config = config or {}
        self.extractors = {}

        for name, cls in get_registered_extractors().items():
            # Pass feature-specific config if available
            feature_cfg = config.get(name, {})
            self.extractors[name] = cls(**feature_cfg)

    def extract_all(
        self, image: np.ndarray, mask: np.ndarray
    ) -> Dict[str, FeatureResult]:
        """
        Extract all registered features from the lesion.

        Args:
            image: Original RGB image (H, W, 3), uint8.
            mask: Binary lesion mask (H, W), uint8.

        Returns:
            Dict mapping feature name → FeatureResult.
        """
        results = {}
        for name, extractor in self.extractors.items():
            try:
                results[name] = extractor.extract(image, mask)
            except Exception as e:
                results[name] = FeatureResult(
                    name=name,
                    score_numeric=0.0,
                    score_label="Error",
                    details={"error": str(e)},
                )
        return results

    def list_features(self) -> list:
        """Return names of all registered feature extractors."""
        return list(self.extractors.keys())
