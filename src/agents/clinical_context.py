"""Clinical Context Agent: asks for, normalizes, and never invents history."""
from __future__ import annotations
from typing import Any, Dict, List
from .state import ABCDEFeature, CaseState

class ClinicalContextAgent:
    name = "clinical_context"
    QUESTION_MAP = {"evolution": "Has the lesion changed in size, shape, color, elevation, or symptoms? If so, over what time period?"}

    def update(self, state: CaseState, supplied: Dict[str, Any] | None = None) -> CaseState:
        supplied = supplied or {}
        for key in ("evolution", "duration", "reported_size_change", "shape_change", "color_change", "symptoms", "history"):
            if key in supplied and supplied[key] is not None:
                state.clinical_context[key] = supplied[key]
        evolution = state.clinical_context.get("evolution")
        if evolution is None:
            state.abcde["E"] = ABCDEFeature("E", "unavailable", {}, limitation="Evolution cannot be determined from a single image; no history was supplied.")
            state.pending_clinical_questions = [{"field": "evolution", "question": self.QUESTION_MAP["evolution"]}]
            state.uncertainty.clinical_context = 0.0
            state.flags.append("Evolution (E) unavailable: patient history was not supplied.")
        else:
            state.abcde["E"] = ABCDEFeature("E", "available", {"reported_history": evolution}, "Patient-reported evolution recorded; it is not inferred from the image.")
            state.pending_clinical_questions = []
            state.uncertainty.clinical_context = 0.8
        state.record(self.name, "request_clinical_context", "updated", "missing_information", {"pending_fields": [q["field"] for q in state.pending_clinical_questions]})
        return state

    def missing_information(self, state: CaseState) -> List[Dict[str, str]]:
        return list(state.pending_clinical_questions)
