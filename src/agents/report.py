"""Report Agent: turns validated CaseState into an evidence-grounded output."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional
from .state import CaseState

@dataclass
class ReportResult:
    dashboard_payload: Dict[str, Any]
    pdf_path: Optional[str] = None

class ReportAgent:
    name = "report"
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
    def generate_explanation(self, state: CaseState) -> CaseState:
        model, limitations = state.classification, list(state.flags)
        if state.abcde.get("E") and state.abcde["E"].availability == "unavailable": limitations.append("Evolution is unavailable because no longitudinal history was supplied.")
        if not state.physical_measurements.get("diameter") or not state.physical_measurements["diameter"].calibrated: limitations.append("Physical diameter is unavailable; no pixel value was interpreted as millimetres.")
        if not state.evidence_assessment.sufficient: limitations.append("Evidence retrieval did not cover all requested criteria.")
        state.explanation = {"model_observation": f"Model prediction: {model.get('prediction', 'unavailable')} ({model.get('confidence', 0):.1f}% confidence).", "literature_context": "Retrieved sources describe associations and do not establish a patient-specific diagnosis.", "uncertainty": limitations, "evidence_references": [{"title": e.title, "source": e.source} for e in state.evidence]}
        state.explanation_result = state.explanation
        state.uncertainty.final_synthesis = min(state.uncertainty.classification, state.uncertainty.evidence_sufficiency)
        state.record(self.name, "generate_explanation", "completed", "grounded_synthesis", tool=True)
        return state
    def generate_report(self, state: CaseState) -> CaseState:
        if state.explanation is None: raise ValueError("Report Agent requires a validated explanation")
        diagnosis = state.diagnosis_result.model_dump(mode="json") if state.diagnosis_result is not None else None
        payload = {"analysis_id": state.analysis_id, "diagnosis": diagnosis, "prediction": state.classification, "raw_measurements": {key: value.__dict__ for key, value in state.pixel_measurements.items()}, "physical_measurements": {key: value.__dict__ for key, value in state.physical_measurements.items()}, "abcde": {key: value.__dict__ for key, value in state.abcde.items()}, "clinical_context": state.clinical_context, "pending_clinical_questions": state.pending_clinical_questions, "evidence": [item.__dict__ for item in state.evidence], "evidence_assessment": state.evidence_assessment.__dict__, "uncertainty": state.uncertainty.__dict__, "explanation": state.explanation, "pipeline_metadata": {"architecture": "three-agent CaseState workflow", "trace": state.public_trace()}}
        # PDF is an optional rendering tool. Failure to render it must not
        # invalidate the structured report, which remains the source of truth.
        pdf_path = None
        if state.diagnosis_result is not None:
            try:
                from .explainability import ExplanationResult
                from .report_generator import ReportRenderer
                explanation = ExplanationResult(
                    summary=state.explanation["model_observation"],
                    reasoning=[state.explanation["literature_context"]], evidence_citations=[],
                    confidence_assessment="requires-review" if state.explanation["uncertainty"] else "moderate",
                    grad_cam_reliable=bool(state.gradcam.get("alignment_reliable")),
                    limitations=state.explanation["uncertainty"],
                )
                pdf_path = ReportRenderer(self.config).generate(
                    state.diagnosis_result, state.evidence, explanation, state.analysis_id
                ).pdf_path
            except Exception as exc:
                state.flags.append(f"PDF rendering unavailable: {type(exc).__name__}")
        state.final_report, state.report_result = payload, ReportResult(payload, pdf_path)
        state.record(self.name, "generate_report", "completed", "validated_report", tool=True)
        return state
