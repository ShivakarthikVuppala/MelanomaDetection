"""
Inference Pipeline
===================

Orchestrates preprocessing, classification, segmentation, and feature
extraction. Classification and segmentation run in parallel since they
are independent. Returns raw inference outputs without building the
DiagnosisResult — that responsibility belongs to the Core Diagnosis Engine.
"""

from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional

import numpy as np
from PIL import Image

from ..classification.inference import SwinV2Predictor
from ..segmentation.segformer_wrapper import SegFormerSegmenter
from ..features.extractor import ABCFeatureExtractor
from ..features.base import FeatureResult
from ..data.preprocessing import DermoscopyPreprocessor


class InferencePipeline:
    """
    Inference pipeline with parallel execution:

        Step 0: Preprocess (sequential — must complete first)
        Step 1: Classify ─┐
                          ├── parallel on preprocessed image
        Step 2: Segment  ─┘
        Step 3: Extract Features (sequential — needs mask from Step 2)

        Each component is injected via constructor for testability.
    The pipeline returns raw outputs; schema construction is handled
    by CoreDiagnosisEngine.

    Args:
        classifier: SwinV2Predictor instance.
        segmenter: SegFormerSegmenter instance.
        locator: LesionLocator instance.
        feature_extractor: ABCFeatureExtractor instance.
        preprocessor: Optional DermoscopyPreprocessor instance.
    """

    def __init__(
        self,
        classifier: SwinV2Predictor,
        segmenter: SegFormerSegmenter,
        feature_extractor: ABCFeatureExtractor,
        preprocessor: Optional[DermoscopyPreprocessor] = None,
    ):
        self.classifier = classifier
        self.segmenter = segmenter
        self.feature_extractor = feature_extractor
        self.preprocessor = preprocessor

    def _classify(self, preprocessed: np.ndarray) -> dict:
        """Run classification on the preprocessed image."""
        return self.classifier.predict_array(preprocessed)

    def _segment(self, preprocessed: np.ndarray) -> np.ndarray:
        """Run SegFormer segmentation."""
        return self.segmenter.segment(preprocessed)

    def run(self, image_path: str) -> Dict:
        """
        Run the full inference pipeline on a single image.

        Classification and segmentation execute in parallel using
        a thread pool. Feature extraction runs after segmentation
        completes (it requires the mask).

        Args:
            image_path: Path to the dermoscopic image.

        Returns:
            Dict with keys:
                - classification: dict with prediction, confidence, probabilities
                - mask: np.ndarray binary mask (H, W)
                - features: dict[str, FeatureResult]
                - preprocessed_image: np.ndarray (H, W, 3) — the cleaned image
                - preprocessing_applied: dict of booleans
        """
        # Load image once
        image = np.array(Image.open(image_path).convert("RGB"))

        # 0. Preprocessing (hair removal, illumination normalization)
        if self.preprocessor is not None:
            preprocessed = self.preprocessor.process(image)
            hair_removed = self.preprocessor.get_hair_removed_image(image)
            preprocessing_applied = self.preprocessor.get_applied_steps()
        else:
            preprocessed = image
            hair_removed = image
            preprocessing_applied = {
                "hair_removal": False,
                "illumination_normalization": False,
            }

        # 1 & 2. Classification + Segmentation in PARALLEL
        with ThreadPoolExecutor(max_workers=2) as executor:
            cls_future = executor.submit(self._classify, preprocessed)
            seg_future = executor.submit(self._segment, preprocessed)

            cls_result = cls_future.result()
        mask = seg_future.result()
        probability_map = getattr(self.segmenter, "last_probability_map", None)

        # 3. ABC Feature Extraction (sequential — needs the mask)
        features = self.feature_extractor.extract_all(preprocessed, mask)

        return {
            "original_image": image,
            "classification": cls_result,
            "mask": mask,
            "probability_map": probability_map,
            "features": features,
            "preprocessed_image": preprocessed,
            "hair_removed_image": hair_removed,
            "preprocessing_applied": preprocessing_applied,
        }
