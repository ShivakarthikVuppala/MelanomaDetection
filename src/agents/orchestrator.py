"""Orchestrator Agent implementing an observe -> decide -> act workflow loop with LLM cognitive reasoning."""
from __future__ import annotations
import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import yaml

from .clinical_context import ClinicalContextAgent
from .evidence import EvidenceAgent
from .report import ReportAgent
from .state import CaseState
from .vision import VisionAgent
from .abcde_fusion import compute_fusion

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    name = "orchestrator"

    def __init__(
        self,
        config_path: str = "config.yaml",
        *,
        vision: Any = None,
        clinical: Any = None,
        evidence: Any = None,
        report: Any = None,
    ):
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except Exception:
            pass

        self.config_path = config_path
        with open(config_path, encoding="utf-8") as file:
            self.config = yaml.safe_load(file) or {}

        orchestrator = self.config.get("orchestrator", {})
        self.confidence_threshold = float(orchestrator.get("classification_confidence_threshold", 70.0)) / 100.0
        self.gradcam_threshold = float(orchestrator.get("gradcam_reliability_threshold", 0.30))
        self.max_retry_attempts = int(orchestrator.get("max_retry_attempts", 1))
        self.max_steps = int(orchestrator.get("max_supervisor_steps", orchestrator.get("max_orchestrator_steps", 12)))

        # Pre-resolve sub-configs so agents never reach into self.config directly
        self._explainability_cfg = self.config.get("explainability", {})
        self._quality_cfg = self.config.get("quality", {})
        self._abcde_weights = orchestrator.get("abcde_weights")

        # Merge report output config WITH explainability config so ReportAgent
        # always receives mode/llm_provider/model for EvidenceGroundedExplanationService
        report_cfg = {**self.config.get("report", {}), **self._explainability_cfg}
        self.vision = vision or VisionAgent(config_path)
        # Clinical Context is a first-class top-level agent (patient history + Evolution).
        self.clinical = clinical or ClinicalContextAgent()
        self.evidence = evidence or EvidenceAgent(int(self.config.get("evidence", {}).get("max_retrieval_cycles", 3)))
        self.report = report or ReportAgent(report_cfg)

        # Cognitive Agent Mind (LLM Reasoning)
        self._gemini_client = None
        self._llm_model = orchestrator.get("model", self._explainability_cfg.get("model", "gemini-2.5-flash"))
        self._llm_enabled = orchestrator.get("cognitive_reasoning", True)
        self._latest_thought: Optional[str] = None
        self._latest_mind_decision: Optional[Dict[str, Any]] = None

    def _get_llm_client(self):
        """Lazily initialize Google GenAI Client for cognitive deliberation."""
        if not self._llm_enabled:
            return None
        if self._gemini_client is not None:
            return self._gemini_client

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return None
        api_key = api_key.strip().strip('"').strip("'")
        if not api_key:
            return None

        try:
            from google import genai
            self._gemini_client = genai.Client(api_key=api_key)
            return self._gemini_client
        except Exception as err:
            logger.debug(f"Could not initialize GenAI Client for orchestrator: {err}")
            return None

    def _deliberate_with_mind(self, state: CaseState) -> Optional[Dict[str, Any]]:
        """
        Cognitive reasoning core of the Orchestrator.
        Uses Gemini to evaluate findings, identify clinical uncertainties,
        and formulate targeted evidence retrieval or stop criteria.
        """
        client = self._get_llm_client()
        if client is None:
            return None

        # Build clinical case observations
        diag = state.diagnosis_result
        pred = getattr(getattr(diag, "diagnosis", None), "prediction", "unknown") if diag else "unknown"
        conf = float(getattr(getattr(diag, "diagnosis", None), "confidence", 0.0) or 0.0) if diag else 0.0
        mel_prob = float(diag.probabilities.get("melanoma", 0.0)) if (diag and hasattr(diag, "probabilities")) else 0.0

        features = getattr(diag, "clinical_features", {}) or {}
        feat_summary = []
        for name in ("asymmetry", "border", "color", "diameter", "evolution"):
            f = features.get(name)
            if f:
                feat_summary.append(
                    f"{name.capitalize()}: {getattr(f, 'score_label', 'unknown')} "
                    f"(score: {getattr(f, 'score_numeric', 0.0):.2f})"
                )

        fusion = state.fusion_result
        fusion_summary = (
            f"Composite score: {fusion.composite_score:.2f}, Prediction: {fusion.prediction}"
            if fusion else "Not calculated"
        )

        evidence_titles = [f"'{e.title}' (rel: {e.relevance_score:.2f})" for e in state.evidence[:5]]
        cycles = state.evidence_assessment.cycles_completed
        max_c = self.evidence.max_cycles

        prompt = f"""You are the cognitive Orchestrator Agent for an AI Melanoma Diagnostic system.
You are in the Clinical Evidence Deliberation Phase.
Evaluate the diagnostic findings and determine if literature retrieval is needed or if evidence is sufficient to explain the case.

Patient & Diagnostic Findings:
- Model Prediction: {pred} (Confidence: {conf:.1f}%, Melanoma Probability: {mel_prob:.2f})
- Multimodal ABCDE Fusion: {fusion_summary}
- Clinical Features: {', '.join(feat_summary) if feat_summary else 'Extracted from image'}
- Attention Alignment: {state.uncertainty.classification:.2f}
- Evidence Cycles Completed: {cycles} of {max_c}
- Evidence Retrieved So Far: {', '.join(evidence_titles) if evidence_titles else 'None'}
- Clinical Context / Patient History: {state.clinical_context.get('patient_history', 'None provided')}

Guidelines for your decision:
1. If evidence cycles completed is 0, or if critical uncertainty/discrepancy exists between classifier and ABCD features and cycles < {max_c}:
   Choose action: "retrieve_evidence"
   Provide a targeted "evidence_query" addressing the specific diagnostic nuance (e.g. differential criteria, atypical presentation, specific ABCDE guidelines).
2. If the retrieved literature provides adequate clinical grounding for the findings, or cycles have exhausted:
   Choose action: "generate_explanation"
   Set "evidence_query": null

Respond in valid JSON only:
{{
  "thought": "<concise clinical reasoning explaining your observation and why you chose this action>",
  "action": "retrieve_evidence" or "generate_explanation",
  "reason": "<short label for the reason category>",
  "evidence_query": "<search query string or null>"
}}
"""
        try:
            print("\n[Orchestrator Mind] Invoking Gemini Cognitive Mind for case deliberation...", flush=True)
            resp = client.models.generate_content(
                model=self._llm_model,
                contents=prompt,
                config={"response_mime_type": "application/json"}
            )
            raw = (resp.text or "").strip()
            data = json.loads(raw)
            if isinstance(data, dict) and data.get("action") in {"retrieve_evidence", "generate_explanation"}:
                self._latest_mind_decision = data
                return data
        except Exception as exc:
            logger.debug(f"LLM deliberation error: {exc}")
            print(f"[Orchestrator Mind] Gemini deliberation error or fallback: {exc}", flush=True)
        return None

    @staticmethod
    def _round_safe(val: Any, n: int = 3) -> Optional[float]:
        try:
            return round(float(val), n) if val is not None else None
        except (ValueError, TypeError):
            return None

    def _format_case_state_json(self, state: CaseState, step_num: int) -> Dict[str, Any]:
        """Generate a structured, serializable JSON snapshot of the CaseState from the Orchestrator's perspective."""
        # 1. Quality evaluation
        iq = state.image_quality if isinstance(state.image_quality, dict) else {}
        quality_summary = {
            "evaluated": bool(state.image_quality),
            "accepted": iq.get("accepted"),
            "resolution": (
                f"{iq.get('width', 0)}x{iq.get('height', 0)}"
                if (iq.get("width") and iq.get("height"))
                else None
            ),
            "laplacian_variance": self._round_safe(iq.get("laplacian_variance"), 2),
            "rejection_reason": iq.get("reason"),
        }

        # 2. Vision and deep learning diagnosis
        diag = state.diagnosis_result
        if diag:
            diag_obj = getattr(diag, "diagnosis", None)
            prediction = getattr(diag_obj, "prediction", "unknown") if diag_obj else "unknown"
            confidence = getattr(diag_obj, "confidence", 0.0) if diag_obj else 0.0
            probs = getattr(diag, "probabilities", {}) or {}
            mel_prob = probs.get("melanoma")
            vision_summary = {
                "evaluated": True,
                "prediction": prediction,
                "confidence_pct": self._round_safe(confidence, 1),
                "melanoma_probability": self._round_safe(mel_prob, 4),
                "probabilities": {k: self._round_safe(v, 4) for k, v in probs.items()},
                "threshold": self._round_safe(getattr(diag, "classification_threshold", None), 4),
            }
        else:
            vision_summary = {
                "evaluated": False,
                "prediction": None,
                "confidence_pct": None,
                "melanoma_probability": None,
                "probabilities": {},
                "threshold": None,
            }

        # 3. Clinical ABCD feature extraction
        features = getattr(diag, "clinical_features", {}) or {} if diag else {}
        abcd_summary: Dict[str, Any] = {}
        for feat_name in ("asymmetry", "border", "color", "diameter", "evolution"):
            feat = features.get(feat_name)
            if feat is not None:
                abcd_summary[feat_name] = {
                    "score_label": getattr(feat, "score_label", "unknown"),
                    "score_numeric": self._round_safe(getattr(feat, "score_numeric", 0.0), 3),
                    "interpretation": getattr(feat, "interpretation", None),
                }
            else:
                abcd_summary[feat_name] = None

        # 4. Grad-CAM visual attention
        gcam = state.gradcam if isinstance(state.gradcam, dict) else {}
        gradcam_summary = {
            "evaluated": bool(state.gradcam),
            "attention_inside_lesion": self._round_safe(gcam.get("attention_inside_lesion"), 4),
            "alignment_reliable": gcam.get("alignment_reliable"),
            "retry_count": gcam.get("retry_count", 0),
            "saved_path": state.grad_cam_saved_path,
        }

        # 5. Multimodal ABCDE fusion
        fusion = state.fusion_result
        if fusion:
            fusion_summary = {
                "evaluated": True,
                "composite_score": self._round_safe(getattr(fusion, "composite_score", 0.0), 4),
                "prediction": getattr(fusion, "prediction", "unknown"),
                "weights_used": (
                    {k: self._round_safe(v, 3) for k, v in fusion.weights_used.items()}
                    if getattr(fusion, "weights_used", None)
                    else {}
                ),
                "component_scores": (
                    {k: self._round_safe(v, 4) for k, v in fusion.component_scores.items()}
                    if getattr(fusion, "component_scores", None)
                    else {}
                ),
            }
        else:
            fusion_summary = {
                "evaluated": False,
                "composite_score": None,
                "prediction": None,
                "weights_used": {},
                "component_scores": {},
            }

        # 6. Longitudinal evolution
        ev_ctx = state.clinical_context.get("evolution") if isinstance(state.clinical_context, dict) else None
        evolution_summary = {
            "historical_images_count": len(state.historical_images or []),
            "evaluated": ev_ctx is not None,
            "status": ev_ctx.get("status") if isinstance(ev_ctx, dict) else None,
            "confidence": self._round_safe(ev_ctx.get("confidence") if isinstance(ev_ctx, dict) else None, 3),
            "comparison": ev_ctx.get("comparison") if isinstance(ev_ctx, dict) else None,
        }

        # 7. Literature evidence & sufficiency
        ev_titles = [
            {"id": getattr(e, "id", str(idx)), "title": getattr(e, "title", "Article"), "relevance_score": self._round_safe(getattr(e, "relevance_score", 0.0), 3)}
            for idx, e in enumerate(state.evidence[:5])
        ]
        ev_assessment = getattr(state, "evidence_assessment", None)
        evidence_summary = {
            "cycles_completed": getattr(ev_assessment, "cycles_completed", 0) if ev_assessment else 0,
            "max_cycles": getattr(self.evidence, "max_cycles", 1),
            "is_sufficient": getattr(ev_assessment, "sufficient", False) if ev_assessment else False,
            "total_retrieved": len(state.evidence or []),
            "retrieved_articles": ev_titles,
        }

        # 8. Uncertainty signals
        unc = getattr(state, "uncertainty", None)
        uncertainty_summary = {
            "classification": self._round_safe(getattr(unc, "classification", 1.0), 3) if unc else 1.0,
            "segmentation": self._round_safe(getattr(unc, "segmentation", 1.0), 3) if unc else 1.0,
            "evidence_sufficiency": self._round_safe(getattr(unc, "evidence_sufficiency", 1.0), 3) if unc else 1.0,
        }

        # 9. Pipeline synthesis outputs
        outputs_summary = {
            "explanation_ready": bool(state.explanation),
            "final_report_ready": bool(state.final_report),
            "pdf_generated": bool(isinstance(state.final_report, dict) and state.final_report.get("pdf_url")),
        }

        # 10. Recent trace
        trace_events = [
            {
                "step": getattr(t, "step", i + 1),
                "agent": getattr(t, "agent", "unknown"),
                "action": getattr(t, "action", "unknown"),
                "result": getattr(t, "result", "unknown"),
                "reason_category": getattr(t, "reason_category", "unknown"),
            }
            for i, t in enumerate(state.agent_decisions + state.tool_executions)
        ]

        return {
            "analysis_id": state.analysis_id,
            "step_number": step_num,
            "workflow_status": state.status,
            "image_quality": quality_summary,
            "vision_diagnosis": vision_summary,
            "clinical_features_abcd": abcd_summary,
            "gradcam_attention": gradcam_summary,
            "multimodal_abcde_fusion": fusion_summary,
            "longitudinal_evolution": evolution_summary,
            "literature_evidence": evidence_summary,
            "uncertainty_signals": uncertainty_summary,
            "pipeline_outputs": outputs_summary,
            "flags": list(state.flags or []),
            "recent_trace": trace_events[-4:] if trace_events else [],
        }

    def _format_thought_action_json(
        self,
        state: CaseState,
        action: str,
        reason: str,
        step_num: int,
        mind_decision: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate structured JSON describing the clinical thought, selected action, and sequence for this step."""
        default_thoughts = {
            "validate_image": (
                "image_safety",
                "Image quality has not yet been validated. Clinical safety protocol mandates validating input image "
                "resolution, illumination, and blur variance before any downstream diagnostic processing.",
                "vision",
            ),
            "finish_case": (
                "case_termination",
                (
                    f"Input image rejected by quality control gate ({state.image_quality.get('reason')}). Safe analysis "
                    "cannot proceed with compromised image data."
                    if isinstance(state.image_quality, dict) and not state.image_quality.get("accepted")
                    else "All diagnostic and reporting phases completed successfully. Finalizing CaseState audit log."
                ),
                "orchestrator",
            ),
            "classify_image": (
                "deep_learning_vision",
                "Image quality verified. Swin Transformer V2 classification, SegFormer lesion segmentation, and ABCD "
                "morphological feature extraction required to establish baseline diagnostic evidence.",
                "vision",
            ),
            "refine_and_reclassify": (
                "spatial_faithfulness",
                "Grad-CAM visual attention map shows low alignment with lesion boundary (AIL below threshold). "
                "Re-extracting feature map and refining classification for spatial faithfulness.",
                "vision",
            ),
            "assess_evolution": (
                "longitudinal_analysis",
                f"Patient has {len(state.historical_images or [])} historical image visit(s). Clinical protocol requires "
                "longitudinal lesion evolution comparison to assess change in morphology over time (E criterion).",
                "clinical_context",
            ),
            "request_clinical_context": (
                "clinical_intake",
                "Evolution (E criterion) is unassessed. Querying patient clinical context and history to evaluate "
                "lesion changes over time.",
                "clinical_context",
            ),
            "apply_abcde_fusion": (
                "multimodal_fusion",
                "Vision predictions and ABCD morphological features are ready. Synthesizing multimodal ABCDE composite "
                "score and clinical risk prediction using weighted multi-criteria fusion.",
                "orchestrator",
            ),
            "retrieve_evidence": (
                "literature_retrieval",
                "Literature retrieval required to validate diagnostic criteria and differential diagnoses against "
                "medical knowledge base.",
                "evidence",
            ),
            "generate_explanation": (
                "clinical_synthesis",
                "Multimodal findings and medical literature are verified and sufficient. Synthesizing evidence-grounded "
                "clinical explanation and diagnostic rationale.",
                "report",
            ),
            "generate_report": (
                "report_generation",
                "Clinical explanation and diagnostic findings are synthesized. Generating comprehensive diagnostic report "
                "and patient documentation.",
                "report",
            ),
        }

        all_ordered_actions = [
            "validate_image",
            "classify_image",
            "assess_evolution" if state.historical_images else None,
            "apply_abcde_fusion",
            "retrieve_evidence",
            "generate_explanation",
            "generate_report",
            "finish_case",
        ]
        all_ordered_actions = [a for a in all_ordered_actions if a is not None]

        if mind_decision and mind_decision.get("thought"):
            phase = "cognitive_mind_deliberation"
            thought = mind_decision["thought"]
            engine = "gemini_cognitive_mind"
            target_agent = "evidence" if action == "retrieve_evidence" else "report"
            evidence_query = mind_decision.get("evidence_query")
        else:
            meta = default_thoughts.get(
                action,
                ("general_orchestration", f"Proceeding with {action} based on {reason}.", "orchestrator"),
            )
            phase = meta[0]
            thought = meta[1]
            target_agent = meta[2]
            engine = "safety_prerequisite_ordering"
            evidence_query = None

        completed_actions = [getattr(t, "action", "") for t in state.agent_decisions]
        upcoming_actions = [a for a in all_ordered_actions if a not in completed_actions and a != action]

        result: Dict[str, Any] = {
            "step": step_num,
            "engine": engine,
            "model": self._llm_model if engine == "gemini_cognitive_mind" else "deterministic_policy",
            "phase": phase,
            "thought": thought,
            "action": action,
            "reason": reason,
            "target_agent": target_agent,
        }
        if evidence_query:
            result["evidence_query"] = evidence_query
        result["workflow_sequence"] = {
            "completed": completed_actions,
            "current": action,
            "upcoming": upcoming_actions,
        }
        return result

    def _print_terminal_step_banner(
        self,
        step_num: int,
        action: str,
        reason: str,
        state_understanding: Dict[str, Any],
        thought_action_sequence: Dict[str, Any],
        gemini_raw_json: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Print prominent, formatted JSON blocks to the backend terminal for workflow observability."""
        delim = "=" * 80
        subdelim = "-" * 80

        print(f"\n{delim}", flush=True)
        print(f" [ORCHESTRATOR STEP {step_num} / {self.max_steps}]  ACTION: {action}  |  REASON: {reason}", flush=True)
        print(f"{delim}", flush=True)

        print("\n>>> 1. CASE STATE UNDERSTANDING (ORCHESTRATOR PERSPECTIVE JSON):", flush=True)
        print(json.dumps(state_understanding, indent=2, default=str), flush=True)

        if gemini_raw_json:
            print(f"\n{subdelim}", flush=True)
            print(">>> 2. GEMINI COGNITIVE MIND DELIBERATION (RAW RETURNED JSON):", flush=True)
            print(json.dumps(gemini_raw_json, indent=2, default=str), flush=True)

        print(f"\n{subdelim}", flush=True)
        print(">>> 3. THOUGHT & ACTION SEQUENCE (JSON):", flush=True)
        print(json.dumps(thought_action_sequence, indent=2, default=str), flush=True)
        print(f"{delim}\n", flush=True)

    def run(
        self,
        image_path: str,
        analysis_id: Optional[str] = None,
        save_mask: bool = False,
        scale_method: str = "auto",
        scale_reference_mm: Optional[float] = None,
        scale_reference_key: Optional[str] = None,
        clinical_context: Optional[Dict[str, Any]] = None,
        historical_images: Optional[List[str]] = None,
    ) -> CaseState:
        analysis_id = analysis_id or f"{Path(image_path).stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        state = CaseState(
            analysis_id=analysis_id,
            image_path=str(image_path),
            status="running",
            historical_images=historical_images or [],
        )

        for step_idx in range(self.max_steps):
            self._latest_thought = None
            self._latest_mind_decision = None
            action, reason = self.choose_next_action(state)

            state_understanding = self._format_case_state_json(state, step_idx + 1)
            thought_action = self._format_thought_action_json(
                state, action, reason, step_idx + 1, mind_decision=self._latest_mind_decision
            )

            # Print formatted Case State Understanding and Thought & Action Sequence JSON directly to terminal
            self._print_terminal_step_banner(
                step_num=step_idx + 1,
                action=action,
                reason=reason,
                state_understanding=state_understanding,
                thought_action_sequence=thought_action,
                gemini_raw_json=self._latest_mind_decision,
            )

            detail: Dict[str, Any] = {
                "thought": thought_action.get("thought"),
                "engine": thought_action.get("engine"),
                "phase": thought_action.get("phase"),
            }
            if self._latest_mind_decision:
                detail["gemini_deliberation"] = self._latest_mind_decision
                detail["cognitive_mode"] = "gemini_guided_deliberation"

            state.record(self.name, action, "selected", reason, detail=detail)

            if action == "finish_case":
                state.status = "completed" if not state.error_code else "failed"
                state.record(self.name, action, "completed", "termination")
                print(f"[Orchestrator] Case analysis completed with status: '{state.status}'.\n", flush=True)
                return state

            try:
                if action == "validate_image":
                    self.vision.validate_image(state, self._quality_cfg)
                elif action in {
                    "classify_image",
                    "segment_lesion",
                    "calculate_measurements",
                    "calibrate_scale",
                    "run_gradcam",
                }:
                    self.vision.analyze(
                        state,
                        save_mask=save_mask,
                        scale_method=scale_method,
                        scale_reference_mm=scale_reference_mm,
                        scale_reference_key=scale_reference_key,
                    )
                elif action == "refine_and_reclassify":
                    self.vision.refine_and_reclassify(state)
                elif action == "assess_evolution":
                    ev_result = self.clinical.assess_evolution(
                        state.historical_images + [state.image_path],
                        config=self._explainability_cfg,
                    )
                    state.clinical_context["evolution"] = ev_result
                    state.record(
                        self.clinical.name,
                        "assess_evolution",
                        ev_result.get("status", "unavailable"),
                        "historical_comparison",
                        {
                            "status": ev_result.get("status"),
                            "confidence": ev_result.get("confidence"),
                            "images_compared": ev_result.get("comparison", {}).get("images_compared"),
                        },
                        tool=True,
                    )
                    if state.diagnosis_result and "evolution" in state.diagnosis_result.clinical_features:
                        ev_status = ev_result.get("status", "unavailable")
                        ev_confidence = float(ev_result.get("confidence", 0.0))
                        state.diagnosis_result.clinical_features["evolution"].score_label = (
                            ev_status.replace("_", " ").title()
                        )
                        state.diagnosis_result.clinical_features["evolution"].score_numeric = ev_confidence
                        state.diagnosis_result.clinical_features["evolution"].details = ev_result
                elif action == "request_clinical_context":
                    self.clinical.update(state, clinical_context)
                    if (
                        state.diagnosis_result
                        and "evolution" in state.clinical_context
                        and "evolution" in state.diagnosis_result.clinical_features
                    ):
                        state.diagnosis_result.clinical_features["evolution"].score_label = "Patient history provided"
                        state.diagnosis_result.clinical_features["evolution"].details = state.clinical_context.get(
                            "evolution", {}
                        )
                elif action == "apply_abcde_fusion":
                    mel_prob = state.diagnosis_result.probabilities.get("melanoma", 0.0)
                    threshold = getattr(state.diagnosis_result, "classification_threshold", None) or 0.5
                    fusion = compute_fusion(
                        melanoma_prob=mel_prob,
                        diagnosis_result=state.diagnosis_result,
                        abcde=state.abcde,
                        clinical_context=state.clinical_context,
                        classification_threshold=threshold,
                        weights=self._abcde_weights,
                    )
                    state.fusion_result = fusion
                    state.diagnosis_result.diagnosis.prediction = fusion.prediction
                    state.diagnosis_result.diagnosis.confidence = float(
                        fusion.composite_score * 100.0
                        if fusion.prediction.lower() == "melanoma"
                        else (1.0 - fusion.composite_score) * 100.0
                    )
                    state.classification.update({
                        "prediction": fusion.prediction,
                        "fusion_score": fusion.composite_score,
                        "fusion_weights": fusion.weights_used,
                        "fusion_components": fusion.component_scores,
                    })
                    state.flags.extend(fusion.flags)
                    print(
                        f"\n[ABCDE Fusion] Score={fusion.composite_score:.4f} Threshold={threshold:.4f} "
                        f"Prediction={fusion.prediction}"
                    )
                    print(f"[ABCDE Fusion] Weights={fusion.weights_used} Components={fusion.component_scores}\n")
                    state.record(
                        self.name,
                        "apply_abcde_fusion",
                        "completed",
                        "abcde_fusion",
                        {
                            "composite_score": fusion.composite_score,
                            "prediction": fusion.prediction,
                            "weights": fusion.weights_used,
                            "components": fusion.component_scores,
                        },
                        tool=True,
                    )
                elif action == "retrieve_evidence":
                    self.evidence.retrieve_evidence(state, reason)
                elif action == "generate_explanation":
                    self.report.generate_explanation(state)
                elif action == "generate_report":
                    self.report.generate_report(state)
                else:
                    raise RuntimeError(f"Unsupported orchestrator action: {action}")
            except Exception as exc:
                state.error_code, state.user_message = (
                    "workflow_action_failed",
                    f"The requested analysis action could not be completed. Action '{action}' failed: {str(exc)}",
                )
                state.flags.append(f"{action} failed: {type(exc).__name__}")
                state.record(
                    self.name,
                    action,
                    "failed",
                    "tool_failure",
                    {"exception": type(exc).__name__},
                    tool=True,
                )
                state.status = "failed"
                return state

        state.error_code, state.user_message, state.status = (
            "orchestrator_step_limit",
            "Analysis ended after reaching the safe workflow step limit.",
            "failed",
        )
        return state

    def choose_next_action(self, state: CaseState) -> Tuple[str, str]:
        """
        Hybrid Guided Reasoning policy:
        Combines mandatory clinical prerequisite ordering with LLM cognitive deliberation.
        """
        # ── 1. Mandatory Safety & Foundational Observations ────────────────
        if not state.image_quality:
            return "validate_image", "image_quality"
        if not state.image_quality.get("accepted"):
            state.error_code, state.user_message, state.retryable = (
                "image_quality_insufficient",
                state.image_quality.get("reason"),
                True,
            )
            return "finish_case", "image_quality"
        if state.diagnosis_result is None:
            return "classify_image", "vision_required"
        if self._should_adapt_from_gradcam(state):
            return "refine_and_reclassify", "gradcam_visual_misaligned"
        if state.historical_images and "evolution" not in state.clinical_context:
            return "assess_evolution", "historical_images_present"
        if "E" not in state.abcde:
            return "request_clinical_context", "missing_evolution"
        if state.fusion_result is None:
            return "apply_abcde_fusion", "abcde_ready"

        # ── 2. Cognitive Deliberation Phase (Orchestrator Mind) ─────────────
        if state.explanation is None:
            # Active deliberation via LLM if cycles remain
            if state.evidence_assessment.cycles_completed < self.evidence.max_cycles:
                mind_decision = self._deliberate_with_mind(state)
                if mind_decision:
                    thought = mind_decision.get("thought", "")
                    action = mind_decision.get("action")
                    reason = mind_decision.get("reason") or "cognitive_deliberation"
                    query = mind_decision.get("evidence_query")
                    self._latest_thought = thought
                    self._latest_mind_decision = mind_decision

                    if action == "retrieve_evidence":
                        return "retrieve_evidence", query or reason
                    elif action == "generate_explanation":
                        state.evidence_assessment.sufficient = True
                        return "generate_explanation", "evidence_sufficient"

            # Deterministic clinical fallback if LLM is offline or unconfigured
            if state.evidence_assessment.cycles_completed == 0:
                return (
                    "retrieve_evidence",
                    "differential" if state.uncertainty.classification < self.confidence_threshold else "ABCDE",
                )
            if (
                not state.evidence_assessment.sufficient
                and state.evidence_assessment.cycles_completed < self.evidence.max_cycles
            ):
                return "retrieve_evidence", "ABCDE"
            return "generate_explanation", "validated_inputs_ready"

        # ── 3. Synthesis & Completion ──────────────────────────────────────
        if state.final_report is None:
            return "generate_report", "validated_synthesis_ready"
        return "finish_case", "report_ready"

    def _should_adapt_from_gradcam(self, state: CaseState) -> bool:
        """Evaluate Grad-CAM visual attention metrics to determine if reclassification is warranted."""
        if state.diagnosis_result is None:
            return False
        retry_count = state.gradcam.get("retry_count", 0)
        if retry_count >= self.max_retry_attempts:
            return False
        if state.gradcam and state.gradcam.get("alignment_reliable") is False:
            return True
        ail = state.gradcam.get("attention_inside_lesion")
        if ail is not None and ail < self.gradcam_threshold:
            return True
        return False

