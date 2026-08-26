"""
Metric Computation Utilities
==============================

Centralized metric functions used by both classification
and segmentation evaluation modules.
"""

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    average_precision_score,
    roc_auc_score,
    confusion_matrix,
)


def compute_classification_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: np.ndarray,
) -> dict:
    """
    Compute all classification metrics.

    Args:
        y_true: Ground truth labels (0 or 1).
        y_pred: Predicted labels (0 or 1).
        y_prob: Predicted probabilities for positive class.

    Returns:
        Dict of metric name → value.
    """
    try:
        auroc = float(roc_auc_score(y_true, y_prob))
    except ValueError:
        # AUROC is undefined when the evaluation subset contains one class.
        # Preserve the report shape and make the limitation explicit via NaN.
        auroc = float("nan")
    try:
        pr_auc = float(average_precision_score(y_true, y_prob))
    except ValueError:
        pr_auc = float("nan")

    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1_score": float(f1_score(y_true, y_pred, zero_division=0)),
        "auroc": auroc,
        "pr_auc": pr_auc,
    }


def compute_segmentation_metrics(
    pred_mask: np.ndarray, gt_mask: np.ndarray
) -> dict:
    """
    Compute segmentation metrics for a single image pair.

    Args:
        pred_mask: Predicted binary mask.
        gt_mask: Ground truth binary mask.

    Returns:
        Dict with dice, iou, precision, recall.
    """
    pred = pred_mask.astype(bool)
    gt = gt_mask.astype(bool)

    intersection = np.logical_and(pred, gt).sum()
    union = np.logical_or(pred, gt).sum()

    tp = intersection
    fp = np.logical_and(pred, ~gt).sum()
    fn = np.logical_and(~pred, gt).sum()

    dice = 2.0 * tp / max(pred.sum() + gt.sum(), 1)
    iou = tp / max(union, 1)
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)

    return {
        "dice": float(dice),
        "iou": float(iou),
        "precision": float(precision),
        "recall": float(recall),
    }


def plot_confusion_matrix(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    class_names: list,
    save_path: str,
):
    """Plot and save a confusion matrix heatmap."""
    cm = confusion_matrix(y_true, y_pred)

    plt.figure(figsize=(8, 6))
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=class_names,
        yticklabels=class_names,
    )
    plt.xlabel("Predicted")
    plt.ylabel("True")
    plt.title("Confusion Matrix")
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
