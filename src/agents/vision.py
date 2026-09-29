"""Vision Agent: coordinates deterministic ML/CV tools and returns typed observations."""
from __future__ import annotations
from typing import Any, Dict, Optional
import numpy as np
from PIL import Image
from .state import ABCDEFeature, CaseState, Measurement

class VisionAgent:
    name = "vision"
    def __init__(self, config_path: str = "config.yaml", engine: Any = None):
        self.config_path, self._engine = config_path, engine

    def _engine_instance(self):
        if self._engine is None:
            from ..engine.engine import CoreDiagnosisEngine
            self._engine = CoreDiagnosisEngine(self.config_path)
        return self._engine

    def validate_image(self, state: CaseState, quality_config: Optional[Dict[str, Any]] = None) -> CaseState:
        from ..engine.image_quality import check_image_quality
        try:
            with Image.open(state.image_path) as image:
                rgb = np.asarray(image.convert("RGB"))
                state.image_metadata = {"width": image.width, "height": image.height, "mode": "RGB"}
            result = check_image_quality(rgb, **(quality_config or {}))
            state.image_quality = {"accepted": result.accepted, "reason": result.reason, "warnings": list(result.warnings)}
            state.uncertainty.measurement = 1.0 if result.accepted else 0.0
            state.record(self.name, "validate_image", "accepted" if result.accepted else "rejected", "image_quality", state.image_quality, tool=True)
        except Exception:
            state.image_quality = {"accepted": False, "reason": "The image could not be read.", "warnings": []}
            state.record(self.name, "validate_image", "failed", "image_decode", tool=True)
        return state

    def analyze(self, state: CaseState, *, save_mask: bool, scale_method: str = "auto", scale_reference_mm: Optional[float] = None, scale_reference_key: Optional[str] = None) -> CaseState:
        """Run existing Swin, SegFormer, CV, calibration and optional Grad-CAM tools once."""
        result = self._engine_instance().diagnose(state.image_path, save_mask=save_mask, request_id=state.analysis_id, scale_method=scale_method, scale_reference_mm=scale_reference_mm, scale_reference_key=scale_reference_key)
        state.diagnosis_result = result
        state.classification = {"prediction": result.diagnosis.prediction, "confidence": result.diagnosis.confidence, "probabilities": result.probabilities}
        state.uncertainty.classification = float(result.diagnosis.confidence) / 100.0
        lesion = result.measurements.get("lesion", {})
        state.segmentation = {"status": result.segmentation.status, "area_px": result.segmentation.area_px, "perimeter_px": result.segmentation.perimeter_px, "mask_path": result.segmentation.mask_path, "mask_consistency": self._mask_consistency(result)}
        state.uncertainty.segmentation = state.segmentation["mask_consistency"]
        state.gradcam = result.explainability.model_dump() if hasattr(result.explainability, "model_dump") else {}
        alignment = state.gradcam.get("attention_inside_lesion")
        state.gradcam["alignment_reliable"] = alignment is not None and alignment >= 0.30
        state.pixel_measurements["diameter"] = Measurement(self._number(lesion.get("diameter_px")), "pixels", False, lesion.get("measurement_method", "maximum_feret_diameter"))
        state.pixel_measurements["area"] = Measurement(self._number(lesion.get("area_px")), "px2", False)
        calibration = result.scale_calibration.model_dump() if result.scale_calibration else {}
        state.calibration = calibration
        calibrated = bool(calibration.get("calibration_valid"))
        state.uncertainty.calibration = float(calibration.get("calibration_confidence", 0.0)) if calibrated else 0.0
        state.physical_measurements["diameter"] = Measurement(self._number(lesion.get("diameter_mm")) if calibrated else None, "mm", calibrated, calibration.get("calibration_method", "none"), None if calibrated else calibration.get("calibration_reason", "No valid calibration"))
        self._build_authoritative_abcde(state, result)
        state.record(self.name, "analyze_image", "completed", "vision_observation", {"classification_confidence": result.diagnosis.confidence, "segmentation_quality": state.segmentation["mask_consistency"], "calibrated": calibrated}, tool=True)
        return state

    @staticmethod
    def _number(value: Any) -> Optional[float]:
        try: return float(value) if value is not None else None
        except (TypeError, ValueError): return None

    @staticmethod
    def _mask_consistency(result: Any) -> float:
        area, measured = result.segmentation.area_px or 0, result.measurements.get("lesion", {}).get("area_px") or 0
        return 0.0 if area <= 0 or measured <= 0 else max(0.0, 1.0 - abs(area - measured) / max(area, measured))

    def _build_authoritative_abcde(self, state: CaseState, result: Any) -> None:
        for criterion, key in {"A": "asymmetry", "B": "border", "C": "color"}.items():
            feature = result.clinical_features.get(key)
            state.abcde[criterion] = ABCDEFeature(criterion, "available", result.measurements.get(key, {}), feature.score_label if feature else None)
        mm, px = state.physical_measurements["diameter"], state.pixel_measurements["diameter"]
        raw = {"pixel_diameter": px.__dict__, "physical_diameter": mm.__dict__}
        interpretation = "Calibrated physical diameter is available." if mm.calibrated and mm.value is not None else "Physical diameter is unavailable; pixel size must not be compared with millimetre thresholds."
        state.abcde["D"] = ABCDEFeature("D", "available", raw, interpretation, mm.reason_unavailable)
        state.uncertainty.abcde = min(state.uncertainty.segmentation, state.uncertainty.calibration or 0.5)
