"""
Classification Evaluation
==========================

Loads the best Swin V2 checkpoint, runs inference on the test set,
and computes standard classification metrics with visualizations.

Supports both raw state_dict and full checkpoint formats.  When a full
checkpoint is available, the class mapping and threshold are read from
the checkpoint metadata to guarantee consistency with training.
"""

import json
from contextlib import nullcontext
from pathlib import Path
from typing import Dict

import yaml
import torch
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from torch.utils.data import DataLoader
from torch.amp import autocast
from tqdm import tqdm

from .model import SwinV2Classifier
from ..data.dataset import MelanomaClassificationDataset
from ..data.transforms import get_classification_transforms


def _normalise_text(value: str) -> str:
    return str(value).strip().lower().replace("-", "_").replace(" ", "_")


def _resolve_melanoma_idx(class_names: list[str]) -> int:
    """Return the index of the melanoma class within *class_names*."""
    for idx, name in enumerate(class_names):
        if _normalise_text(name) == "melanoma":
            return idx
    raise ValueError(f"No class named 'melanoma' in {class_names}")


@torch.no_grad()
def evaluate_classifier(config_path: str = "config.yaml") -> Dict:
    """
    Evaluate the trained classifier on the test set.

    Computes: Accuracy, Precision, Recall (Sensitivity), Specificity,
    F1, ROC-AUC, PR-AUC, Confusion Matrix.

    Saves report as JSON and confusion matrix as PNG.

    Args:
        config_path: Path to configuration file.

    Returns:
        Dictionary of computed metrics.
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

    # --------------- Load checkpoint ---------------
    checkpoint_setting = paths.get("classification_checkpoint")
    checkpoint_path = resolve_config_path(checkpoint_setting) if checkpoint_setting else (
        resolve_config_path("checkpoints") / "best_swin_checkpoint.pth"
    )

    raw = torch.load(checkpoint_path, map_location=device, weights_only=False)

    if isinstance(raw, dict) and "model_state_dict" in raw:
        # Full checkpoint from Kaggle notebook
        state_dict = raw["model_state_dict"]
        class_names = list(raw.get("class_names", cls_cfg["class_names"]))
        threshold = float(raw.get("threshold", cls_cfg.get("classification_threshold", 0.5)))
        ckpt_cfg = raw.get("model_config", {})
        model_name = ckpt_cfg.get("model_name", cls_cfg["model_name"])
        num_classes = ckpt_cfg.get("num_classes", cls_cfg["num_classes"])
    else:
        # Raw state_dict
        state_dict = raw
        class_names = list(cls_cfg["class_names"])
        threshold = float(cls_cfg.get("classification_threshold", 0.5))
        model_name = cls_cfg["model_name"]
        num_classes = cls_cfg["num_classes"]

    melanoma_idx = _resolve_melanoma_idx(class_names)
    non_melanoma_idx = 1 - melanoma_idx

    print(f"Class names: {class_names}")
    print(f"Melanoma index: {melanoma_idx}")
    print(f"Classification threshold: {threshold}")

    # --------------- Build model ---------------
    model = SwinV2Classifier(
        model_name=model_name,
        num_classes=num_classes,
        pretrained=False,
    )
    model.load_state_dict(state_dict)
    model = model.to(device)
    model.eval()

    # --------------- Test data ---------------
    test_tfm = get_classification_transforms("test", cls_cfg["img_size"])
    test_ds = MelanomaClassificationDataset(
        paths["classification_test"],
        test_tfm,
        class_names=class_names,
    )
    test_loader = DataLoader(
        test_ds,
        batch_size=cls_cfg["batch_size"],
        shuffle=False,
        num_workers=cls_cfg["num_workers"],
        pin_memory=True,
    )

    # --------------- Collect predictions ---------------
    all_labels = []
    all_melanoma_probs = []

    for images, labels in tqdm(test_loader, desc="Evaluating"):
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
        all_melanoma_probs.append(probs[:, melanoma_idx].cpu().numpy())

    y_true_raw = np.concatenate(all_labels)
    melanoma_probs = np.concatenate(all_melanoma_probs)

    # Convert labels to binary: 1 = melanoma, 0 = non-melanoma
    y_true_binary = (y_true_raw == melanoma_idx).astype(np.int64)
    y_pred_binary = (melanoma_probs >= threshold).astype(np.int64)

    # --------------- Compute metrics ---------------
    cm = confusion_matrix(y_true_binary, y_pred_binary, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()
    specificity = float(tn / (tn + fp)) if (tn + fp) > 0 else float("nan")

    try:
        roc_auc = float(roc_auc_score(y_true_binary, melanoma_probs))
    except ValueError:
        roc_auc = float("nan")

    try:
        pr_auc = float(average_precision_score(y_true_binary, melanoma_probs))
    except ValueError:
        pr_auc = float("nan")

    metrics = {
        "accuracy": float(accuracy_score(y_true_binary, y_pred_binary)),
        "precision": float(precision_score(y_true_binary, y_pred_binary, zero_division=0)),
        "recall_sensitivity": float(recall_score(y_true_binary, y_pred_binary, zero_division=0)),
        "specificity": specificity,
        "f1_score": float(f1_score(y_true_binary, y_pred_binary, zero_division=0)),
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
        "classification_threshold": threshold,
        "total_samples": int(len(y_true_binary)),
        "class_names": class_names,
        "melanoma_index": melanoma_idx,
        "confusion_matrix": cm.tolist(),
        "classification_report": classification_report(
            y_true_binary,
            y_pred_binary,
            target_names=["non_melanoma", "melanoma"],
            zero_division=0,
        ),
    }

    # --------------- Save report ---------------
    output_dir = Path(paths["outputs"])
    output_dir.mkdir(parents=True, exist_ok=True)

    report_path = output_dir / "classification_report.json"
    # Remove non-serializable items for JSON
    json_metrics = {k: v for k, v in metrics.items() if k != "classification_report"}
    with open(report_path, "w") as f:
        json.dump(json_metrics, f, indent=2)
    print(f"Classification report saved to: {report_path}")

    # --------------- Plot confusion matrix ---------------
    plt.figure(figsize=(8, 6))
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=["Non-melanoma", "Melanoma"],
        yticklabels=["Non-melanoma", "Melanoma"],
    )
    plt.xlabel("Predicted")
    plt.ylabel("True")
    plt.title(f"Confusion Matrix (threshold={threshold:.3f})")
    cm_path = output_dir / "confusion_matrix.png"
    plt.savefig(cm_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Confusion matrix saved to: {cm_path}")

    # --------------- Print summary ---------------
    print("\n--- Classification Results ---")
    for key in ["accuracy", "precision", "recall_sensitivity", "specificity",
                 "f1_score", "roc_auc", "pr_auc"]:
        print(f"  {key:>20s}: {metrics[key]:.4f}")
    print(f"  {'threshold':>20s}: {threshold:.4f}")
    print(f"\nConfusion matrix (rows=true, cols=predicted):")
    print(f"  TN={tn}  FP={fp}")
    print(f"  FN={fn}  TP={tp}")
    print(f"\n{metrics['classification_report']}")

    return metrics
