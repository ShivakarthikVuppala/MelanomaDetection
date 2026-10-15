"""Evidence Agent: hybrid RAG retrieval over medical literature with bounded
evidence-gap follow-up cycles.

Patient history and evolution are handled by the first-class ClinicalContextAgent;
the clinical methods below are retained only as backward-compatibility shims.
"""
from __future__ import annotations
from typing import Any, Dict, Iterable, List, Optional
from .state import CaseState, EvidenceAssessment, EvidenceRecord

class EvidenceAgent:
    name = "evidence"
    def __init__(self, max_cycles: int = 3, backend: Any = None, clinical_context: Any = None):
        self.max_cycles = max_cycles
        self._backend = backend
        # Backward-compatibility only: the Clinical Context Agent is now a first-class
        # top-level agent orchestrated directly. This retained instance and the shims
        # below keep older callers (and injected test doubles) working.
        from .clinical_context import ClinicalContextAgent
        self.clinical_context = clinical_context or ClinicalContextAgent()

    def update_clinical_context(self, state: CaseState, supplied: Dict[str, Any] | None = None) -> CaseState:
        """Deprecated shim — delegates to the first-class Clinical Context Agent."""
        return self.clinical_context.update(state, supplied)

    def assess_evolution(
        self,
        image_paths: List[str],
        timestamps: List[str] | None = None,
        config: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """Deprecated shim — delegates to the first-class Clinical Context Agent."""
        return self.clinical_context.assess_evolution(image_paths, timestamps, config)

    def _backend_instance(self):
        if self._backend is None:
            from rag_pipeline.agent import create_backend
            self._backend = create_backend()
        return self._backend
    def retrieve_evidence(self, state: CaseState, evidence_goal: str) -> CaseState:
        try:
            backend = self._backend_instance()
            current_completed = getattr(state.evidence_assessment, "cycles_completed", 0)
            is_targeted = bool(evidence_goal and evidence_goal not in {"ABCDE", "differential", "measurement", "clinical_guidelines"})
            queries = self._plan_queries(state, evidence_goal, backend, is_targeted=is_targeted)
            accumulated = list(state.evidence)
            documents = []
            for query in queries:
                documents.extend(backend.hybrid_search(query))
            cycle = current_completed + 1
            accumulated = self._deduplicate(accumulated, documents, evidence_goal, cycle)
            assessment = self._evaluate(state, accumulated, evidence_goal, cycle)
            state.record(
                self.name,
                "retrieve_evidence",
                "sufficient" if assessment.sufficient else "follow_up_required",
                "evidence_gap",
                {"cycle": cycle, "goal": evidence_goal, "missing": assessment.missing},
                tool=True,
            )
            state.evidence = state.retrieved_evidence = accumulated
            state.evidence_assessment = assessment
            state.uncertainty.retrieval = 1.0 if accumulated else 0.0
            state.uncertainty.evidence_sufficiency = 1.0 if assessment.sufficient else 0.35
            return state
        except Exception as e:
            state.record(self.name, "retrieve_evidence", "skipped", "backend_unavailable", {"error": str(e)}, tool=True)
            state.evidence = state.retrieved_evidence = []
            state.evidence_assessment = EvidenceAssessment(sufficient=False, missing=["A", "B", "C", "D", "E"], cycles_completed=self.max_cycles)
            state.uncertainty.retrieval = 0.0
            state.uncertainty.evidence_sufficiency = 0.0
            return state

    def _plan_queries(self, state: CaseState, goal: str, backend: Any = None, is_targeted: bool = False) -> List[str]:
        if is_targeted:
            return [goal]
        queries = ["ABCDE clinical guideline evidence for suspicious pigmented lesions"]
        if goal == "differential" or state.uncertainty.classification < 0.70:
            queries.append("differential diagnosis of uncertain pigmented skin lesion dermoscopy")
        if goal in {"ABCDE", "measurement", "clinical_guidelines"}:
            queries.extend(["melanoma asymmetry irregular border color variation evidence", "melanoma diameter criterion evidence calibrated measurement"])
        if state.abcde.get("E") and state.abcde["E"].availability == "unavailable":
            queries.append("clinical importance of evolution history in ABCDE melanoma assessment")
        # Run HyDE only on initial baseline cycle when no targeted query is provided
        if not is_targeted and backend is not None and hasattr(backend, "create_queries"):
            features = getattr(state.diagnosis_result, "clinical_features", {}) or {}
            metrics = {
                "asymmetry_index": getattr(features.get("asymmetry"), "score_numeric", 0.0),
                "border_irregularity_score": getattr(features.get("border"), "score_numeric", 0.0),
                "color_variation_score": getattr(features.get("color"), "score_numeric", 0.0),
                "diameter_pixels": state.pixel_measurements.get("diameter").value if state.pixel_measurements.get("diameter") else 0.0,
                "diameter_mm": state.physical_measurements.get("diameter").value if state.physical_measurements.get("diameter") else None,
                "calibration_valid": bool(state.physical_measurements.get("diameter") and state.physical_measurements["diameter"].calibrated),
                "evolution": state.clinical_context.get("evolution", {"status": "unavailable", "reported_change": None}),
            }
            try:
                queries.extend(backend.create_queries(metrics))
            except Exception:
                pass
        return list(dict.fromkeys(queries))
    def _evaluate(self, state: CaseState, evidence: List[EvidenceRecord], goal: str, cycle: int) -> EvidenceAssessment:
        required = ["A", "B", "C", "D", "E"] if (goal == "ABCDE" or len(goal) > 20) else [goal]
        corpus = " ".join((item.title + " " + item.content).lower() for item in evidence)
        terms = {"A": ("asymmetr",), "B": ("border", "margin"), "C": ("color", "colour", "pigment"), "D": ("diameter", "size"), "E": ("evolution", "change", "temporal")}
        covered = [key for key in required if key not in terms or any(term in corpus for term in terms[key])]
        missing = [key for key in required if key not in covered]
        return EvidenceAssessment(not missing, covered, missing, [f"clinical evidence for ABCDE {key} criterion melanoma" for key in missing], cycle)
    @staticmethod
    def _deduplicate(existing: List[EvidenceRecord], docs: Iterable[Dict[str, Any]], goal: str, cycle: int) -> List[EvidenceRecord]:
        seen, result = {(e.source, e.title, e.content[:120]) for e in existing}, list(existing)
        for index, doc in enumerate(docs):
            metadata = doc.get("metadata", {}) or {}
            record = EvidenceRecord(str(metadata.get("id", f"{cycle}-{index}")), str(metadata.get("title", metadata.get("source", "Medical reference"))), str(metadata.get("source", "Knowledge base")), str(doc.get("text", "")), float(doc.get("rerank_score", doc.get("rrf_score", doc.get("dense_score", 0.0)))), goal, cycle)
            key = (record.source, record.title, record.content[:120])
            if record.content and key not in seen: result.append(record); seen.add(key)
        return result
