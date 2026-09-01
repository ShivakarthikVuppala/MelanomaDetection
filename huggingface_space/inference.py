"""Exact single-image inference implementation from the working notebook."""

from contextlib import nullcontext
from pathlib import Path

import albumentations as A
import numpy as np
import torch
from PIL import Image
from torch.amp import autocast
from albumentations.pytorch import ToTensorV2

from model import SwinV2Classifier


def _normalise_text(value):
    return str(value).strip().lower().replace("-", "_").replace(" ", "_")


class MelanomaPredictor:
    """Loads the supplied checkpoint once and applies notebook inference."""

    def __init__(self, checkpoint_path):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        # Keep optimizer/training tensors on CPU; only the model weights move
        # to the selected inference device below.
        checkpoint = torch.load(Path(checkpoint_path), map_location="cpu", weights_only=False)
        self.class_names = checkpoint["class_names"]
        preprocessing = checkpoint["preprocessing_config"]
        self.threshold = float(checkpoint.get("threshold", 0.5))
        model_config = checkpoint["model_config"]

        self.model = SwinV2Classifier(
            model_config["model_name"],
            num_classes=model_config["num_classes"],
            pretrained=False,
            dropout=model_config["dropout"],
        ).to(self.device)
        # Preserve the notebook's full-checkpoint loading mechanism.
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.eval()

        self.transform = A.Compose([
            A.Resize(height=int(preprocessing["image_size"]), width=int(preprocessing["image_size"])),
            A.Normalize(mean=tuple(preprocessing["mean"]), std=tuple(preprocessing["std"])),
            ToTensorV2(),
        ])
        self.melanoma_idx = next(
            i for i, name in enumerate(self.class_names)
            if _normalise_text(name) == "melanoma"
        )
        self.non_melanoma_idx = next(
            i for i, name in enumerate(self.class_names)
            if _normalise_text(name) in {"non_melanoma", "not_melanoma"}
        )

    @torch.no_grad()
    def predict(self, image):
        image = np.asarray(Image.fromarray(image.astype(np.uint8)).convert("RGB"))
        tensor = self.transform(image=image)["image"].unsqueeze(0).to(self.device)
        context = autocast(device_type="cuda", dtype=torch.float16) if self.device.type == "cuda" else nullcontext()
        with context:
            logits = self.model(tensor)
        probabilities = torch.softmax(logits.float(), dim=1)[0].cpu().numpy()

        melanoma_probability = float(probabilities[self.melanoma_idx])
        predicted_index = self.melanoma_idx if melanoma_probability >= self.threshold else self.non_melanoma_idx
        return {
            "predicted_class": self.class_names[predicted_index],
            "melanoma_probability": melanoma_probability,
            "non_melanoma_probability": float(probabilities[self.non_melanoma_idx]),
            "threshold_used": self.threshold,
            "probabilities": {name: float(p) for name, p in zip(self.class_names, probabilities)},
        }


def format_prediction(result):
    return (
        f"Prediction: {result['predicted_class']}\n"
        f"Melanoma probability: {result['melanoma_probability']:.4f}\n"
        f"Non-melanoma probability: {result['non_melanoma_probability']:.4f}\n"
        f"Threshold used: {result['threshold_used']:.4f}"
    )
