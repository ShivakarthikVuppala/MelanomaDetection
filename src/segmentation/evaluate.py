"""
Segmentation Evaluation
========================

Evaluates SegFormer segmentation quality against ground-truth masks
using Dice, IoU, Precision, and Recall metrics.
"""

import json
from pathlib import Path
from typing import Dict, List

import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from tqdm import tqdm


def dice_coefficient(pred: np.ndarray, gt: np.ndarray) -> float:
    """Compute Dice Similarity Coefficient."""
    intersection = np.logical_and(pred, gt).sum()
    total = pred.sum() + gt.sum()
    if total == 0:
        return 1.0  # both empty
    return float(2.0 * intersection / total)


def iou_score(pred: np.ndarray, gt: np.ndarray) -> float:
    """Compute Intersection over Union."""
    intersection = np.logical_and(pred, gt).sum()
    union = np.logical_or(pred, gt).sum()
    if union == 0:
        return 1.0
    return float(intersection / union)


def pixel_precision(pred: np.ndarray, gt: np.ndarray) -> float:
    """Compute pixel-level precision."""
    tp = np.logical_and(pred, gt).sum()
    fp = np.logical_and(pred, ~gt.astype(bool)).sum()
    if tp + fp == 0:
        return 0.0
    return float(tp / (tp + fp))


def pixel_recall(pred: np.ndarray, gt: np.ndarray) -> float:
    """Compute pixel-level recall."""
    tp = np.logical_and(pred, gt).sum()
    fn = np.logical_and(~pred.astype(bool), gt).sum()
    if tp + fn == 0:
        return 0.0
    return float(tp / (tp + fn))


def evaluate_segmentation(
    segmenter,
    locator,
    img_dir: str,
    mask_dir: str,
    output_dir: str,
    max_samples: int = None,
) -> Dict:
    """
    Evaluate segmentation on a dataset with ground-truth masks.

    Args:
        segmenter: SegFormerSegmenter instance.
        locator: LesionLocator instance.
        img_dir: Path to test images.
        mask_dir: Path to ground-truth masks.
        output_dir: Path to save reports and visualizations.
        max_samples: Limit evaluation to N samples (for quick testing).

    Returns:
        Dictionary with per-sample and aggregate metrics.
    """
    img_dir = Path(img_dir)
    mask_dir = Path(mask_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    valid_ext = {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}

    # Match image-mask pairs by filename stem
    mask_stems = {}
    for f in mask_dir.iterdir():
        if f.suffix.lower() in valid_ext:
            mask_stems[f.stem] = f

    pairs = []
    for f in sorted(img_dir.iterdir()):
        if f.suffix.lower() in valid_ext and f.stem in mask_stems:
            pairs.append((f, mask_stems[f.stem]))

    if max_samples is not None:
        pairs = pairs[:max_samples]

    if not pairs:
        raise ValueError(
            f"No image/mask pairs found for segmentation evaluation in {img_dir} and {mask_dir}."
        )

    # Evaluate
    results = []
    for img_path, gt_path in tqdm(pairs, desc="Segmentation Eval"):
        image = np.array(Image.open(img_path).convert("RGB"))
        gt_mask = np.array(Image.open(gt_path).convert("L"))
        gt_mask = (gt_mask > 127).astype(np.uint8)

        # Locate and segment
        if locator:
            bbox = locator.locate(image)
            # SegFormer does not currently require bounding box prompts
        pred_mask = segmenter.segment(image)

        # Compute metrics
        sample = {
            "name": img_path.stem,
            "dice": dice_coefficient(pred_mask, gt_mask),
            "iou": iou_score(pred_mask, gt_mask),
            "precision": pixel_precision(pred_mask, gt_mask),
            "recall": pixel_recall(pred_mask, gt_mask),
        }
        results.append(sample)

    # Aggregate
    metrics = ["dice", "iou", "precision", "recall"]
    aggregate = {}
    for m in metrics:
        values = [r[m] for r in results]
        aggregate[m] = {
            "mean": float(np.mean(values)),
            "std": float(np.std(values)),
            "min": float(np.min(values)),
            "max": float(np.max(values)),
        }

    report = {
        "total_samples": len(results),
        "aggregate": aggregate,
        "per_sample": results,
    }

    # Save report
    report_path = output_dir / "segmentation_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Segmentation report saved to: {report_path}")

    # Print summary
    print("\n--- Segmentation Results ---")
    for m in metrics:
        print(f"  {m:>12s}: {aggregate[m]['mean']:.4f} ± {aggregate[m]['std']:.4f}")

    return report
