"""FastAPI transport layer for the melanoma analysis workflow."""

import io
import logging
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import yaml
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from PIL import Image, UnidentifiedImageError
PROJECT_ROOT = Path(__file__).resolve().parent.parent

env_path = PROJECT_ROOT / ".env"
if env_path.exists():
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()

from .auth import router as auth_router
from .admin import router as admin_router
from .schemas import (
    AnalysisResponse, AnalysisListItem, PhaseStatus,
    DiagnosisResultOut, DiagnosisInfoOut, FeatureScoreOut,
    SegmentationInfoOut, ExplainabilityInfoOut, PreprocessingInfoOut,
    PipelineInfoOut, MetadataInfoOut, MedicalEvidenceOut,
    ExplanationOut, ReportOut, PreprocessResponse, ScaleCalibrationOut,
)

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
UPLOADS_DIR = PROJECT_ROOT / "uploads"
REPORTS_DIR = OUTPUTS_DIR / "reports"
UPLOADS_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_MIME_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
ALLOWED_EXTENSIONS = {".jpeg", ".jpg", ".png", ".webp"}

app = FastAPI(
    title="Melanoma Orchestrator API",
    version="1.0.0",
    description="AI-assisted melanoma image analysis workflow",
)

@app.on_event("startup")
async def startup_event():
    from .auth import seed_admin
    await seed_admin()
cors_origins = [origin.strip() for origin in os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173",
).split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)
app.include_router(auth_router)
app.include_router(admin_router)
app.mount("/static/outputs", StaticFiles(directory=str(OUTPUTS_DIR)), name="outputs")
app.mount("/static/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

analyses_store: Dict[str, AnalysisResponse] = {}
_orchestrator_instance = None
_orchestrator_init_lock = threading.Lock()
from .db import get_db, ping_db


def _config() -> dict:
    try:
        with open(PROJECT_ROOT / "config.yaml", encoding="utf-8") as config_file:
            return yaml.safe_load(config_file) or {}
    except Exception:
        logger.exception("Configuration could not be loaded")
        return {}


def _resolve_project_path(value: Optional[str], default: Path) -> Path:
    """Resolve a configured path relative to the repository root."""
    if not value:
        return default
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _configured_model_paths() -> tuple[Path, Path]:
    """Return the checkpoints actually used by the diagnosis engine."""
    config = _config()
    paths = config.get("paths", {})
    checkpoints_dir = _resolve_project_path(
        paths.get("checkpoints"), PROJECT_ROOT / "checkpoints"
    )
    classification_path = _resolve_project_path(
        paths.get("classification_checkpoint"),
        PROJECT_ROOT / "checkpoints" / "best_swin_checkpoint.pth",
    )
    segmentation_path = _resolve_project_path(
        config.get("segmentation", {}).get("checkpoint"),
        checkpoints_dir / "segformer_best.pt",
    )
    return classification_path, segmentation_path


def _models_available() -> bool:
    """Check the configured classification and segmentation checkpoints."""
    return all(path.is_file() for path in _configured_model_paths())


def _get_orchestrator():
    global _orchestrator_instance
    if _orchestrator_instance is None:
        with _orchestrator_init_lock:
            if _orchestrator_instance is None:
                from src.orchestrator.agent import OrchestratorAgent
                _orchestrator_instance = OrchestratorAgent(str(PROJECT_ROOT / "config.yaml"))
                logger.info("Orchestrator initialized")
    return _orchestrator_instance


def _output_url(path: Optional[str], folder: str) -> Optional[str]:
    if not path:
        return None
    return f"/static/outputs/{folder}/{Path(path).name}"


def _workflow_to_response(state, original_image_url: Optional[str]) -> AnalysisResponse:
    phase_names = {
        "diagnosis": (1, "Diagnosis"),
        "medical_evidence": (2, "Medical Evidence"),
        "explanation": (3, "Explanation"),
        "report": (4, "Report Generation"),
    }
    phases = []
    for key, (number, name) in phase_names.items():
        phase = state.phases[key]
        phases.append(PhaseStatus(
            phase=number, name=name, status=phase.status,
            started_at=phase.started_at, completed_at=phase.completed_at,
            error=phase.error,
        ))

    diagnosis_out = None
    if state.diagnosis_result is not None:
        diag = state.diagnosis_result
        features = {
            name: FeatureScoreOut(
                name=feat.name,
                score_numeric=feat.score_numeric,
                score_label=feat.score_label,
            )
            for name, feat in diag.clinical_features.items()
        }
        diagnosis_out = DiagnosisResultOut(
            diagnosis=DiagnosisInfoOut(
                prediction=diag.diagnosis.prediction,
                confidence=diag.diagnosis.confidence,
            ),
            probabilities=diag.probabilities,
            melanoma_probability=diag.probabilities.get("melanoma"),
            non_melanoma_probability=diag.probabilities.get(
                "non_melanoma", diag.probabilities.get("not_melanoma")
            ),
            classification_threshold=diag.classification_threshold,
            measurements=diag.measurements,
            clinical_features=features,
            clinical_interpretations=diag.clinical_interpretations,
            segmentation=SegmentationInfoOut(
                status=diag.segmentation.status,
                mask_url=_output_url(diag.segmentation.mask_path, "masks"),
                overlay_url=_output_url(diag.segmentation.overlay_path, "masks"),
                area_px=diag.segmentation.area_px,
                perimeter_px=diag.segmentation.perimeter_px,
            ),
            explainability=ExplainabilityInfoOut(
                attention_inside_lesion=diag.explainability.attention_inside_lesion,
                attention_outside_lesion=diag.explainability.attention_outside_lesion,
                centroid_distance=diag.explainability.centroid_distance,
                mask_cam_iou=diag.explainability.mask_cam_iou,
            ),
            preprocessing=PreprocessingInfoOut(
                hair_removal=diag.preprocessing.hair_removal,
                illumination_normalization=diag.preprocessing.illumination_normalization,
            ),
            pipeline=PipelineInfoOut(
                classification_model=diag.pipeline.classification_model,
                segmentation_model=diag.pipeline.segmentation_model,
                feature_extractor=diag.pipeline.feature_extractor,
                pipeline_version=diag.pipeline.pipeline_version,
                classification_threshold=(
                    diag.pipeline.classification_threshold
                    if diag.pipeline.classification_threshold is not None
                    else diag.classification_threshold
                ),
            ),
            metadata=MetadataInfoOut(
                timestamp=diag.metadata.timestamp,
                image_id=diag.metadata.request_id or state.analysis_id,
            ),
            processing_status=diag.processing_status,
            warnings=diag.warnings,
        )

    # Scale calibration
    scale_cal_out = None
    if diagnosis_out and state.diagnosis_result and state.diagnosis_result.scale_calibration:
        sc = state.diagnosis_result.scale_calibration
        scale_cal_out = ScaleCalibrationOut(
            pixels_per_mm=sc.pixels_per_mm,
            method=sc.method,
            confidence=sc.confidence,
            reference_type=sc.reference_type,
            reference_diameter_px=sc.reference_diameter_px,
            reference_bbox_px=sc.reference_bbox_px,
            reference_diameter_mm=sc.reference_diameter_mm,
            detected=sc.detected,
            calibration_confidence=sc.calibration_confidence,
            calibration_valid=sc.calibration_valid,
            calibration_method=sc.calibration_method,
            reference_object_type=sc.reference_object_type,
            reference_length_px=sc.reference_length_px,
            reference_length_mm=sc.reference_length_mm,
            calibration_reason=sc.calibration_reason,
            scale_region=sc.scale_region,
            orientation=sc.orientation,
            angle_degrees=sc.angle_degrees,
            interval_mm=sc.interval_mm,
            tick_positions_px=sc.tick_positions_px,
            tick_spacing_px=sc.tick_spacing_px,
            validated_tick_count=sc.validated_tick_count,
            reference_points_px=sc.reference_points_px,
            reprojection_error_px=sc.reprojection_error_px,
            calibration_uncertainty=sc.calibration_uncertainty,
            warnings=sc.warnings,
            homography=sc.homography,
            axis_endpoints_px=sc.axis_endpoints_px,
            tick_points_px=sc.tick_points_px,
            interval_residuals_px=sc.interval_residuals_px,
        )
        diagnosis_out.scale_calibration = scale_cal_out

    evidence = None
    if state.retrieved_evidence is not None:
        evidence = [MedicalEvidenceOut(
            source=item.source,
            title=item.title,
            relevance_score=item.relevance_score,
            snippet=item.content[:300],
        ) for item in state.retrieved_evidence]

    explanation = None
    if state.explanation_result is not None:
        result = state.explanation_result
        explanation = ExplanationOut(
            summary=result.summary,
            reasoning=result.reasoning,
            grad_cam_url=_output_url(state.grad_cam_saved_path, "gradcam_samples"),
            confidence_assessment=result.confidence_assessment,
            next_steps=result.next_steps,
            limitations=result.limitations,
        )

    report = ReportOut()
    if state.report_result is not None and state.report_result.pdf_path:
        report.pdf_url = _output_url(state.report_result.pdf_path, "reports")

    return AnalysisResponse(
        analysis_id=state.analysis_id,
        status=state.overall_status,
        phases=phases,
        diagnosis=diagnosis_out,
        evidence=evidence,
        explanation=explanation,
        report=report,
        original_image_url=original_image_url,
        flags=state.flags,
        error_code=state.error_code,
        message=state.user_message,
        retryable=state.retryable,
    )


@app.exception_handler(RequestValidationError)
async def request_validation_handler(request: Request, exc: RequestValidationError):
    logger.warning("Request validation failed for %s", request.url.path)
    return JSONResponse(status_code=422, content={
        "error_code": "invalid_request",
        "message": "Please provide a supported image file.",
    })


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled API error for %s", request.url.path)
    return JSONResponse(status_code=500, content={
        "error_code": "internal_error",
        "message": "The request could not be completed. Please try again later.",
    })


@app.get("/")
def root():
    return {"message": "Melanoma Orchestrator API", "version": "1.0.0"}


@app.get("/api/health")
async def health():
    db = get_db()
    mongo_status = await ping_db() if db is not None else False
    count = len(analyses_store)
    if mongo_status:
        try:
            count = await db["analyses"].count_documents({})
        except Exception:
            pass
    return {
        "status": "healthy",
        "models_loaded": _models_available(),
        "mongodb_connected": mongo_status,
        "analyses_count": count,
    }


@app.get("/api/analyses", response_model=list[AnalysisListItem])
async def list_analyses():
    db = get_db()
    items = []
    if db is not None:
        try:
            cursor = db["analyses"].find({"diagnosis": {"$exists": True}}).sort("diagnosis.metadata.timestamp", -1)
            async for doc in cursor:
                try:
                    items.append(AnalysisListItem(
                        analysis_id=doc["analysis_id"],
                        image_name=doc.get("diagnosis", {}).get("metadata", {}).get("image_id") or doc["analysis_id"],
                        prediction=doc.get("diagnosis", {}).get("diagnosis", {}).get("prediction", "Unknown"),
                        confidence=doc.get("diagnosis", {}).get("diagnosis", {}).get("confidence", 0.0),
                        timestamp=doc.get("diagnosis", {}).get("metadata", {}).get("timestamp", datetime.now()),
                        status=doc.get("status", "completed"),
                    ))
                except Exception as e:
                    logger.warning(f"Skipping document {doc.get('analysis_id')} due to parse error: {e}")
            return items
        except Exception as e:
            logger.error(f"MongoDB error in list_analyses: {e}")
            # Fall back to in-memory store
            
    for analysis in analyses_store.values():
        if analysis.diagnosis:
            items.append(AnalysisListItem(
                analysis_id=analysis.analysis_id,
                image_name=analysis.diagnosis.metadata.image_id or analysis.analysis_id,
                prediction=analysis.diagnosis.diagnosis.prediction,
                confidence=analysis.diagnosis.diagnosis.confidence,
                timestamp=analysis.diagnosis.metadata.timestamp,
                status=analysis.status,
            ))
    return sorted(items, key=lambda item: item.timestamp, reverse=True)


@app.get("/api/analyses/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(analysis_id: str):
    db = get_db()
    if db is not None:
        try:
            doc = await db["analyses"].find_one({"analysis_id": analysis_id})
            if doc:
                return AnalysisResponse(**doc)
        except Exception as e:
            logger.error(f"MongoDB error in get_analysis: {e}")
            
    analysis = analyses_store.get(analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail={
            "error_code": "analysis_not_found",
            "message": "Analysis not found.",
        })
    return analysis


@app.post("/api/preprocess", response_model=PreprocessResponse)
async def preprocess_image(file: UploadFile = File(...)):
    """Run hair-removal preprocessing and return a before/after comparison."""
    preview_id = str(uuid.uuid4())[:8]
    extension = Path(file.filename or "").suffix.lower()
    if file.content_type not in ALLOWED_MIME_TYPES or extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail={
            "error_code": "unsupported_format",
            "message": "Unsupported image format.",
        })

    contents = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail={
            "error_code": "file_too_large",
            "message": "Image file is too large.",
        })

    try:
        with Image.open(io.BytesIO(contents)) as candidate:
            candidate.verify()
        with Image.open(io.BytesIO(contents)) as candidate:
            image = candidate.convert("RGB")
            image_array = np.asarray(image, dtype=np.uint8)
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(status_code=400, detail={
            "error_code": "image_decode_failed",
            "message": "The selected file is not a readable image.",
        })

    # Save original for comparison
    orig_path = UPLOADS_DIR / f"{preview_id}_original.png"
    Image.fromarray(image_array).save(orig_path, format="PNG")

    # Run hair removal only
    from src.data.preprocessing import DermoscopyPreprocessor
    preprocessor = DermoscopyPreprocessor(
        hair_removal=True, illumination_normalization=False,
    )
    preprocessed = await run_in_threadpool(preprocessor.process, image_array)

    # Detect hair pixels by comparing original and preprocessed
    import cv2
    gray_orig = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 17))
    blackhat = cv2.morphologyEx(gray_orig, cv2.MORPH_BLACKHAT, kernel)
    _, hair_mask = cv2.threshold(blackhat, 10, 255, cv2.THRESH_BINARY)
    hair_pixel_count = int((hair_mask > 0).sum())
    hair_detected = hair_pixel_count > 500  # meaningful threshold

    # Save preprocessed image
    preproc_path = UPLOADS_DIR / f"{preview_id}_preprocessed.png"
    Image.fromarray(preprocessed).save(preproc_path, format="PNG")

    return PreprocessResponse(
        preprocessed_url=f"/static/uploads/{preproc_path.name}",
        hair_detected=hair_detected,
        hair_pixel_count=hair_pixel_count,
        original_url=f"/static/uploads/{orig_path.name}",
    )


async def _save_analysis(analysis: AnalysisResponse):
    analyses_store[analysis.analysis_id] = analysis
    db = get_db()
    if db is not None:
        try:
            await db["analyses"].update_one(
                {"analysis_id": analysis.analysis_id},
                {"$set": analysis.model_dump(mode='json')},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Failed to save analysis {analysis.analysis_id} to MongoDB: {e}")

@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_image(
    file: UploadFile = File(...),
    scale_method: str = Form("auto"),
    scale_reference_mm: Optional[float] = Form(None),
    scale_reference_key: Optional[str] = Form(None),
):
    """Validate an image and run the existing orchestrator workflow."""
    analysis_id = str(uuid.uuid4())[:8]
    extension = Path(file.filename or "").suffix.lower()
    if file.content_type not in ALLOWED_MIME_TYPES or extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail={
            "error_code": "unsupported_format",
            "message": "Unsupported image format. Please upload a JPEG, JPG, PNG, or WEBP image.",
        })

    contents = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail={
            "error_code": "file_too_large",
            "message": "Image file is too large. Please upload an image no larger than 10 MB.",
        })

    file_path = UPLOADS_DIR / f"{analysis_id}.png"
    try:
        with Image.open(io.BytesIO(contents)) as candidate:
            candidate.verify()
        with Image.open(io.BytesIO(contents)) as candidate:
            image = candidate.convert("RGB")
            image.save(file_path, format="PNG", optimize=True)
            image_array = np.asarray(image, dtype=np.uint8)
    except (UnidentifiedImageError, OSError, ValueError):
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail={
            "error_code": "image_decode_failed",
            "message": "The selected file is not a readable image. Please choose another image.",
        })

    from src.engine.image_quality import check_image_quality
    quality = check_image_quality(image_array, **_config().get("quality", {}))
    if not quality.accepted:
        file_path.unlink(missing_ok=True)
        now = datetime.now()
        analysis = AnalysisResponse(
            analysis_id=analysis_id,
            status="image_quality_insufficient",
            phases=[
                PhaseStatus(phase=1, name="Diagnosis", status="failed", started_at=now, completed_at=now, error=quality.reason),
                PhaseStatus(phase=2, name="Medical Evidence", status="skipped"),
                PhaseStatus(phase=3, name="Explanation", status="skipped"),
                PhaseStatus(phase=4, name="Report Generation", status="skipped"),
            ],
            error_code="image_quality_insufficient",
            message=quality.reason,
            retryable=True,
            flags=quality.warnings,
        )
        await _save_analysis(analysis)
        return analysis

    if not _models_available():
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=503, detail={
            "error_code": "models_unavailable",
            "message": "The analysis service is temporarily unavailable. Please try again later.",
        })

    original_image_url = f"/static/uploads/{file_path.name}"
    try:
        state = await run_in_threadpool(
            _get_orchestrator().run,
            str(file_path),
            analysis_id=analysis_id,
            save_mask=True,
            scale_method=scale_method,
            scale_reference_mm=scale_reference_mm,
            scale_reference_key=scale_reference_key,
        )
        analysis = _workflow_to_response(state, original_image_url)
    except Exception:
        logger.exception("Orchestrator pipeline failed for request %s", analysis_id)
        now = datetime.now()
        analysis = AnalysisResponse(
            analysis_id=analysis_id,
            status="failed",
            phases=[
                PhaseStatus(phase=1, name="Diagnosis", status="failed", started_at=now, completed_at=now, error="Analysis could not be completed."),
                PhaseStatus(phase=2, name="Medical Evidence", status="skipped"),
                PhaseStatus(phase=3, name="Explanation", status="skipped"),
                PhaseStatus(phase=4, name="Report Generation", status="skipped"),
            ],
            original_image_url=original_image_url,
            error_code="pipeline_failed",
            message="Analysis could not be completed. Please try again with a clearer image.",
            retryable=True,
        )

    await _save_analysis(analysis)
    return analysis
