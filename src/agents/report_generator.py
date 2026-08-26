"""
Report Generation Agent — Phase 4
====================================

Generates the final structured report from all pipeline outputs:
- Dashboard payload (JSON for the React frontend)
- PDF report (using fpdf2)

The PDF is structured for clinical readability:
    1. Diagnosis summary & risk level
    2. Recommended next step
    3. Plain-language explanation (before technical details)
    4. Image findings (ABCD features)
    5. Lesion measurements & scale calibration
    6. Visualizations (original, overlay, Grad-CAM)
    7. Supporting medical references
    8. Technical pipeline information
    9. Disclaimer

Usage:
    agent = ReportGenerationAgent(config)
    report = agent.generate(diagnosis_result, evidence, explanation)
"""

import logging
import tempfile
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


def _evidence_value(evidence_item: Any, key: str, default: Any = "") -> Any:
    """Read evidence fields from dataclass objects or dictionary payloads."""
    if isinstance(evidence_item, dict):
        return evidence_item.get(key, default)
    return getattr(evidence_item, key, default)


@dataclass
class ReportResult:
    """Output from the Report Generation Agent."""
    dashboard_payload: Dict[str, Any]
    pdf_path: Optional[str] = None
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())


class ReportGenerationAgent:
    """
    Phase 4 agent: generates PDF reports and dashboard payloads.

    Args:
        config: Dict with keys:
            - output_dir: path for PDF reports (default: outputs/reports/)
            - include_gradcam: bool (default: True)
            - include_evidence: bool (default: True)
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.output_dir = Path(config.get("output_dir", "outputs/reports"))
        self.include_gradcam = config.get("include_gradcam", True)
        self.include_evidence = config.get("include_evidence", True)

    def generate(
        self,
        diagnosis_result,
        evidence: List[Any],
        explanation,
        analysis_id: str = "report",
    ) -> ReportResult:
        """
        Generate the final report from all pipeline phase outputs.

        Args:
            diagnosis_result: DiagnosisResult from Phase 1.
            evidence: List of EvidenceItem from Phase 2.
            explanation: ExplanationResult from Phase 3.
            analysis_id: Identifier for this analysis.

        Returns:
            ReportResult with dashboard payload and optional PDF path.
        """
        # Build dashboard payload
        payload = self._build_dashboard_payload(
            diagnosis_result, evidence, explanation, analysis_id
        )

        # Generate PDF
        pdf_path = None
        try:
            pdf_path = self._generate_pdf(
                diagnosis_result, evidence, explanation, analysis_id
            )
            payload["pdf_url"] = f"/static/outputs/reports/{Path(pdf_path).name}"
        except Exception as e:
            logger.warning(f"PDF generation failed: {e}")
            payload["pdf_url"] = None

        return ReportResult(
            dashboard_payload=payload,
            pdf_path=pdf_path,
        )

    def _build_dashboard_payload(
        self,
        diagnosis_result,
        evidence: List[Any],
        explanation,
        analysis_id: str,
    ) -> Dict[str, Any]:
        """Build the JSON payload consumed by the React dashboard."""
        diag = diagnosis_result

        # Serialize evidence
        evidence_list = []
        for ev in evidence:
            evidence_list.append({
                "title": _evidence_value(ev, "title"),
                "source": _evidence_value(ev, "source"),
                "category": _evidence_value(ev, "category"),
                "content": _evidence_value(ev, "content"),
                "relevance_score": _evidence_value(ev, "relevance_score", 0.0),
            })

        # Serialize clinical features
        features = {}
        for name, feat in diag.clinical_features.items():
            features[name] = {
                "name": feat.name,
                "score_numeric": feat.score_numeric,
                "score_label": feat.score_label,
            }

        # Serialize explainability metrics
        expl_metrics = {}
        for attr in ["attention_inside_lesion", "attention_outside_lesion",
                      "centroid_distance", "mask_cam_iou"]:
            val = getattr(diag.explainability, attr, None)
            if val is not None:
                expl_metrics[attr] = val

        # Serialize scale calibration
        scale_cal = {}
        if diag.scale_calibration is not None:
            scale_cal = {
                "pixels_per_mm": diag.scale_calibration.pixels_per_mm,
                "method": diag.scale_calibration.method,
                "confidence": diag.scale_calibration.confidence,
                "reference_type": diag.scale_calibration.reference_type,
                "reference_diameter_px": diag.scale_calibration.reference_diameter_px,
                "reference_diameter_mm": diag.scale_calibration.reference_diameter_mm,
                "reference_bbox_px": diag.scale_calibration.reference_bbox_px,
                "detected": diag.scale_calibration.detected,
                "calibration_confidence": diag.scale_calibration.calibration_confidence,
                "calibration_valid": diag.scale_calibration.calibration_valid,
                "calibration_method": diag.scale_calibration.calibration_method,
                "reference_object_type": diag.scale_calibration.reference_object_type,
                "reference_length_px": diag.scale_calibration.reference_length_px,
                "reference_length_mm": diag.scale_calibration.reference_length_mm,
                "calibration_reason": diag.scale_calibration.calibration_reason,
                "orientation": diag.scale_calibration.orientation,
                "angle_degrees": diag.scale_calibration.angle_degrees,
                "interval_mm": diag.scale_calibration.interval_mm,
                "tick_positions_px": diag.scale_calibration.tick_positions_px,
                "tick_spacing_px": diag.scale_calibration.tick_spacing_px,
                "validated_tick_count": diag.scale_calibration.validated_tick_count,
            }

        payload = {
            "analysis_id": analysis_id,
            "status": "completed",
            "generated_at": datetime.now().isoformat(),
            "diagnosis": {
                "prediction": diag.diagnosis.prediction,
                "confidence": diag.diagnosis.confidence,
            },
            "probabilities": diag.probabilities,
            "classification_threshold": diag.classification_threshold,
            "clinical_features": features,
            "clinical_interpretations": diag.clinical_interpretations,
            "measurements": diag.measurements,
            "segmentation": {
                "status": diag.segmentation.status,
                "area_px": diag.segmentation.area_px,
                "perimeter_px": diag.segmentation.perimeter_px,
                "physical_scale_available": diag.measurements.get("lesion", {}).get("physical_scale_available", False),
            },
            "scale_calibration": scale_cal,
            "explainability_metrics": expl_metrics,
            "preprocessing": {
                "hair_removal": diag.preprocessing.hair_removal,
                "illumination_normalization": diag.preprocessing.illumination_normalization,
            },
            "pipeline": {
                "classification_model": diag.pipeline.classification_model,
                "segmentation_model": diag.pipeline.segmentation_model,
                "feature_extractor": diag.pipeline.feature_extractor,
                "pipeline_version": diag.pipeline.pipeline_version,
            },
            "evidence": evidence_list if self.include_evidence else [],
            "explanation": {
                "summary": explanation.summary,
                "reasoning": explanation.reasoning,
                "confidence_assessment": explanation.confidence_assessment,
                "next_steps": explanation.next_steps,
                "limitations": explanation.limitations,
                "grad_cam_reliable": explanation.grad_cam_reliable,
                "flags": explanation.flags,
            },
            "metadata": {
                "timestamp": diag.metadata.timestamp.isoformat(),
                "image_id": diag.metadata.request_id or analysis_id,
            },
        }

        return payload

    # ==================================================================
    # PDF Generation
    # ==================================================================

    def _generate_pdf(
        self,
        diagnosis_result,
        evidence: List[Any],
        explanation,
        analysis_id: str,
    ) -> str:
        """Generate a well-structured clinical PDF report."""
        import warnings
        warnings.filterwarnings(
            "ignore",
            message="You have both PyFPDF & fpdf2 installed",
            category=UserWarning,
        )
        from fpdf import FPDF

        self.output_dir.mkdir(parents=True, exist_ok=True)
        diag = diagnosis_result
        prediction = diag.diagnosis.prediction
        confidence = diag.diagnosis.confidence
        is_melanoma = prediction == "Melanoma"
        probs = diag.probabilities
        mel_prob = float(probs.get("melanoma", 0.0))
        ben_prob = float(probs.get("non_melanoma", probs.get("not_melanoma", 0.0)))
        threshold = diag.classification_threshold
        ail = getattr(diag.explainability, "attention_inside_lesion", None)
        focus_requires_review = ail is not None and ail < 0.30
        timestamp = diag.metadata.timestamp.strftime("%Y-%m-%d %H:%M:%S")

        # ---- Page geometry ----------------------------------------
        LM = 15   # left margin  mm
        RM = 15   # right margin mm
        TM = 15   # top margin   mm
        BM = 20   # bottom auto-break margin mm

        class SafePDF(FPDF):
            @staticmethod
            def _safe_text(value: Any) -> str:
                text = (str(value)
                        .replace("\u2022", "-").replace("\u2014", "-")
                        .replace("\u2013", "-").replace("\u26a0", "Warning:")
                        .replace("\u2713", "[ok]").replace("\u2019", "'")
                        .replace("\u201c", '"').replace("\u201d", '"'))
                return text.encode("latin-1", errors="replace").decode("latin-1")

            def safe_cell(self, w, h, text, **kwargs):
                return super().cell(w, h, self._safe_text(text), **kwargs)

            def safe_multi_cell(self, w, h, text, **kwargs):
                return super().multi_cell(w, h, self._safe_text(text), **kwargs)

            def footer(self):
                self.set_y(-13)
                self.set_font("Helvetica", "", 8)
                self.set_text_color(120, 120, 120)
                self.cell(0, 6, f"MelaDetect AI  |  Page {self.page_no()}", align="C")
                self.set_text_color(0, 0, 0)

        pdf = SafePDF()
        pdf.set_margins(left=LM, top=TM, right=RM)
        pdf.set_auto_page_break(auto=True, margin=BM)
        pdf.add_page()

        PW = pdf.epw  # effective page width = 210 - LM - RM = 180 mm

        # Convenience wrappers that always reset x to LM first
        def row(text, h=5, size=9, bold=False, align="L", color=(0, 0, 0), fill=False):
            pdf.set_font("Helvetica", "B" if bold else "", size)
            pdf.set_text_color(*color)
            pdf.set_x(LM)
            pdf.safe_cell(PW, h, text, ln=True, align=align, fill=fill)
            pdf.set_text_color(0, 0, 0)

        def wrap(text, h=5, size=9, bold=False, color=(0, 0, 0), indent=0):
            pdf.set_font("Helvetica", "B" if bold else "", size)
            pdf.set_text_color(*color)
            pdf.set_x(LM + indent)
            pdf.safe_multi_cell(PW - indent, h, text)
            pdf.set_text_color(0, 0, 0)

        # ==============================================================
        # HEADER BAR  (teal background)
        # ==============================================================
        pdf.set_fill_color(13, 94, 88)
        pdf.rect(0, 0, 210, 36, "F")   # full-width background rect
        pdf.set_xy(LM, 7)
        pdf.set_font("Helvetica", "B", 20)
        pdf.set_text_color(255, 255, 255)
        pdf.safe_cell(PW, 10, "Melanoma Diagnostic Report", ln=True, align="C")
        pdf.set_x(LM)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(200, 230, 228)
        pdf.safe_cell(PW, 6, f"Analysis {analysis_id}  |  {timestamp}", ln=True, align="C")

        # Advance below header bar
        pdf.set_y(TM + 28)
        pdf.set_text_color(0, 0, 0)

        # ==============================================================
        # RISK BANNER
        # ==============================================================
        if is_melanoma and focus_requires_review:
            pdf.set_fill_color(254, 243, 199)
            risk_color = (146, 92, 0)
            risk_text = "SCREENING FLAG - FOCUS REVIEW REQUIRED"
        elif is_melanoma and mel_prob < 0.50:
            pdf.set_fill_color(254, 243, 199)
            risk_color = (146, 92, 0)
            risk_text = "SCREENING FLAG - PROBABILITY BELOW 50%"
        elif is_melanoma:
            pdf.set_fill_color(254, 226, 226)
            risk_color = (185, 28, 28)
            risk_text = "SCREENING FLAG - MELANOMA PROBABILITY ABOVE THRESHOLD"
        else:
            pdf.set_fill_color(220, 252, 231)
            risk_color = (16, 130, 80)
            risk_text = "SCREENING RESULT - BELOW MELANOMA THRESHOLD"

        row(risk_text, h=11, size=13, bold=True, align="C", color=risk_color, fill=True)
        pdf.ln(2)

        row(f"Thresholded model output: {prediction}  |  Melanoma probability: {mel_prob:.2%}", h=6, size=10, align="C")
        row(f"Non-melanoma probability: {ben_prob:.2%}  |  Model score, not a diagnosis", h=6, size=10, align="C")
        if threshold is not None:
            row(f"Screening decision threshold: {threshold:.4f}", h=5, size=9, align="C")
        if focus_requires_review:
            row("Focus validation: review required because attention was predominantly outside the lesion", h=5, size=8, color=(146, 92, 0), align="C")
        pdf.ln(6)

        # ==============================================================
        # 1. RECOMMENDED NEXT STEP
        # ==============================================================
        self._section_header(pdf, "1", "Recommended Next Step", PW, LM, BM)
        next_steps = explanation.next_steps or (
            "Arrange evaluation by a qualified dermatologist. If clinically indicated, "
            "a biopsy with histopathology may be used to confirm the diagnosis."
        )
        wrap(next_steps, h=5, size=10)
        pdf.ln(4)

        # ==============================================================
        # 2. PLAIN-LANGUAGE EXPLANATION
        # ==============================================================
        self._section_header(pdf, "2", "What This Means", PW, LM, BM)
        wrap(explanation.summary, h=6, size=10, bold=True)
        pdf.ln(2)

        pdf.set_fill_color(240, 245, 255)
        row(f"Confidence Assessment: {explanation.confidence_assessment.upper()}", h=5, size=9, fill=True)
        pdf.ln(2)

        for line in explanation.reasoning:
            wrap(f"  - {self._safe(line)}", h=4, size=9)
            pdf.ln(1)

        if explanation.limitations:
            pdf.ln(2)
            for lim in explanation.limitations:
                wrap(f"  * {self._safe(lim)}", h=4, size=8, color=(120, 120, 120))
        pdf.ln(4)

        # ==============================================================
        # 3. IMAGE FINDINGS (ABCD)
        # ==============================================================
        self._section_header(pdf, "3", "Image Findings (ABCD Features)", PW, LM, BM)
        wrap(
            "The SwinV2 classifier produced the melanoma screening output from the image. "
            "These ABCD features and measurements were extracted separately from the "
            "SegFormer/refined lesion mask and are complementary findings, not classifier inputs.",
            h=4, size=8, color=(90, 90, 90),
        )
        pdf.ln(2)
        for name, feat in diag.clinical_features.items():
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_x(LM)
            pdf.safe_cell(45, 6, f"  {name.capitalize()}", ln=False)
            pdf.set_font("Helvetica", "", 10)
            pdf.safe_cell(PW - 45, 6, f"{feat.score_label}  (score: {feat.score_numeric:.3f})", ln=True)

        if diag.clinical_interpretations.get("diameter"):
            pdf.ln(2)
            wrap(f"  Diameter: {diag.clinical_interpretations['diameter']}", h=4, size=9)
        pdf.ln(4)

        # ==============================================================
        # 4. LESION MEASUREMENTS
        # ==============================================================
        self._section_header(pdf, "4", "Lesion Measurements", PW, LM, BM)
        seg = diag.segmentation
        lesion = diag.measurements.get("lesion", {})

        if seg.area_px:
            row(f"  Area: {seg.area_px:,} px", h=6, size=10)
        if seg.perimeter_px:
            row(f"  Perimeter: {seg.perimeter_px:.1f} px", h=6, size=10)
        if lesion.get("diameter_px"):
            row(f"  Diameter: {lesion['diameter_px']:,.1f} px", h=6, size=10)

        if lesion.get("physical_scale_available"):
            pdf.ln(2)
            row("  Physical measurements (calibrated):", h=6, size=10, bold=True)
            if lesion.get("diameter_mm") is not None:
                row(f"    Diameter: {lesion['diameter_mm']:.2f} mm", h=6, size=10)
            if lesion.get("area_mm2") is not None:
                row(f"    Area: {lesion['area_mm2']:.2f} mm2", h=6, size=10)
            if lesion.get("perimeter_mm") is not None:
                row(f"    Perimeter: {lesion['perimeter_mm']:.2f} mm", h=6, size=10)
            if diag.scale_calibration and diag.scale_calibration.calibration_valid:
                sc = diag.scale_calibration
                row(
                    f"    Calibration method: {sc.calibration_method.capitalize()}",
                    h=5, size=8, color=(100, 100, 100),
                )
                row(
                    f"    Calibration confidence: {sc.calibration_confidence:.0%}",
                    h=5, size=8, color=(100, 100, 100),
                )
                reference_px = sc.reference_diameter_px or sc.reference_length_px
                reference_mm = sc.reference_diameter_mm or sc.reference_length_mm
                if reference_px is not None and reference_mm is not None:
                    row(
                        f"    Reference length: {reference_px:.1f} px = {reference_mm:.2f} mm",
                        h=5, size=8, color=(100, 100, 100),
                    )
                if sc.pixels_per_mm is not None:
                    row(f"    Scale: {sc.pixels_per_mm:.2f} px/mm", h=5, size=8, color=(100, 100, 100))
                if sc.method == "ruler":
                    row(
                        f"    Ruler: {sc.orientation}, {sc.validated_tick_count} validated ticks; "
                        f"1 mm = {sc.tick_spacing_px or sc.reference_length_px:.2f} px",
                        h=5, size=8, color=(100, 100, 100),
                    )
            cleanup = lesion.get("mask_cleanup") or {}
            if cleanup:
                row(
                    f"    Mask cleanup: {cleanup.get('connected_components_before', 0)} -> "
                    f"{cleanup.get('connected_components_after', 0)} components; "
                    f"final area {cleanup.get('area_px', lesion.get('area_px', 0)):,} px",
                    h=5, size=8, color=(100, 100, 100),
                )
        else:
            wrap(
                "  Physical measurement: UNAVAILABLE. "
                f"Reason: {diag.scale_calibration.calibration_reason if diag.scale_calibration else 'reliable reference calibration was not provided'}. "
                "Pixel measurements remain available.",
                h=4, size=8, color=(120, 120, 120),
            )
        pdf.ln(4)

        # ==============================================================
        # 5. VISUALIZATIONS
        # ==============================================================
        self._section_header(pdf, "5", "Visualizations", PW, LM, BM)

        col_w = (PW - 5) / 2   # two equal columns with 5 mm gap
        img_h = 62              # fixed image height mm

        orig_path = getattr(diag.metadata, "image_path", None)
        overlay_path = getattr(seg, "overlay_path", None)
        orig_ok = bool(orig_path and Path(orig_path).exists())
        overlay_ok = bool(overlay_path and Path(overlay_path).exists())

        if orig_ok or overlay_ok:
            # Downsample before embedding.  Full-resolution dermoscopy images
            # can make a report tens of megabytes and can also cause slow,
            # awkward rendering in browser PDF viewers.
            with tempfile.TemporaryDirectory(prefix="meladetect_report_") as preview_dir:
                image_specs = []
                for label, source_path in (
                    (("Original Image", orig_path),) if orig_ok else tuple()
                ):
                    image_specs.append((label, source_path))
                if overlay_ok:
                    image_specs.append(("Segmentation Overlay", overlay_path))

                prepared = []
                for label, source_path in image_specs:
                    try:
                        from PIL import Image

                        with Image.open(source_path) as source:
                            source = source.convert("RGB")
                            source.thumbnail((1400, 1000), Image.Resampling.LANCZOS)
                            preview_path = Path(preview_dir) / f"{len(prepared)}.jpg"
                            source.save(preview_path, format="JPEG", quality=86, optimize=True)
                            prepared.append((label, str(preview_path), source.width, source.height))
                    except Exception:
                        logger.warning("Could not prepare report image: %s", source_path)

                if prepared:
                    gap = 5 if len(prepared) > 1 else 0
                    max_width = (PW - gap) / len(prepared)
                    max_height = 62
                    dimensions = []
                    for label, prepared_path, image_width, image_height in prepared:
                        ratio = image_width / max(image_height, 1)
                        width = min(max_width, max_height * ratio)
                        height = width / max(ratio, 1e-6)
                        dimensions.append((label, prepared_path, width, height))

                    required_height = max(height for _, _, _, height in dimensions) + 12
                    if pdf.get_y() + required_height > pdf.h - BM:
                        pdf.add_page()
                    y_label = pdf.get_y()
                    pdf.set_font("Helvetica", "I", 8)
                    for index, (label, _, width, _) in enumerate(dimensions):
                        x = LM + index * (max_width + gap)
                        pdf.set_xy(x, y_label)
                        pdf.safe_cell(max_width, 4, label, align="C")
                    y_img = y_label + 5
                    for index, (_, prepared_path, width, height) in enumerate(dimensions):
                        x_cell = LM + index * (max_width + gap)
                        x = x_cell + (max_width - width) / 2
                        try:
                            pdf.image(prepared_path, x=x, y=y_img, w=width, h=height)
                        except Exception:
                            logger.warning("Prepared report image could not be embedded")
                    pdf.set_y(y_img + max(height for _, _, _, height in dimensions) + 4)

        # Grad-CAM reliability note
        expl = diag.explainability
        ail = getattr(expl, "attention_inside_lesion", None)
        if ail is not None:
            if ail >= 0.30:
                note = "  Image focus check: The classifier's attention aligns with the lesion region."
            else:
                note = "  Image focus check: The classifier's attention is partially outside the lesion; the visual explanation requires review."
        else:
            note = "  Image focus check was not available."
        wrap(note, h=5, size=9)
        pdf.ln(4)

        # ==============================================================
        # 6. SUPPORTING MEDICAL REFERENCES
        # ==============================================================
        if self.include_evidence and evidence:
            self._section_header(pdf, "6", "Supporting Medical References", PW, LM, BM)
            for i, ev in enumerate(evidence, 1):
                title = _evidence_value(ev, "title", "Medical reference")
                source = _evidence_value(ev, "source", "")
                score = _evidence_value(ev, "relevance_score", 0.0)
                content = _evidence_value(ev, "content", "")
                row(f"  [{i}] {title}", h=5, size=9, bold=True)
                row(f"      Source: {source}  (relevance: {score:.2f})", h=4, size=8)
                content = content[:250] + "..." if len(content) > 250 else content
                wrap(f"      {self._safe(content)}", h=4, size=8)
                pdf.ln(2)
            pdf.ln(2)

        # ==============================================================
        # 7. TECHNICAL INFORMATION
        # ==============================================================
        self._section_header(pdf, "7", "Technical Information", PW, LM, BM)
        info_lines = [
            f"Classification model: {diag.pipeline.classification_model}",
            f"Segmentation model: {diag.pipeline.segmentation_model}",
            f"Feature extractor: {diag.pipeline.feature_extractor}",
            f"Pipeline version: {diag.pipeline.pipeline_version}",
            f"Preprocessing: hair removal={'yes' if diag.preprocessing.hair_removal else 'no'}, "
            f"illumination normalization={'yes' if diag.preprocessing.illumination_normalization else 'no'}",
            f"Request ID: {diag.metadata.request_id or analysis_id}",
        ]
        for line in info_lines:
            row(f"  {line}", h=4, size=8, color=(80, 80, 80))
        pdf.ln(6)

        # ==============================================================
        # 8. DISCLAIMER
        # ==============================================================
        pdf.set_fill_color(255, 248, 240)
        row("  IMPORTANT DISCLAIMER", h=5, size=8, bold=True, color=(140, 80, 20), fill=True)
        wrap(
            "  This system is an AI-based decision-support/research tool "
            "and does not provide a definitive medical diagnosis. It should not "
            "replace evaluation by a qualified dermatologist or healthcare "
            "professional. Seek professional medical evaluation for lesions "
            "that are new, changing, bleeding, painful, or otherwise unusual.",
            h=4, size=7, color=(130, 130, 130),
        )

        # Save PDF
        filename = f"{analysis_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf_path = self.output_dir / filename
        pdf.output(str(pdf_path))
        logger.info(f"PDF report saved: {pdf_path}")
        return str(pdf_path)

    # ==================================================================
    # Helpers
    # ==================================================================

    @staticmethod
    def _safe(value: Any) -> str:
        """Keep built-in Helvetica output within its Latin-1 character set."""
        text = (str(value)
                .replace("\u2022", "-").replace("\u2014", "-").replace("\u2013", "-")
                .replace("\u26a0", "Warning:").replace("\u2713", "[ok]")
                .replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"'))
        return text.encode("latin-1", errors="replace").decode("latin-1")

    def _section_header(self, pdf, number: str, title: str, pw: float, lm: float = 10, bottom_margin: float = 20):
        """Add a styled numbered section header to the PDF."""
        # Keep a heading with at least a small amount of following content;
        # otherwise long explanations can leave an orphaned heading at the
        # bottom of a page.
        if pdf.get_y() + 16 > pdf.h - bottom_margin:
            pdf.add_page()
        # Teal accent bar (3 mm wide)
        pdf.set_fill_color(13, 148, 136)
        pdf.rect(lm, pdf.get_y(), 3, 8, "F")

        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(13, 80, 76)
        pdf.set_x(lm)
        pdf.safe_cell(pw, 8, f"    {number}. {title}", ln=True)
        pdf.set_draw_color(200, 200, 200)
        pdf.line(lm, pdf.get_y(), lm + pw, pdf.get_y())
        pdf.ln(3)
        pdf.set_text_color(0, 0, 0)

    # Legacy compatibility alias
    _pdf_safe = _safe
