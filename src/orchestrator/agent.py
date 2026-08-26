"""
Orchestrator Agent
====================

Coordinates the complete 4-phase melanoma diagnostic workflow:

    Phase 1: Diagnosis (Swin Transformer + SegFormer + OpenCV/scikit-image)
    Phase 2: Medical Evidence Retrieval (BGE + Qdrant)
    Phase 3: Explanation (Template-based + Grad-CAM validation)
    Phase 4: Report Generation (PDF + Dashboard)

Implements agentic decision-making:
- Evaluates intermediate outputs against reliability thresholds.
- Selectively re-invokes only the components that need refinement.
- Preserves reliable intermediate results across retries.
- Does not blindly rerun the entire pipeline.

Usage:
    orchestrator = OrchestratorAgent("config.yaml")
    state = orchestrator.run("path/to/image.jpg")
"""

import logging
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List

import yaml

logger = logging.getLogger(__name__)

SAFE_STAGE_MESSAGES = {
    "image_quality_insufficient": "Image quality is insufficient for reliable analysis. Please retake the image with better focus and even lighting.",
    "segmentation_failed": "The lesion could not be segmented reliably. Please upload a clearer, well-centered image or retry.",
    "classification_failed": "The image could not be classified. Please try again with a clearer image.",
    "measurement_failed": "Lesion measurements could not be calculated. Please try again with a clearer image.",
    "retrieval_failed": "Medical evidence could not be retrieved. The analysis can be retried.",
    "explanation_failed": "The explanation could not be generated. The model result requires review.",
    "report_generation_failed": "The report could not be generated. Please retry the analysis.",
}


# ---------------------------------------------------------------------------
# Workflow State
# ---------------------------------------------------------------------------

@dataclass
class PhaseStatus:
    """Tracks the status of a single pipeline phase."""
    name: str
    status: str = "pending"     # pending | running | completed | failed | skipped
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    retries: int = 0

    def start(self):
        self.status = "running"
        self.started_at = datetime.now()

    def complete(self):
        self.status = "completed"
        self.completed_at = datetime.now()

    def fail(self, error: str):
        self.status = "failed"
        self.completed_at = datetime.now()
        self.error = error

    def skip(self, reason: str):
        self.status = "skipped"
        self.error = reason


@dataclass
class WorkflowState:
    """Complete state of the multi-phase analysis pipeline."""
    analysis_id: str
    image_path: str

    # Phase statuses
    phases: Dict[str, PhaseStatus] = field(default_factory=lambda: {
        "diagnosis": PhaseStatus(name="Diagnosis"),
        "medical_evidence": PhaseStatus(name="Medical Evidence"),
        "explanation": PhaseStatus(name="Explanation"),
        "report": PhaseStatus(name="Report Generation"),
    })

    # Phase outputs (preserved across retries)
    diagnosis_result: Optional[Any] = None
    retrieved_evidence: Optional[List[Any]] = None
    explanation_result: Optional[Any] = None
    report_result: Optional[Any] = None

    # Agentic flags
    flags: List[str] = field(default_factory=list)
    overall_status: str = "pending"  # pending | running | completed | failed
    error_code: Optional[str] = None
    user_message: Optional[str] = None
    retryable: bool = False

    # Intermediate artifacts
    mask_saved_path: Optional[str] = None
    grad_cam_saved_path: Optional[str] = None


# ---------------------------------------------------------------------------
# Orchestrator Agent
# ---------------------------------------------------------------------------

class OrchestratorAgent:
    """
    Orchestrator Agent coordinating the multi-phase workflow.

    Initializes all phase agents from a config file and provides
    a single `.run(image_path)` interface that executes the complete
    pipeline with agentic quality gates.

    Args:
        config_path: Path to config.yaml.
    """

    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        self._thresholds = self.config.get("orchestrator", {})
        self._cls_confidence_threshold = self._thresholds.get(
            "classification_confidence_threshold", 70.0
        )
        self._seg_min_area = self._thresholds.get(
            "segmentation_min_area_px", 100
        )
        self._gradcam_threshold = self._thresholds.get(
            "gradcam_reliability_threshold", 0.30
        )
        self._max_retries = self._thresholds.get("max_retry_attempts", 1)

        # Lazy-initialized components
        self._diagnosis_engine = None
        self._retrieval_agent = None
        self._explainability_agent = None
        self._report_agent = None

    # ------------------------------------------------------------------
    # Lazy initialization (avoids loading heavy models if not needed)
    # ------------------------------------------------------------------

    def _get_diagnosis_engine(self):
        """Lazily initialize the Phase 1 CoreDiagnosisEngine."""
        if self._diagnosis_engine is None:
            from ..engine.engine import CoreDiagnosisEngine
            self._diagnosis_engine = CoreDiagnosisEngine(
                config_path=self._find_config_path()
            )
            logger.info("Phase 1: CoreDiagnosisEngine initialized")
        return self._diagnosis_engine

    def _get_retrieval_agent(self):
        """Lazily initialize the Phase 2 MedicalRetrievalAgent."""
        if self._retrieval_agent is None:
            from ..agents.medical_retrieval import MedicalRetrievalAgent
            retrieval_cfg = dict(self.config.get("retrieval", {}))
            project_root = Path(__file__).resolve().parents[2]
            if retrieval_cfg.get("knowledge_base"):
                retrieval_cfg["knowledge_base"] = str(project_root / retrieval_cfg["knowledge_base"])
            if retrieval_cfg.get("qdrant_path"):
                retrieval_cfg["qdrant_path"] = str(project_root / retrieval_cfg["qdrant_path"])
            for key in ("embedding_model_path", "embedding_cache_dir"):
                if retrieval_cfg.get(key):
                    retrieval_cfg[key] = str(project_root / retrieval_cfg[key])
            self._retrieval_agent = MedicalRetrievalAgent(retrieval_cfg)
            logger.info("Phase 2: MedicalRetrievalAgent initialized")
        return self._retrieval_agent

    def _get_explainability_agent(self):
        """Lazily initialize the Phase 3 ExplainabilityAgent."""
        if self._explainability_agent is None:
            from ..agents.explainability import ExplainabilityAgent
            expl_cfg = self.config.get("explainability", {})
            self._explainability_agent = ExplainabilityAgent(expl_cfg)
            logger.info("Phase 3: ExplainabilityAgent initialized")
        return self._explainability_agent

    def _get_report_agent(self):
        """Lazily initialize the Phase 4 ReportGenerationAgent."""
        if self._report_agent is None:
            from ..agents.report_generator import ReportGenerationAgent
            report_cfg = dict(self.config.get("report", {}))
            if report_cfg.get("output_dir"):
                report_cfg["output_dir"] = str(Path(__file__).resolve().parents[2] / report_cfg["output_dir"])
            self._report_agent = ReportGenerationAgent(report_cfg)
            logger.info("Phase 4: ReportGenerationAgent initialized")
        return self._report_agent

    def _find_config_path(self) -> str:
        """Resolve config.yaml path for sub-components."""
        candidates = [
            Path("config.yaml"),
            Path(__file__).resolve().parent.parent.parent / "config.yaml",
        ]
        for p in candidates:
            if p.exists():
                return str(p)
        return "config.yaml"

    # ------------------------------------------------------------------
    # Main pipeline execution
    # ------------------------------------------------------------------

    def run(
        self,
        image_path: str,
        analysis_id: Optional[str] = None,
        save_mask: bool = True,
        scale_method: str = "auto",
        scale_reference_mm: Optional[float] = None,
        scale_reference_key: Optional[str] = None,
    ) -> WorkflowState:
        """
        Execute the complete 4-phase diagnostic pipeline.

        Args:
            image_path: Path to the dermoscopic image.
            analysis_id: Optional analysis identifier.
            save_mask: Whether to save the segmentation mask.

        Returns:
            WorkflowState with all phase outputs.
        """
        if analysis_id is None:
            stem = Path(image_path).stem
            analysis_id = f"{stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        state = WorkflowState(
            analysis_id=analysis_id,
            image_path=str(image_path),
        )
        state.overall_status = "running"

        # Protect non-HTTP callers with the same deterministic input gate used
        # by the API. This is a usability check, not a diagnostic model.
        try:
            from PIL import Image
            import numpy as np
            from ..engine.image_quality import check_image_quality
            with Image.open(image_path) as image:
                quality = check_image_quality(
                    np.asarray(image.convert("RGB")),
                    **self.config.get("quality", {}),
                )
            if not quality.accepted:
                state.error_code = "image_quality_insufficient"
                state.user_message = quality.reason
                state.retryable = True
                state.phases["diagnosis"].fail(quality.reason)
                state.overall_status = "image_quality_insufficient"
                return state
        except Exception:
            logger.exception("Input quality validation failed for request %s", analysis_id)
            state.error_code = "image_decode_failed"
            state.user_message = "The image could not be read. Please choose another image."
            state.retryable = True
            state.phases["diagnosis"].fail(state.user_message)
            state.overall_status = "image_quality_insufficient"
            return state

        logger.info(f"=== Orchestrator: Starting analysis {analysis_id} ===")
        logger.info(f"Image: {image_path}")

        # ---- PHASE 1: DIAGNOSIS ----
        state = self._execute_phase1(state, save_mask, scale_method, scale_reference_mm, scale_reference_key)
        if state.phases["diagnosis"].status == "failed":
            state.overall_status = "failed"
            logger.error("Pipeline aborted: Phase 1 failed")
            return state

        # ---- AGENTIC QUALITY GATE ----
        state = self._quality_gate_phase1(state)

        # ---- PHASE 2: MEDICAL EVIDENCE ----
        state = self._execute_phase2(state)

        # ---- PHASE 3: EXPLANATION ----
        state = self._execute_phase3(state)

        # ---- AGENTIC: CHECK IF EXPLANATION NEEDS MORE EVIDENCE ----
        state = self._quality_gate_phase3(state)

        # ---- PHASE 4: REPORT GENERATION ----
        state = self._execute_phase4(state)

        # Final status
        failed_phases = [
            k for k, v in state.phases.items() if v.status == "failed"
        ]
        state.overall_status = "failed" if failed_phases else "completed"

        logger.info(f"=== Orchestrator: Analysis {analysis_id} {state.overall_status} ===")
        if state.flags:
            logger.info(f"Flags: {state.flags}")

        return state

    # ------------------------------------------------------------------
    # Phase 1: Diagnosis
    # ------------------------------------------------------------------

    def _execute_phase1(
        self, state: WorkflowState, save_mask: bool,
        scale_method: str = "auto",
        scale_reference_mm: Optional[float] = None,
        scale_reference_key: Optional[str] = None,
    ) -> WorkflowState:
        """Execute Phase 1: Classification + Segmentation + Feature Extraction."""
        phase = state.phases["diagnosis"]
        phase.start()
        logger.info("Phase 1: Running diagnosis pipeline...")

        try:
            engine = self._get_diagnosis_engine()
            result = engine.diagnose(
                state.image_path,
                save_mask=save_mask,
                request_id=state.analysis_id,
                scale_method=scale_method,
                scale_reference_mm=scale_reference_mm,
                scale_reference_key=scale_reference_key,
            )
            state.diagnosis_result = result

            if save_mask and result.segmentation.mask_path:
                state.mask_saved_path = result.segmentation.mask_path

            phase.complete()
            logger.info(
                f"Phase 1 complete: {result.diagnosis.prediction} "
                f"({result.diagnosis.confidence:.1f}%)"
            )

        except Exception as e:
            error_code = str(e) if str(e) in SAFE_STAGE_MESSAGES else "classification_failed"
            if "segmentation" in str(e).lower():
                error_code = "segmentation_failed"
            elif "measurement" in str(e).lower() or "contour" in str(e).lower():
                error_code = "measurement_failed"
            state.error_code = error_code
            state.user_message = SAFE_STAGE_MESSAGES[error_code]
            state.retryable = True
            phase.fail(state.user_message)
            logger.exception("Phase 1 failed for request %s", state.analysis_id)

        return state

    # ------------------------------------------------------------------
    # Phase 1 Quality Gate
    # ------------------------------------------------------------------

    def _quality_gate_phase1(self, state: WorkflowState) -> WorkflowState:
        """
        Agentic decision-making after Phase 1.

        Evaluates classification confidence, segmentation validity,
        measurement consistency, and Grad-CAM alignment.
        Does NOT rerun reliable components — only flags issues.
        """
        diag = state.diagnosis_result
        if diag is None:
            return state

        # 1. Classification confidence check
        confidence = diag.diagnosis.confidence
        if confidence < self._cls_confidence_threshold:
            flag = (
                f"Low classification confidence ({confidence:.1f}% < "
                f"{self._cls_confidence_threshold}%) — requesting broader "
                f"evidence retrieval in Phase 2"
            )
            state.flags.append(flag)
            logger.warning(flag)

        # 2. Segmentation validity check
        seg_area = diag.segmentation.area_px
        if seg_area is not None and seg_area < self._seg_min_area:
            flag = (
                f"Segmentation mask area ({seg_area} px) below minimum "
                f"threshold ({self._seg_min_area} px) — measurements derived "
                f"from this mask may be unreliable"
            )
            state.flags.append(flag)
            logger.warning(flag)

        # 3. Measurement consistency check
        border_meas = diag.measurements.get("border", {})
        circ = border_meas.get("circularity")
        area_from_meas = border_meas.get("area_px")
        if (circ is not None and area_from_meas is not None
                and seg_area is not None):
            # If measurement area and segmentation area diverge significantly
            if area_from_meas > 0 and abs(area_from_meas - seg_area) / area_from_meas > 0.1:
                flag = (
                    f"Measurement area ({area_from_meas}) inconsistent with "
                    f"segmentation area ({seg_area}) — image analysis may "
                    f"need review"
                )
                state.flags.append(flag)
                logger.warning(flag)

        # 4. Grad-CAM reliability check
        ail = getattr(diag.explainability, "attention_inside_lesion", None)
        if ail is not None and ail < self._gradcam_threshold:
            flag = (
                f"Grad-CAM attention primarily outside lesion "
                f"(AIL={ail:.3f} < {self._gradcam_threshold}) — "
                f"visual explanation marked as uncertified"
            )
            state.flags.append(flag)
            logger.warning(flag)

        return state

    # ------------------------------------------------------------------
    # Phase 2: Medical Evidence Retrieval
    # ------------------------------------------------------------------

    def _execute_phase2(self, state: WorkflowState) -> WorkflowState:
        """Execute Phase 2: Medical evidence retrieval."""
        phase = state.phases["medical_evidence"]

        if state.diagnosis_result is None:
            phase.skip("No diagnosis result available")
            return state

        phase.start()
        logger.info("Phase 2: Retrieving medical evidence...")

        try:
            agent = self._get_retrieval_agent()

            # Agentic: if classification confidence is low, request more evidence
            top_k = self.config.get("retrieval", {}).get("top_k", 5)
            extra_query = None

            low_conf_flag = any(
                "Low classification confidence" in f for f in state.flags
            )
            if low_conf_flag:
                top_k = min(top_k + 3, 10)  # Request more evidence
                extra_query = "differential diagnosis pigmented lesion uncertain classification"
                logger.info(
                    f"Agentic: increasing retrieval to top_k={top_k} "
                    f"due to low classification confidence"
                )

            evidence = agent.retrieve(
                state.diagnosis_result,
                extra_query=extra_query,
                top_k=top_k,
            )
            state.retrieved_evidence = evidence
            phase.complete()
            logger.info(f"Phase 2 complete: {len(evidence)} evidence items retrieved")

        except Exception:
            state.error_code = "retrieval_failed"
            state.user_message = SAFE_STAGE_MESSAGES["retrieval_failed"]
            state.retryable = True
            phase.fail(state.user_message)
            state.retrieved_evidence = []
            logger.exception("Phase 2 failed for request %s", state.analysis_id)

        return state

    # ------------------------------------------------------------------
    # Phase 3: Explanation
    # ------------------------------------------------------------------

    def _execute_phase3(self, state: WorkflowState) -> WorkflowState:
        """Execute Phase 3: Generate evidence-supported explanation."""
        phase = state.phases["explanation"]

        if state.diagnosis_result is None:
            phase.skip("No diagnosis result available")
            return state

        phase.start()
        logger.info("Phase 3: Generating explanation...")

        try:
            agent = self._get_explainability_agent()
            explanation = agent.explain(
                diagnosis_result=state.diagnosis_result,
                evidence=state.retrieved_evidence or [],
            )
            state.explanation_result = explanation

            # Propagate Grad-CAM flags
            if not explanation.grad_cam_reliable:
                if not any("Grad-CAM" in f for f in state.flags):
                    state.flags.append(
                        "Grad-CAM visual explanation is not certified as reliable"
                    )

            phase.complete()
            logger.info(
                f"Phase 3 complete: confidence={explanation.confidence_assessment}"
            )

        except Exception:
            state.error_code = "explanation_failed"
            state.user_message = SAFE_STAGE_MESSAGES["explanation_failed"]
            state.retryable = True
            phase.fail(state.user_message)
            logger.exception("Phase 3 failed for request %s", state.analysis_id)

        return state

    # ------------------------------------------------------------------
    # Phase 3 Quality Gate
    # ------------------------------------------------------------------

    def _quality_gate_phase3(self, state: WorkflowState) -> WorkflowState:
        """
        Agentic check after explanation:
        If evidence is insufficient for a reliable explanation,
        re-invoke Phase 2 with a broader query.
        """
        if state.explanation_result is None:
            return state

        evidence_count = len(state.retrieved_evidence or [])
        assessment = state.explanation_result.confidence_assessment
        phase2 = state.phases["medical_evidence"]

        # Only retry if Phase 2 completed but evidence was thin
        if (assessment in ("low", "requires-review")
                and evidence_count < 3
                and phase2.retries < self._max_retries):

            logger.info(
                "Agentic: explanation confidence is low with insufficient "
                "evidence — re-invoking Phase 2 retrieval with broader query"
            )
            phase2.retries += 1

            try:
                agent = self._get_retrieval_agent()
                extra = agent.retrieve(
                    state.diagnosis_result,
                    extra_query="dermoscopy clinical guidelines management risk factors",
                    top_k=5,
                )

                # Merge new evidence (deduplicate by title)
                existing_titles = {e.title for e in (state.retrieved_evidence or [])}
                for ev in extra:
                    if ev.title not in existing_titles:
                        state.retrieved_evidence.append(ev)

                logger.info(
                    f"Agentic: retrieved {len(extra)} additional evidence items, "
                    f"total now {len(state.retrieved_evidence)}"
                )

                # Re-run explanation with expanded evidence
                state = self._execute_phase3(state)

            except Exception as e:
                logger.warning(f"Agentic re-retrieval failed: {e}")

        return state

    # ------------------------------------------------------------------
    # Phase 4: Report Generation
    # ------------------------------------------------------------------

    def _execute_phase4(self, state: WorkflowState) -> WorkflowState:
        """Execute Phase 4: Generate final report (PDF + dashboard)."""
        phase = state.phases["report"]

        if state.diagnosis_result is None:
            phase.skip("No diagnosis result available")
            return state

        phase.start()
        logger.info("Phase 4: Generating report...")

        try:
            agent = self._get_report_agent()

            # Use a default explanation if Phase 3 failed
            explanation = state.explanation_result
            if explanation is None:
                from ..agents.explainability import ExplanationResult
                explanation = ExplanationResult(
                    summary="Explanation unavailable.",
                    reasoning=["Phase 3 did not produce an explanation."],
                    evidence_citations=[],
                    confidence_assessment="low",
                    grad_cam_reliable=False,
                    flags=["explanation_unavailable"],
                )

            report = agent.generate(
                diagnosis_result=state.diagnosis_result,
                evidence=state.retrieved_evidence or [],
                explanation=explanation,
                analysis_id=state.analysis_id,
            )
            state.report_result = report
            phase.complete()
            logger.info(
                f"Phase 4 complete: PDF={report.pdf_path or 'none'}"
            )

        except Exception:
            state.error_code = "report_generation_failed"
            state.user_message = SAFE_STAGE_MESSAGES["report_generation_failed"]
            state.retryable = True
            phase.fail(state.user_message)
            logger.exception("Phase 4 failed for request %s", state.analysis_id)

        return state
