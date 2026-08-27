"""Ground-truth evaluation for calibration and lesion measurement."""

from pathlib import Path
from typing import Iterable, Optional

import cv2
import numpy as np


def _errors(predicted: Iterable[float], truth: Iterable[float]) -> np.ndarray:
    pred, actual = np.asarray(list(predicted), dtype=float), np.asarray(list(truth), dtype=float)
    if pred.shape != actual.shape or pred.size == 0:
        raise ValueError("predictions and ground truth must have the same non-empty shape")
    return pred - actual


def segmentation_scores(predicted_mask: np.ndarray, ground_truth_mask: np.ndarray) -> dict:
    pred, truth = np.asarray(predicted_mask) > 0, np.asarray(ground_truth_mask) > 0
    if pred.shape != truth.shape:
        raise ValueError("predicted and ground-truth masks must have the same shape")
    intersection = float(np.logical_and(pred, truth).sum())
    union = float(np.logical_or(pred, truth).sum())
    dice = 2.0 * intersection / max(float(pred.sum() + truth.sum()), 1.0)
    return {"dice": round(dice, 6), "iou": round(intersection / max(union, 1.0), 6)}


def evaluate_measurements(
    predicted_mm: Iterable[float], ground_truth_mm: Iterable[float],
    predicted_calibration_ppm: Optional[Iterable[float]] = None,
    ground_truth_calibration_ppm: Optional[Iterable[float]] = None,
    predicted_masks: Optional[Iterable[np.ndarray]] = None,
    ground_truth_masks: Optional[Iterable[np.ndarray]] = None,
) -> dict:
    """Return MAE/RMSE/relative-error and tolerance coverage.

    Calibration and lesion errors are reported independently so a good scale
    cannot hide an inflated or eroded lesion mask.
    """
    predicted_mm, ground_truth_mm = list(predicted_mm), list(ground_truth_mm)
    lesion_error = _errors(predicted_mm, ground_truth_mm)
    truth = np.asarray(ground_truth_mm, dtype=float)
    result = {
        "lesion_diameter_mae_mm": round(float(np.mean(np.abs(lesion_error))), 6),
        "lesion_diameter_rmse_mm": round(float(np.sqrt(np.mean(lesion_error ** 2))), 6),
        "lesion_diameter_median_absolute_error_mm": round(float(np.median(np.abs(lesion_error))), 6),
        "lesion_diameter_median_relative_error": round(float(np.median(np.abs(lesion_error) / np.maximum(np.abs(truth), 1e-9))), 6),
        "within_0_5_mm": round(float(np.mean(np.abs(lesion_error) <= 0.5)), 6),
        "within_1_mm": round(float(np.mean(np.abs(lesion_error) <= 1.0)), 6),
        "sample_count": int(lesion_error.size),
    }
    if predicted_calibration_ppm is not None and ground_truth_calibration_ppm is not None:
        predicted_calibration_ppm, ground_truth_calibration_ppm = list(predicted_calibration_ppm), list(ground_truth_calibration_ppm)
        calibration_error = _errors(predicted_calibration_ppm, ground_truth_calibration_ppm)
        calibration_truth = np.asarray(ground_truth_calibration_ppm, dtype=float)
        result.update({
            "calibration_mae_ppm": round(float(np.mean(np.abs(calibration_error))), 6),
            "calibration_rmse_ppm": round(float(np.sqrt(np.mean(calibration_error ** 2))), 6),
            "calibration_relative_error": round(float(np.mean(np.abs(calibration_error) / np.maximum(np.abs(calibration_truth), 1e-9))), 6),
        })
    if predicted_masks is not None and ground_truth_masks is not None:
        scores = [segmentation_scores(p, t) for p, t in zip(predicted_masks, ground_truth_masks)]
        if scores:
            result["segmentation_dice"] = round(float(np.mean([s["dice"] for s in scores])), 6)
            result["segmentation_iou"] = round(float(np.mean([s["iou"] for s in scores])), 6)
    return result


def save_mask_debug(raw_mask: np.ndarray, final_mask: np.ndarray, output_path: str | Path) -> str:
    """Save raw-vs-final mask audit: white=final, red=removed raw pixels."""
    raw, final = np.asarray(raw_mask) > 0, np.asarray(final_mask) > 0
    canvas = np.zeros((*raw.shape, 3), dtype=np.uint8)
    canvas[raw & ~final] = (0, 0, 255)
    canvas[final] = (0, 255, 0)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), canvas)
    return str(path)
