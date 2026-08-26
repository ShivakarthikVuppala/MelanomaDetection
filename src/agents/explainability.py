"""
Explainability Agent — Phase 3
================================

Generates evidence-supported explanations of the model output by
combining the DiagnosisResult, retrieved medical evidence, and
Grad-CAM validation metrics.

Supports two modes:
- **template**: Deterministic, rule-based explanations. No external dependency.
- **llm**: Sends a structured clinical prompt to Google Gemini for
  natural language medical reasoning. Requires GEMINI_API_KEY env var.

Usage:
    agent = ExplainabilityAgent(config)
    explanation = agent.explain(diagnosis_result, evidence_list)
"""

import os
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


def _evidence_value(evidence_item: Any, key: str, default: Any = "") -> Any:
    """Read evidence fields from either dataclass objects or dictionaries."""
    if isinstance(evidence_item, dict):
        return evidence_item.get(key, default)
    return getattr(evidence_item, key, default)


def _format_metric(value: Any) -> str:
    """Format an optional numeric explainability metric safely."""
    return f"{value:.4f}" if value is not None else "N/A"


@dataclass
class ExplanationResult:
    """Structured explanation output from the Explainability Agent."""
    summary: str
    reasoning: List[str]
    evidence_citations: List[Dict[str, str]]
    confidence_assessment: str  # high | moderate | low | requires-review
    grad_cam_reliable: bool
    next_steps: str = ""
    limitations: List[str] = field(default_factory=list)
    grad_cam_detail: Optional[str] = None
    flags: List[str] = field(default_factory=list)


class ExplainabilityAgent:
    """
    Phase 3 agent: generates evidence-supported explanations.

    Template mode builds deterministic explanations from diagnosis
    features and retrieved evidence. LLM mode uses Google Gemini
    to generate clinical-grade natural language explanations.

    Args:
        config: Dict with keys:
            - mode: 'template' | 'llm'
            - llm_provider: 'gemini' (currently only supported provider)
            - gradcam_ail_threshold: float (default: 0.30)
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.mode = config.get("mode", "template")
        self.llm_provider = config.get("llm_provider", "gemini")
        self.model_name = config.get("model") or os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
        self.ail_threshold = config.get("gradcam_ail_threshold", 0.30)
        self._gemini_model = None

    def explain(
        self,
        diagnosis_result,
        evidence: List[Any],
        grad_cam_heatmap=None,
        mask=None,
    ) -> ExplanationResult:
        """
        Generate an explanation combining diagnosis, evidence, and Grad-CAM.

        Args:
            diagnosis_result: DiagnosisResult from Phase 1.
            evidence: List of EvidenceItem from Phase 2.
            grad_cam_heatmap: Optional Grad-CAM heatmap array.
            mask: Optional segmentation mask array.

        Returns:
            ExplanationResult with reasoning chain and citations.
        """
        if self.mode == "llm":
            return self._llm_explain(diagnosis_result, evidence)
        else:
            return self._template_explain(diagnosis_result, evidence)

    # ==================================================================
    # LLM Mode — Google Gemini
    # ==================================================================

    def _get_gemini_model(self):
        """Lazily initialize the Gemini generative model."""
        if self._gemini_model is not None:
            return self._gemini_model

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY environment variable not set. "
                "Set it via: set GEMINI_API_KEY=your_key (Windows) "
                "or export GEMINI_API_KEY=your_key (Linux/Mac). "
                "Get a free key at https://aistudio.google.com/apikey"
            )

        from google import genai

        client = genai.Client(api_key=api_key)
        self._gemini_model = client
        logger.info("Gemini client initialized (%s)", self.model_name)
        return client

    def _build_clinical_prompt(self, diagnosis_result, evidence: List[Any]) -> str:
        """
        Build a structured clinical prompt for the LLM.

        Provides all diagnostic data in a structured format and asks
        the LLM to generate a dermatologist-level clinical explanation.
        """
        diag = diagnosis_result
        prediction = diag.diagnosis.prediction
        confidence = diag.diagnosis.confidence

        # ABCD features
        feature_lines = []
        for name, feat in diag.clinical_features.items():
            feature_lines.append(f"  - {name.capitalize()}: {feat.score_label} (score: {feat.score_numeric:.3f})")

        # Color details
        color_meas = diag.measurements.get("color", {})
        derm_colors = color_meas.get("detected_derm_colors", [])
        n_clusters = color_meas.get("dominant_clusters", 0)

        # Segmentation
        seg = diag.segmentation
        seg_info = ""
        if seg.area_px and seg.perimeter_px:
            seg_info = f"Lesion area: {seg.area_px:,} px, Perimeter: {seg.perimeter_px:.0f} px"

        # Grad-CAM metrics
        expl = diag.explainability
        ail = getattr(expl, "attention_inside_lesion", None)
        aol = getattr(expl, "attention_outside_lesion", None)
        iou = getattr(expl, "mask_cam_iou", None)
        centroid = getattr(expl, "centroid_distance", None)

        gradcam_info = "Not available"
        if ail is not None:
            gradcam_info = (
                f"Attention Inside Lesion (AIL): {ail:.4f}\n"
                f"  Attention Outside Lesion (AOL): {_format_metric(aol)}\n"
                f"  Centroid Distance: {_format_metric(centroid)}\n"
                f"  Mask-CAM IoU: {_format_metric(iou)}\n"
                f"  Reliability: {'RELIABLE' if ail >= self.ail_threshold else 'UNRELIABLE — attention primarily outside lesion'}"
            )

        # Evidence
        evidence_lines = []
        for i, ev in enumerate(evidence, 1):
            title = _evidence_value(ev, "title", "")
            source = _evidence_value(ev, "source", "")
            content = _evidence_value(ev, "content", "")
            score = _evidence_value(ev, "relevance_score", 0)
            evidence_lines.append(
                f"  [{i}] \"{title}\" — {source} (relevance: {score:.3f})\n"
                f"      {content[:250]}"
            )

        prompt = f"""You are an AI dermatology assistant analyzing the output of an automated melanoma diagnostic pipeline. Generate a clinical explanation of the following diagnosis result.

## DIAGNOSTIC DATA

**Classification Result:** {prediction} ({confidence:.1f}% confidence)
**Probabilities:** melanoma={diag.probabilities.get('melanoma', 0):.4f}, benign={diag.probabilities.get('non_melanoma', diag.probabilities.get('not_melanoma', 0)):.4f}

**Clinical Features (ABCD Rule):**
{chr(10).join(feature_lines)}

**Branch separation:** The SwinV2 image classifier produced the melanoma
probability and thresholded screening output independently. The ABCD features
and lesion measurements were extracted separately from the SegFormer/refined
lesion mask; they are complementary image findings and were not classifier
inputs.

**Color Analysis:**
  Dominant clusters: {n_clusters}
  Detected dermoscopic colors: {', '.join(derm_colors) if derm_colors else 'N/A'}

**Segmentation:**
  {seg_info or 'Not available'}

**Grad-CAM Explainability Metrics:**
  {gradcam_info}

**Retrieved Medical Evidence:**
{chr(10).join(evidence_lines) if evidence_lines else '  No evidence retrieved.'}

## INSTRUCTIONS

Generate a patient-friendly explanation following this format:

1. **WHAT THIS MEANS** (1-2 short sentences): Explain the AI estimate in everyday language. Say clearly that it is not a diagnosis.
2. **WHAT THE IMAGE SHOWED** (short paragraph): Explain the ABCD findings in everyday language. Use the supplied values only when useful.
3. **HOW THE IMAGE WAS CHECKED** (1 short sentence): Say that the lesion outline and image focus checks were supportive or require review. Do not use terms such as AIL, AOL, IoU, logits, embeddings, or attention maps.
4. **MEDICAL INFORMATION THAT SUPPORTS THIS** (short paragraph): Summarize the retrieved evidence in plain language and cite its source names.
5. **WHAT TO DO NEXT** (1-2 sentences): Recommend evaluation by a qualified dermatologist, especially for a new, changing, bleeding, painful, or unusual lesion. Explain that a biopsy with histopathology may be considered by the clinician when needed to confirm the diagnosis.
6. **CONFIDENCE AND LIMITATIONS** (1 short sentence): Explain uncertainty and that an image cannot replace an examination.

IMPORTANT GUIDELINES:
- Write for a patient or caregiver, using plain language and short sentences.
- Do not call the result a confirmed malignancy or definitive diagnosis.
- Put the dermatologist and possible histopathology recommendation near the beginning, not only at the end.
- Be precise with numbers — reference actual scores and metrics.
- Use only numerical values explicitly supplied in DIAGNOSTIC DATA. Never estimate or invent a missing measurement.
- Clearly distinguish model output, computed image measurements, retrieved evidence, and generated explanation.
- If features contradict the classification, note the discrepancy.
- Always include the disclaimer that this is an AI-assisted analysis, not a clinical diagnosis.
- Keep the total response under 400 words.
- Separate each section with the section header in bold."""

        return prompt

    def _parse_llm_response(
        self, response_text: str, diagnosis_result, evidence: List[Any]
    ) -> ExplanationResult:
        """Parse the LLM's natural language response into an ExplanationResult."""
        diag = diagnosis_result
        confidence = diag.diagnosis.confidence
        prediction = diag.diagnosis.prediction

        # Extract sections as reasoning steps
        reasoning = []
        current_section = []
        for line in response_text.strip().split("\n"):
            stripped = line.strip()
            if not stripped:
                if current_section:
                    reasoning.append(" ".join(current_section))
                    current_section = []
                continue
            # Clean markdown bold markers for cleaner display
            current_section.append(stripped)

        if current_section:
            reasoning.append(" ".join(current_section))

        # Build citations from evidence
        citations = []
        for ev in evidence:
            title = _evidence_value(ev, "title", "")
            source = _evidence_value(ev, "source", "")
            score = _evidence_value(ev, "relevance_score", 0)
            citations.append({
                "title": title,
                "source": source,
                "relevance_score": str(round(score, 3)),
            })

        # Determine Grad-CAM reliability
        ail = getattr(diag.explainability, "attention_inside_lesion", None)
        grad_cam_reliable = ail is not None and ail >= self.ail_threshold

        grad_cam_detail = None
        iou = getattr(diag.explainability, "mask_cam_iou", None)
        if ail is not None:
            if grad_cam_reliable:
                grad_cam_detail = (
                    f"Grad-CAM attention aligns with lesion "
                    f"(AIL={ail:.3f}, IoU={_format_metric(iou)})."
                )
            else:
                grad_cam_detail = (
                    f"⚠ Grad-CAM attention outside lesion "
                    f"(AIL={ail:.3f}, IoU={_format_metric(iou)}). Visual explanation unreliable."
                )

        flags = []
        if not grad_cam_reliable and ail is not None:
            flags.append("grad_cam_unreliable")

        # Confidence assessment
        confidence_assessment = self._assess_confidence(
            confidence, grad_cam_reliable, len(evidence), flags
        )

        # Summary — extract from the first reasoning line or build one
        summary_line = reasoning[0] if reasoning else ""
        if len(summary_line) > 200:
            summary = summary_line[:197] + "..."
        else:
            summary = summary_line

        # Fallback summary if LLM didn't give a good one
        if not summary or len(summary) < 20:
            summary = (
                f"{'Melanoma detected' if prediction == 'Melanoma' else 'Benign lesion'}"
                f" — AI confidence: {confidence:.1f}% (Gemini-enhanced analysis)"
            )

        return ExplanationResult(
            summary=summary,
            reasoning=reasoning,
            evidence_citations=citations,
            confidence_assessment=confidence_assessment,
            grad_cam_reliable=grad_cam_reliable,
            next_steps=(
                "Please arrange an evaluation with a qualified dermatologist. "
                "If the clinician considers it necessary, a biopsy with histopathology "
                "may be used to confirm the diagnosis."
            ),
            limitations=[
                "This image-based AI result is not a definitive diagnosis.",
                "Physical size in millimeters cannot be determined without a calibrated scale.",
            ],
            grad_cam_detail=grad_cam_detail,
            flags=flags,
        )

    def _llm_explain(
        self,
        diagnosis_result,
        evidence: List[Any],
    ) -> ExplanationResult:
        """Generate an LLM-powered clinical explanation via Google Gemini."""
        logger.info("Phase 3: Generating LLM explanation via Gemini...")

        try:
            client = self._get_gemini_model()
            prompt = self._build_clinical_prompt(diagnosis_result, evidence)

            chat = client.chats.create(model=self.model_name)
            response = chat.send_message(prompt)

            response_text = response.text
            logger.info(f"Gemini response received ({len(response_text)} chars)")

            result = self._parse_llm_response(
                response_text, diagnosis_result, evidence
            )
            return result

        except Exception as e:
            logger.warning(
                f"LLM explanation failed: {e}. "
                f"Falling back to template mode."
            )
            # Graceful fallback to template mode
            result = self._template_explain(diagnosis_result, evidence)
            result.flags.append("llm_fallback_to_template")
            return result

    # ==================================================================
    # Template Mode — Deterministic (no LLM)
    # ==================================================================

    def _template_explain(
        self,
        diagnosis_result,
        evidence: List[Any],
    ) -> ExplanationResult:
        """Generate a deterministic template-based explanation."""
        diag = diagnosis_result
        prediction = diag.diagnosis.prediction
        confidence = diag.diagnosis.confidence
        is_melanoma = prediction == "Melanoma"

        melanoma_probability = float(diag.probabilities.get("melanoma", 0.0))
        non_melanoma_probability = float(
            diag.probabilities.get("not_melanoma", diag.probabilities.get("non_melanoma", 0.0))
        )
        feature_text = []
        for name, feature in diag.clinical_features.items():
            friendly_name = {"asymmetry": "shape symmetry", "border": "edge regularity", "color": "color variation"}.get(name, name)
            feature_text.append(f"The lesion's {friendly_name} was described as {feature.score_label.lower()}.")

        lesion = diag.measurements.get("lesion", {})
        measurement_text = []
        if lesion.get("diameter_px") is not None:
            measurement_text.append(f"The estimated image diameter was {lesion['diameter_px']:,.0f} pixels.")
        if lesion.get("area_px") is not None and lesion.get("perimeter_px") is not None:
            measurement_text.append(f"The outlined area was {lesion['area_px']:,} pixels with a perimeter of {lesion['perimeter_px']:,.0f} pixels.")
        measurement_text.append("These are image measurements, not millimeters; physical size requires a calibrated reference.")

        ail = getattr(diag.explainability, "attention_inside_lesion", None)
        focus_text = (
            "The image-focus check was consistent with the outlined lesion."
            if ail is not None and ail >= self.ail_threshold
            else "The image-focus check requires review, so the visual explanation should be interpreted cautiously."
        )
        evidence_text = []
        citations = []
        for ev in evidence[:3]:
            title = _evidence_value(ev, "title", "Medical reference")
            source = _evidence_value(ev, "source", "")
            evidence_text.append(f"{title} ({source}) was retrieved as supporting medical information.")
            score = _evidence_value(ev, "relevance_score", 0)
            citations.append({"title": title, "source": source, "relevance_score": str(round(score, 3))})

        confidence_assessment = self._assess_confidence(
            confidence, ail is not None and ail >= self.ail_threshold, len(evidence), []
        )
        summary = (
            f"The AI estimates a {melanoma_probability * 100:.1f}% chance that this lesion is melanoma "
            f"and a {non_melanoma_probability * 100:.1f}% chance that it is not melanoma. "
            "This is an AI estimate, not a confirmed diagnosis."
        ) if is_melanoma else (
            f"The AI estimate favors a non-melanoma lesion ({non_melanoma_probability * 100:.1f}%), "
            f"with a melanoma probability of {melanoma_probability * 100:.1f}%. "
            "This is an AI estimate, not a confirmed diagnosis."
        )
        reasoning = [
            f"AI estimate: melanoma {melanoma_probability * 100:.1f}%; non-melanoma {non_melanoma_probability * 100:.1f}%.",
            "The SwinV2 image classifier produced the screening output independently of the separately extracted ABCD features. The ABCD findings describe the refined SegFormer lesion mask and did not cause the classifier prediction.",
            *feature_text,
            *measurement_text,
            focus_text,
            f"Medical information: {(' '.join(evidence_text)) if evidence_text else 'No supporting medical references were available.'}",
            "What to do next: Please arrange an evaluation with a qualified dermatologist, especially if the lesion is new, changing, bleeding, painful, or unusual. If the clinician considers it necessary, a biopsy with histopathology may be used to confirm the diagnosis.",
            "Limitations: An image-based AI result cannot replace an in-person examination and cannot confirm or rule out cancer by itself.",
        ]
        return ExplanationResult(
            summary=summary,
            reasoning=reasoning,
            evidence_citations=citations,
            confidence_assessment=confidence_assessment,
            grad_cam_reliable=ail is not None and ail >= self.ail_threshold,
            next_steps="Please arrange a qualified dermatologist evaluation. If clinically indicated, biopsy with histopathology may be used to confirm the diagnosis.",
            limitations=["AI image analysis is not a definitive diagnosis.", "Physical size in millimeters is unavailable without calibrated scale."],
            grad_cam_detail=None,
            flags=[],
        )

    # ==================================================================
    # Shared helpers
    # ==================================================================

    def _interpret_feature(self, name: str, feat, is_melanoma: bool) -> str:
        """Generate a clinical interpretation for a single ABCD feature."""
        score = feat.score_numeric
        label = feat.score_label

        interpretations = {
            "asymmetry": {
                True: {
                    "high": f"Asymmetry is {label} (score: {score:.3f}), strongly suggestive of melanoma. Asymmetric lesions indicate uneven melanocyte proliferation.",
                    "moderate": f"Asymmetry is {label} (score: {score:.3f}), moderately atypical. This level of asymmetry warrants careful evaluation alongside other features.",
                    "low": f"Asymmetry is {label} (score: {score:.3f}), relatively symmetric. This is less typical for melanoma but does not exclude it.",
                },
                False: {
                    "high": f"Asymmetry is {label} (score: {score:.3f}), atypically high for a benign lesion.",
                    "moderate": f"Asymmetry is {label} (score: {score:.3f}), within acceptable range for benign lesions.",
                    "low": f"Asymmetry is {label} (score: {score:.3f}), consistent with symmetric benign nevi.",
                },
            },
            "border": {
                True: {
                    "high": f"Border irregularity is {label} (score: {score:.3f}), indicating irregular peripheral growth typical of melanoma.",
                    "moderate": f"Border irregularity is {label} (score: {score:.3f}), showing some border irregularity consistent with atypical lesions.",
                    "low": f"Border is {label} (score: {score:.3f}), relatively smooth. Well-defined borders are less common in melanoma.",
                },
                False: {
                    "high": f"Border irregularity is {label} (score: {score:.3f}), atypically irregular for a benign lesion.",
                    "moderate": f"Border irregularity is {label} (score: {score:.3f}), within range for benign melanocytic lesions.",
                    "low": f"Border is {label} (score: {score:.3f}), smooth and well-defined as expected in benign nevi.",
                },
            },
            "color": {
                True: {
                    "high": f"Color variation is {label} (score: {score:.3f}), indicating significant color variegation associated with melanoma.",
                    "moderate": f"Color variation is {label} (score: {score:.3f}), showing some heterogeneity that may be concerning.",
                    "low": f"Color variation is {label} (score: {score:.3f}), relatively homogeneous. Limited color variation is less typical for melanoma.",
                },
                False: {
                    "high": f"Color variation is {label} (score: {score:.3f}), unusually varied for a benign lesion.",
                    "moderate": f"Color variation is {label} (score: {score:.3f}), within normal range for benign nevi.",
                    "low": f"Color is {label} (score: {score:.3f}), homogeneous as expected in benign melanocytic lesions.",
                },
            },
        }

        # Determine severity bucket
        if score > 0.5:
            severity = "high"
        elif score > 0.2:
            severity = "moderate"
        else:
            severity = "low"

        feature_map = interpretations.get(name, {})
        melanoma_map = feature_map.get(is_melanoma, {})
        return melanoma_map.get(
            severity,
            f"{name.capitalize()} is {label} (score: {score:.3f})."
        )

    def _assess_confidence(
        self,
        model_confidence: float,
        grad_cam_reliable: bool,
        evidence_count: int,
        flags: List[str],
    ) -> str:
        """Determine overall confidence assessment."""
        if "grad_cam_unreliable" in flags or not grad_cam_reliable:
            return "requires-review"
        if model_confidence >= 90 and grad_cam_reliable and evidence_count >= 3:
            return "high"
        if model_confidence >= 70:
            return "moderate"
        return "low"

    def _summarize_features(self, clinical_features: dict) -> str:
        """Create a brief summary of clinical feature labels."""
        parts = []
        for name, feat in clinical_features.items():
            parts.append(f"{feat.score_label.lower()} {name}")
        return ", ".join(parts)
