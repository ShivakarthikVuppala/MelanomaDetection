"""Typed models for longitudinal (E criterion) lesion comparison."""

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


class EvolutionComparisonResult(BaseModel):
    """Image-derived change measurements for two visits of one lesion.

    These values support clinical review. They are not diagnostic thresholds.
    Size changes remain relative to the submitted images unless a shared
    physical scale is supplied by a future capture workflow.
    """

    baseline_date: date
    followup_date: date
    interval_days: int = Field(ge=1)
    area_change_percent: Optional[float] = None
    diameter_change_percent: Optional[float] = None
    border_change_score: Optional[float] = Field(default=None, ge=0.0)
    color_change_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    color_lab_delta: Optional[float] = Field(default=None, ge=0.0)
    normalized_shape_overlap: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    reported_changes: List[str] = Field(default_factory=list)
    reported_symptoms: List[str] = Field(default_factory=list)
    reported_change: bool = False
    lesion_site: Optional[str] = Field(default=None, max_length=100)
    self_reported_prior_history: Optional[str] = Field(default=None, max_length=500)
    scale_available: bool = False
    comparison_confidence: str = Field(pattern="^(low|medium|high)$")
    quality_flags: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def followup_must_be_later(self):
        if self.followup_date <= self.baseline_date:
            raise ValueError("followup_date must be later than baseline_date")
        return self

    def to_rag_evolution(self) -> dict:
        """Convert to the evolution structure consumed by the RAG agent."""
        return {
            "reported_change": self.reported_change,
            "change_types": self.reported_changes,
            "timeframe_months": round(self.interval_days / 30.44, 1),
            "symptoms": self.reported_symptoms,
            "status": "longitudinal_image_comparison",
            "comparison": self.model_dump(mode="json"),
            "notes": (
                "Evolution metrics were calculated from baseline and follow-up "
                "images. They are decision-support measurements, not diagnostic thresholds."
                + (
                    " A self-reported prior clinical history was supplied; it is unverified."
                    if self.self_reported_prior_history else ""
                )
            ),
        }
