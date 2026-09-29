"""Architecture tests for the three-agent + Supervisor melanoma workflow.

These tests verify the corrected architecture:
- Three top-level agents: Vision, Evidence, Report
- Supervisor orchestrates the three agents
- Clinical context is an internal utility, not a top-level agent
- CaseState is the central contract
"""
from pathlib import Path
from types import SimpleNamespace

from src.agents.clinical_context import ClinicalContextAgent
from src.agents.evidence import EvidenceAgent
from src.agents.report import ReportAgent
from src.agents.state import CaseState, EvidenceRecord, Measurement
from src.agents.supervisor import SupervisorAgent
from src.agents.vision import VisionAgent


class FakeVision:
    def validate_image(self, state, quality_config):
        state.image_quality = {"accepted": True, "reason": ""}
        return state
    def analyze(self, state, **kwargs):
        state.diagnosis_result = SimpleNamespace(model_dump=lambda **_: {"validated": True})
        state.classification = {"prediction": "melanoma", "confidence": 62.0, "probabilities": {"melanoma": .62}}
        state.uncertainty.classification = .62
        state.pixel_measurements["diameter"] = Measurement(184, "pixels", False)
        state.physical_measurements["diameter"] = Measurement(None, "mm", False, reason_unavailable="no scale")
        state.abcde.update({key: SimpleNamespace(availability="available") for key in "ABCD"})
        return state


class Backend:
    def __init__(self): self.calls = []
    def hybrid_search(self, query):
        self.calls.append(query)
        return [{"text": "asymmetry border color diameter evolution clinical evidence", "metadata": {"source": "guideline", "title": "ABCDE"}, "rerank_score": .8}]


# ── Clinical Context (internal utility, not a top-level agent) ──

def test_clinical_context_never_fabricates_evolution():
    state = CaseState("id", "image.jpg")
    ClinicalContextAgent().update(state)
    assert state.abcde["E"].availability == "unavailable"
    assert state.pending_clinical_questions[0]["field"] == "evolution"
    assert "single_timepoint_capture" not in str(state.abcde["E"].raw)


# ── Evidence Agent ──

def test_evidence_agent_is_goal_driven_and_bounded():
    backend = Backend()
    state = CaseState("id", "image.jpg")
    state.abcde["E"] = SimpleNamespace(availability="unavailable")
    EvidenceAgent(max_cycles=2, backend=backend).retrieve_evidence(state, "ABCDE")
    assert state.evidence_assessment.sufficient
    assert len(backend.calls) >= 1
    assert all(item.trust_boundary == "UNTRUSTED_EVIDENCE" for item in state.evidence)


# ── Measurement safety ──

def test_pixel_measurement_cannot_be_promoted_to_mm_or_threshold():
    state = CaseState("id", "image.jpg")
    state.pixel_measurements["diameter"] = Measurement(184, "pixels", False)
    state.physical_measurements["diameter"] = Measurement(None, "mm", False, reason_unavailable="no calibration")
    state.abcde["E"] = SimpleNamespace(availability="unavailable")
    queries = EvidenceAgent(backend=Backend())._plan_queries(state, "measurement")
    assert not any("184" in query or "6 mm" in query for query in queries)
    assert state.physical_measurements["diameter"].value is None


# ── Vision Agent ──

def test_vision_maps_model_segmentation_gradcam_and_calibration_safely():
    result = SimpleNamespace(
        diagnosis=SimpleNamespace(prediction="melanoma", confidence=81.0),
        probabilities={"melanoma": .81},
        segmentation=SimpleNamespace(status="completed", area_px=100, perimeter_px=44, mask_path=None),
        measurements={"lesion": {"area_px": 100, "diameter_px": 184, "measurement_method": "feret"}, "asymmetry": {}, "border": {}, "color": {}},
        clinical_features={key: SimpleNamespace(score_label="observed") for key in ("asymmetry", "border", "color")},
        explainability=SimpleNamespace(model_dump=lambda: {"attention_inside_lesion": .9}),
        scale_calibration=SimpleNamespace(model_dump=lambda: {"calibration_valid": False, "calibration_reason": "no reference", "calibration_confidence": 0}),
    )
    engine = SimpleNamespace(diagnose=lambda *args, **kwargs: result)
    state = VisionAgent(engine=engine).analyze(CaseState("id", "image.jpg"), save_mask=False)
    assert state.classification["confidence"] == 81.0
    assert state.segmentation["mask_consistency"] == 1.0
    assert state.gradcam["alignment_reliable"]
    assert state.physical_measurements["diameter"].value is None
    assert "millimetre thresholds" in state.abcde["D"].interpretation


# ── Supervisor workflow ──

def test_supervisor_conditional_routing_and_report_output(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("quality: {}\nsupervisor: {classification_confidence_threshold: 70, max_supervisor_steps: 12}\nevidence: {max_retrieval_cycles: 2}\nreport: {}\n")
    supervisor = SupervisorAgent(str(config), vision=FakeVision(), evidence=EvidenceAgent(2, Backend()), report=ReportAgent())
    state = supervisor.run("image.jpg")
    actions = [event.action for event in state.agent_decisions]
    assert state.status == "completed"
    assert "request_clinical_context" in actions
    assert "retrieve_evidence" in actions
    assert state.final_report["physical_measurements"]["diameter"]["value"] is None
    assert state.final_report["pending_clinical_questions"]
    assert state.final_report["pipeline_metadata"]["trace"]


# ── Report Agent ──

def test_report_requires_validated_state_and_propagates_uncertainty():
    state = CaseState("id", "image.jpg")
    state.classification = {"prediction": "unknown", "confidence": 0}
    state.explanation = {"model_observation": "unavailable", "literature_context": "none", "uncertainty": ["missing evidence"]}
    ReportAgent().generate_report(state)
    assert state.final_report["uncertainty"]["final_synthesis"] == 1.0
    assert state.report_result.dashboard_payload["explanation"]["uncertainty"] == ["missing evidence"]


# ── Architecture correctness ──

def test_three_agent_architecture():
    """Verify the corrected architecture has exactly three top-level agents."""
    import src.agents as agents_module
    # __all__ should export exactly 4 names: Supervisor + 3 agents
    assert set(agents_module.__all__) == {"SupervisorAgent", "VisionAgent", "EvidenceAgent", "ReportAgent"}


def test_report_metadata_says_three_agent():
    """Report metadata should say three-agent, not five-agent."""
    state = CaseState("id", "image.jpg")
    state.classification = {"prediction": "test", "confidence": 50}
    state.explanation = {"model_observation": "test", "literature_context": "test", "uncertainty": []}
    ReportAgent().generate_report(state)
    assert "three-agent" in state.final_report["pipeline_metadata"]["architecture"]


def test_clinical_context_not_in_top_level_all():
    """ClinicalContextAgent should be importable but not in __all__."""
    import src.agents as agents_module
    # Should be importable (it's used internally by Supervisor)
    assert hasattr(agents_module, "ClinicalContextAgent")
    # But NOT in __all__ (it's not a top-level agent)
    assert "ClinicalContextAgent" not in agents_module.__all__


def test_supervisor_uses_clinical_context_internally():
    """Supervisor should use clinical context functionality internally."""
    import src.agents.supervisor as sup_module
    # The supervisor imports and uses ClinicalContextAgent as an internal utility
    assert hasattr(sup_module, "ClinicalContextAgent")
