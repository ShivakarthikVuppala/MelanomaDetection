"""
Feature Extraction Base & Registry
====================================

Abstract base class for feature extractors with a registry pattern
that allows D/E features to be added in later phases via a simple
decorator without modifying existing code.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Type

import numpy as np


@dataclass
class FeatureResult:
    """Standardized output from a feature extractor."""
    name: str                          # e.g., "asymmetry"
    score_numeric: float               # normalized 0.0–1.0
    score_label: str                   # e.g., "High", "Irregular", "Multiple"
    details: Dict = field(default_factory=dict)  # algorithm-specific metadata


class FeatureExtractor(ABC):
    """
    Abstract base class for all feature extractors.

    Subclasses must implement `extract()` which takes the original
    image and binary mask, and returns a FeatureResult.
    """

    @abstractmethod
    def extract(self, image: np.ndarray, mask: np.ndarray) -> FeatureResult:
        """
        Extract a clinical feature from the lesion.

        Args:
            image: Original RGB image (H, W, 3), uint8.
            mask: Binary lesion mask (H, W), uint8, values 0 or 1.

        Returns:
            FeatureResult with numeric score, label, and details.
        """
        ...


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
_REGISTRY: Dict[str, Type[FeatureExtractor]] = {}


def register_feature(name: str):
    """
    Decorator to register a feature extractor.

    Usage:
        @register_feature("asymmetry")
        class AsymmetryExtractor(FeatureExtractor):
            ...

    In later phases, adding D/E features is just:
        @register_feature("diameter")
        class DiameterExtractor(FeatureExtractor):
            ...
    """
    def decorator(cls: Type[FeatureExtractor]):
        _REGISTRY[name] = cls
        return cls
    return decorator


def get_registered_extractors() -> Dict[str, Type[FeatureExtractor]]:
    """Return all registered feature extractor classes."""
    return dict(_REGISTRY)


def get_extractor(name: str) -> Type[FeatureExtractor]:
    """Get a specific extractor class by name."""
    if name not in _REGISTRY:
        raise KeyError(
            f"Feature extractor '{name}' not registered. "
            f"Available: {list(_REGISTRY.keys())}"
        )
    return _REGISTRY[name]
