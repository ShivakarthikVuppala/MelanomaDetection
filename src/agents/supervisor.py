"""Supervisor Agent implementing an observe -> decide -> act workflow loop."""
from __future__ import annotations
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional, Tuple
import yaml
from .clinical_context import ClinicalContextAgent
from .evidence import EvidenceAgent
from .report import ReportAgent
from .state import CaseState
from .vision import VisionAgent

class SupervisorAgent:
    name = "supervisor"
    def __init__(self, config_path: str = "config.yaml", *, vision: Any = None, clinical: Any = None, evidence: Any = None, report: Any = None):
        self.config_path = config_path
        with open(config_path, encoding="utf-8") as file: self.config = yaml.safe_load(file) or {}
        supervisor = self.config.get("supervisor", {})
        self.confidence_threshold = float(supervisor.get("classification_confidence_threshold", 70.0)) / 100.0
        self.max_steps = int(supervisor.get("max_supervisor_steps", 12))
        self.vision, self.clinical = vision or VisionAgent(config_path), clinical or ClinicalContextAgent()
        self.evidence, self.report = evidence or EvidenceAgent(int(self.config.get("evidence", {}).get("max_retrieval_cycles", 3))), report or ReportAgent(self.config.get("report", {}))
    def run(self, image_path: str, analysis_id: Optional[str] = None, save_mask: bool = True, scale_method: str = "auto", scale_reference_mm: Optional[float] = None, scale_reference_key: Optional[str] = None, clinical_context: Optional[Dict[str, Any]] = None) -> CaseState:
        analysis_id = analysis_id or f"{Path(image_path).stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        state = CaseState(analysis_id=analysis_id, image_path=str(image_path), status="running")
        for _ in range(self.max_steps):
            action, reason = self.choose_next_action(state)
            state.record(self.name, action, "selected", reason)
            if action == "finish_case":
                state.status = "completed" if not state.error_code else "failed"; state.record(self.name, action, "completed", "termination"); return state
            try:
                if action == "validate_image": self.vision.validate_image(state, self.config.get("quality", {}))
                elif action in {"classify_image", "segment_lesion", "calculate_measurements", "calibrate_scale", "run_gradcam"}: self.vision.analyze(state, save_mask=save_mask, scale_method=scale_method, scale_reference_mm=scale_reference_mm, scale_reference_key=scale_reference_key)
                elif action == "request_clinical_context": self.clinical.update(state, clinical_context)
                elif action == "retrieve_evidence": self.evidence.retrieve_evidence(state, reason)
                elif action == "generate_explanation": self.report.generate_explanation(state)
                elif action == "generate_report": self.report.generate_report(state)
                else: raise RuntimeError(f"Unsupported supervisor action: {action}")
            except Exception as exc:
                state.error_code, state.user_message = "workflow_action_failed", "The requested analysis action could not be completed."
                state.flags.append(f"{action} failed: {type(exc).__name__}")
                state.record(self.name, action, "failed", "tool_failure", {"exception": type(exc).__name__}, tool=True)
                state.status = "failed"; return state
        state.error_code, state.user_message, state.status = "supervisor_step_limit", "Analysis ended after reaching the safe workflow step limit.", "failed"
        return state
    def choose_next_action(self, state: CaseState) -> Tuple[str, str]:
        """Policy over observable state, intentionally not a fixed phase sequence."""
        if not state.image_quality: return "validate_image", "image_quality"
        if not state.image_quality.get("accepted"):
            state.error_code, state.user_message, state.retryable = "image_quality_insufficient", state.image_quality.get("reason"), True
            return "finish_case", "image_quality"
        if state.diagnosis_result is None: return "classify_image", "vision_required"
        if "E" not in state.abcde: return "request_clinical_context", "missing_evolution"
        if state.evidence_assessment.cycles_completed == 0: return "retrieve_evidence", "differential" if state.uncertainty.classification < self.confidence_threshold else "ABCDE"
        if not state.evidence_assessment.sufficient and state.evidence_assessment.cycles_completed < self.evidence.max_cycles: return "retrieve_evidence", "ABCDE"
        if state.explanation is None: return "generate_explanation", "validated_inputs_ready"
        if state.final_report is None: return "generate_report", "validated_synthesis_ready"
        return "finish_case", "report_ready"
