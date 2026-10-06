import yaml
from pathlib import Path
from src.agents.report_generator import ReportRenderer
from src.engine.diagnosis import DiagnosisResult, DiagnosisInfo, MetadataInfo, ScaleCalibrationInfo, ExplainabilityInfo, PreprocessingInfo, PipelineInfo, FeatureScore
from src.agents.explainability import ExplanationResult
import datetime

try:
    with open("config.yaml") as f:
        config = yaml.safe_load(f)
    diag = DiagnosisResult(
        diagnosis=DiagnosisInfo(prediction="Melanoma", confidence=0.85, status="completed", reason=""),
        probabilities={"melanoma": 0.85, "non_melanoma": 0.15},
        classification_threshold=0.5,
        measurements={"lesion": {"diameter_mm": 5.0}},
        clinical_features={"asymmetry": FeatureScore(name="asymmetry", score_numeric=0.8, score_label="high")},
        explainability=ExplainabilityInfo(),
        preprocessing=PreprocessingInfo(),
        pipeline=PipelineInfo(pipeline_version="1.0", segmentation_model="segformer", feature_extractor="abcd"),
        metadata=MetadataInfo(timestamp=datetime.datetime.now(), request_id="test", image_path="test.png")
    )
    exp = ExplanationResult(
        summary="Test summary",
        reasoning=["Reason 1"],
        evidence_citations=[],
        confidence_assessment="high",
        grad_cam_reliable=True,
        limitations=["None"]
    )
    renderer = ReportRenderer(config)
    result = renderer.generate(diag, [], exp, "test_analysis")
    print("PDF Path:", result.pdf_path)
except Exception as e:
    import traceback
    traceback.print_exc()
