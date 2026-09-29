"""
Evolution Feature Extractor
===========================

Processes patient or clinical reported evolution (E in ABCDE).
Since static 2D images capture a single point in time,
the E criterion incorporates longitudinal change metadata.
"""

import numpy as np

from .base import FeatureExtractor, FeatureResult, register_feature


@register_feature("evolution")
class EvolutionExtractor(FeatureExtractor):
    """
    Processes patient or clinical reported evolution (E in ABCDE).
    Since static 2D images capture a single point in time,
    the E criterion incorporates longitudinal change metadata.

    Args:
        evolution_history: Optional dictionary containing clinical history.
    """

    def __init__(
        self,
        evolution_history: dict = None,
        **kwargs
    ):
        self.evolution_history = evolution_history

    def format_evolution_status(
        self,
        evolution_history: dict = None
    ) -> dict:
        """
        Processes patient or clinical reported evolution (E in ABCDE).
        """
        if not evolution_history:
            return {
                "reported_change": None,
                "status": "unavailable",
                "notes": "Evolution is unavailable without patient/clinical longitudinal history."
            }

        return {
            "reported_change": bool(evolution_history.get("reported_change", False)),
            "change_types": evolution_history.get("change_types", []),
            "timeframe_months": evolution_history.get("timeframe_months", None),
            "symptoms": evolution_history.get("symptoms", []),
            "notes": evolution_history.get("notes", "Longitudinal change reported by patient/clinician.")
        }

    def extract(self, image: np.ndarray, mask: np.ndarray) -> FeatureResult:
        evolution = self.format_evolution_status(self.evolution_history)
        
        reported_change = evolution.get("reported_change", False)
        
        # Calculate a pseudo-score based on reported change
        score_numeric = 1.0 if reported_change else 0.0
        score_label = "Evolving" if reported_change else "Unavailable" if evolution["status"] == "unavailable" else "No reported evolution"
        
        return FeatureResult(
            name="evolution",
            score_numeric=score_numeric,
            score_label=score_label,
            details=evolution,
        )
