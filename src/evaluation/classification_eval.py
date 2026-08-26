"""
Classification Evaluation Report
==================================

Loads the best classifier checkpoint, evaluates on the test set,
and produces a JSON report with confusion matrix visualization.
"""

import json
from contextlib import nullcontext
from pathlib import Path

import yaml
import numpy as np
import torch
from torch.utils.data import DataLoader
from torch.amp import autocast
from tqdm import tqdm

from ..classification.model import SwinV2Classifier
from ..data.dataset import MelanomaClassificationDataset
from ..data.transforms import get_classification_transforms
from .metrics import compute_classification_metrics, plot_confusion_matrix


def run_classification_evaluation(config_path: str = "config.yaml") -> dict:
    """
    Full classification evaluation pipeline.

    Loads best checkpoint, runs on test set, computes metrics,
    saves JSON report and confusion matrix PNG.

    Args:
        config_path: Path to config.yaml.

    Returns:
        Dict of metrics.
    """
    config_file = Path(config_path).resolve()
    project_root = config_file.parent
    with open(config_file) as f:
        config = yaml.safe_load(f)

    cls_cfg = config["classification"]
    paths = config["paths"]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def resolve_config_path(value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else project_root / path

    # Load checkpoint (support both raw state_dict and full checkpoint)
    checkpoint_setting = paths.get("classification_checkpoint")
    ckpt_path = resolve_config_path(checkpoint_setting) if checkpoint_setting else (
        resolve_config_path("codex-model") / "best_swin_checkpoint.pth"
    )
    raw = torch.load(ckpt_path, map_location=device, weights_only=False)

    if isinstance(raw, dict) and "model_state_dict" in raw:
        state_dict = raw["model_state_dict"]
        class_names = list(raw.get("class_names", cls_cfg["class_names"]))
        threshold = float(raw.get("threshold", raw.get("classification_threshold", cls_cfg.get("classification_threshold", 0.5))))
        model_cfg = raw.get("model_config", {})
        model_name = model_cfg.get("model_name", cls_cfg["model_name"])
        num_classes = int(model_cfg.get("num_classes", len(class_names)))
        dropout_rate = float(model_cfg.get("dropout", 0.3))
    else:
        state_dict = raw
        class_names = list(cls_cfg["class_names"])
        threshold = float(cls_cfg.get("classification_threshold", 0.5))
        model_name = cls_cfg["model_name"]
        num_classes = cls_cfg["num_classes"]
        dropout_rate = 0.3

    # Resolve melanoma index by name
    melanoma_idx = next(
        i for i, n in enumerate(class_names)
        if n.strip().lower().replace("-", "_").replace(" ", "_") == "melanoma"
    )

    model = SwinV2Classifier(
        model_name=model_name,
        num_classes=num_classes,
        pretrained=False,
        dropout_rate=dropout_rate,
    )
    model.load_state_dict(state_dict)
    model = model.to(device)
    model.eval()

    # Test data
    test_tfm = get_classification_transforms("test", cls_cfg["img_size"])
    test_ds = MelanomaClassificationDataset(
        str(resolve_config_path(paths["classification_test"])), test_tfm, class_names=class_names,
    )
    test_loader = DataLoader(
        test_ds, batch_size=cls_cfg["batch_size"],
        shuffle=False, num_workers=cls_cfg["num_workers"], pin_memory=True,
    )

    # Inference
    all_labels, all_preds, all_probs = [], [], []
    with torch.no_grad():
        for images, labels in tqdm(test_loader, desc="Classification Eval"):
            images = images.to(device, non_blocking=True)
            autocast_context = (
                autocast(device_type="cuda", dtype=torch.float16)
                if device.type == "cuda"
                else nullcontext()
            )
            with autocast_context:
                logits = model(images)
            probs = torch.softmax(logits.float(), dim=1)
            all_labels.append(labels.numpy())
            melanoma_probs = probs[:, melanoma_idx]
            all_preds.append(
                (melanoma_probs >= threshold).to(torch.int64).cpu().numpy()
            )
            all_probs.append(melanoma_probs.cpu().numpy())

    y_true = np.concatenate(all_labels)
    y_pred = np.concatenate(all_preds)
    y_prob = np.concatenate(all_probs)

    # Metrics
    # Dataset labels follow the checkpoint class order; convert them to a
    # stable binary convention where melanoma is the positive class.
    y_true = (y_true == melanoma_idx).astype(np.int64)
    metrics = compute_classification_metrics(y_true, y_pred, y_prob)
    metrics["total_samples"] = int(len(y_true))
    metrics["classification_threshold"] = threshold

    # Save
    output_dir = resolve_config_path(paths["outputs"])
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "classification_report.json", "w") as f:
        json.dump(metrics, f, indent=2)

    plot_confusion_matrix(
        y_true, y_pred, ["non_melanoma", "melanoma"],
        str(output_dir / "confusion_matrix.png"),
    )

    print("\n--- Classification Results ---")
    for k in ["accuracy", "precision", "recall", "f1_score", "auroc"]:
        print(f"  {k:>12s}: {metrics[k]:.4f}")

    return metrics
