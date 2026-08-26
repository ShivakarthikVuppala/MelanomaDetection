"""
Single-Image Inference
=======================

Provides a simple predictor class that loads the trained Swin V2
checkpoint and runs inference on individual images.

Supports two checkpoint formats:
  1. Raw ``state_dict`` (backward compatible)
  2. Full checkpoint dict produced by the Kaggle training notebook
     (contains ``model_state_dict``, ``class_to_idx``, ``class_names``,
     ``preprocessing_config``, and optionally ``threshold``).
"""

from contextlib import nullcontext
from pathlib import Path
from typing import Optional

import numpy as np
import torch
from torch.amp import autocast
from PIL import Image

from .model import SwinV2Classifier
from ..data.transforms import get_classification_transforms


def _normalise_text(value: str) -> str:
    """Lowercase, replace hyphens/spaces with underscores."""
    return str(value).strip().lower().replace("-", "_").replace(" ", "_")


class SwinV2Predictor:
    """
    Single-image predictor for melanoma classification.

    Loads the trained checkpoint and provides a simple ``.predict()`` interface.
    Handles all preprocessing internally.

    The predictor reads class mapping and threshold from the checkpoint when
    available (full checkpoint format).  When the checkpoint is a raw state_dict,
    it falls back to the ``class_names``, ``melanoma_class_name``, and
    ``classification_threshold`` arguments.

    Args:
        checkpoint_path: Path to the trained model weights (.pth).
        model_name: timm model identifier.
        img_size: Input image size for preprocessing.
        device: Torch device (auto-detected if None).
        class_names: Fallback class names if checkpoint has no metadata.
        melanoma_class_name: Name of the melanoma class.
        classification_threshold: Fallback threshold if checkpoint has no
            saved threshold.
    """

    def __init__(
        self,
        checkpoint_path: str,
        model_name: str = "swinv2_base_window12to16_192to256",
        img_size: int = 256,
        device: torch.device = None,
        class_names: Optional[list[str]] = None,
        melanoma_class_name: str = "melanoma",
        classification_threshold: float = 0.5,
    ):
        self.device = device or torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        self.img_size = img_size

        # Load checkpoint (support both raw state_dict and full checkpoint)
        raw = torch.load(
            checkpoint_path, map_location=self.device, weights_only=False
        )

        if isinstance(raw, dict) and "model_state_dict" in raw:
            # --- Full checkpoint format (from Kaggle notebook) ---
            state_dict = raw["model_state_dict"]
            checkpoint_names = raw.get("class_names")
            if checkpoint_names is None and raw.get("class_to_idx"):
                checkpoint_names = [name for name, _ in sorted(raw["class_to_idx"].items(), key=lambda item: item[1])]
            self.class_names = list(checkpoint_names or class_names or ["melanoma", "non_melanoma"])
            # Checkpoint threshold ALWAYS wins over config/constructor arg.
            # The notebook saves it as "threshold"; older checkpoints may use
            # "classification_threshold".  Fall back to the constructor arg
            # only when the checkpoint carries neither key.
            checkpoint_threshold = raw.get("threshold", raw.get("classification_threshold"))
            self.classification_threshold = float(
                checkpoint_threshold if checkpoint_threshold is not None
                else (classification_threshold if classification_threshold is not None else 0.5)
            )
            ckpt_config = raw.get("model_config", {})
            model_name = ckpt_config.get("model_name", model_name)
            num_classes = ckpt_config.get("num_classes", len(self.class_names))
            dropout = ckpt_config.get("dropout", 0.3)
        else:
            # --- Raw state_dict format (backward compatible) ---
            state_dict = raw
            self.class_names = list(class_names or ["melanoma", "non_melanoma"])
            self.classification_threshold = float(
                classification_threshold if classification_threshold is not None else 0.5
            )
            num_classes = len(self.class_names)
            dropout = 0.3

        # Resolve melanoma index by name lookup
        self.melanoma_class_name = next(
            (name for name in self.class_names if _normalise_text(name) == "melanoma"),
            melanoma_class_name,
        )
        melanoma_candidates = [
            i for i, name in enumerate(self.class_names)
            if _normalise_text(name) == "melanoma"
        ]
        if not melanoma_candidates:
            raise ValueError(
                f"No class named 'melanoma' found in class_names: {self.class_names}"
            )
        self.melanoma_idx = melanoma_candidates[0]
        if len(self.class_names) != 2 or num_classes != 2:
            raise ValueError(
                "SwinV2Predictor expects exactly two classes for thresholded "
                f"melanoma inference; got class_names={self.class_names}, "
                f"num_classes={num_classes}."
            )
        self.non_melanoma_idx = next(
            idx for idx in range(len(self.class_names)) if idx != self.melanoma_idx
        )

        if not 0.0 < self.classification_threshold < 1.0:
            raise ValueError("Classification threshold must be between 0 and 1.")

        # Build and load model
        self.model = SwinV2Classifier(
            model_name=model_name,
            num_classes=num_classes,
            pretrained=False,
            dropout_rate=dropout,
        )
        self.model.load_state_dict(state_dict)
        self.model = self.model.to(self.device)
        self.model.eval()

        # Preprocessing
        self.transform = get_classification_transforms("val", img_size)

    @torch.no_grad()
    def predict(self, image_path: str) -> dict:
        """
        Run classification on a single dermoscopic image from file path.

        Args:
            image_path: Path to the input image.

        Returns:
            Dict with keys:
                - prediction (str): Class name (capitalised)
                - confidence (float): Confidence percentage (0–100)
                - probabilities (dict): {class_name: float}
                - classification_threshold (float): Threshold used
                - melanoma_probability (float): Probability of melanoma
        """
        image = np.array(Image.open(image_path).convert("RGB"))
        return self._classify(image)

    @torch.no_grad()
    def predict_array(self, image: np.ndarray) -> dict:
        """
        Run classification on a preprocessed image array.

        Args:
            image: RGB image as numpy array (H, W, 3), uint8.

        Returns:
            Same dict format as predict().
        """
        return self._classify(image)

    def _classify(self, image: np.ndarray) -> dict:
        """Shared classification logic for both predict() and predict_array()."""
        transformed = self.transform(image=image)
        tensor = transformed["image"].unsqueeze(0).to(self.device)

        # Forward pass
        # Float16 autocast is a CUDA optimization.  On CPU it can silently
        # produce unsupported operations or native crashes, so use full
        # precision there.
        autocast_context = (
            autocast(device_type="cuda", dtype=torch.float16)
            if self.device.type == "cuda"
            else nullcontext()
        )
        with autocast_context:
            logits = self.model(tensor)

        probs = torch.softmax(logits.float(), dim=1).squeeze(0).cpu().numpy()

        melanoma_prob = float(probs[self.melanoma_idx])
        pred_idx = (
            self.melanoma_idx
            if melanoma_prob >= self.classification_threshold
            else self.non_melanoma_idx
        )
        pred_label = "Melanoma" if pred_idx == self.melanoma_idx else "Non-melanoma"
        confidence = float(probs[pred_idx]) * 100.0

        return {
            "prediction": pred_label.capitalize(),
            "confidence": round(confidence, 2),
            "probabilities": {
                name: round(float(p), 4)
                for name, p in zip(self.class_names, probs)
            },
            "melanoma_probability": round(melanoma_prob, 4),
            "classification_threshold": self.classification_threshold,
        }
