"""
Segmentation Evaluation Report
================================

Evaluates SegFormer segmentation against ground-truth masks
and produces a JSON report with overlay visualizations.
"""

import json
from pathlib import Path

import yaml
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from tqdm import tqdm

from ..segmentation.segformer_wrapper import SegFormerSegmenter
from ..segmentation.lesion_locator import LesionLocator
from .metrics import compute_segmentation_metrics


def run_segmentation_evaluation(
    config_path: str = "config.yaml",
    max_samples: int = None,
    save_overlays: int = 10,
) -> dict:
    """
    Full segmentation evaluation pipeline.

    Args:
        config_path: Path to config.yaml.
        max_samples: Limit evaluation samples (None = all).
        save_overlays: Number of overlay visualizations to save.

    Returns:
        Dict with aggregate and per-sample metrics.
    """
    config_file = Path(config_path).resolve()
    project_root = config_file.parent
    with open(config_file) as f:
        config = yaml.safe_load(f)

    seg_cfg = config["segmentation"]
    paths = config["paths"]

    def resolve_config_path(value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else project_root / path

    # Initialize
    segmenter = SegFormerSegmenter(
        checkpoint_path=str(resolve_config_path(seg_cfg["checkpoint"])),
        encoder_name=seg_cfg.get("encoder_name", "mit_b2"),
        input_size=seg_cfg.get("input_size", 512),
        closing_kernel=seg_cfg.get("morphological_closing_kernel", 5),
    )
    locator = LesionLocator(bbox_padding=seg_cfg.get("bbox_padding", 0.10))

    # Load dataset pairs
    img_dir = resolve_config_path(paths["segmentation_images"])
    mask_dir = resolve_config_path(paths["segmentation_masks"])
    valid_ext = {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}

    mask_stems = {f.stem: f for f in mask_dir.iterdir() if f.suffix.lower() in valid_ext}
    pairs = [
        (f, mask_stems[f.stem])
        for f in sorted(img_dir.iterdir())
        if f.suffix.lower() in valid_ext and f.stem in mask_stems
    ]

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
        gt_mask = (np.array(Image.open(gt_path).convert("L")) > 127).astype(np.uint8)

        pred_mask = segmenter.segment(image)

        sample_metrics = compute_segmentation_metrics(pred_mask, gt_mask)
        sample_metrics["name"] = img_path.stem
        results.append(sample_metrics)

    # Aggregate
    metric_names = ["dice", "iou", "precision", "recall"]
    aggregate = {}
    for m in metric_names:
        values = [r[m] for r in results]
        aggregate[m] = {
            "mean": round(float(np.mean(values)), 4),
            "std": round(float(np.std(values)), 4),
        }

    report = {
        "total_samples": len(results),
        "aggregate": aggregate,
        "per_sample": results,
    }

    # Save report
    output_dir = resolve_config_path(paths["outputs"])
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "segmentation_report.json", "w") as f:
        json.dump(report, f, indent=2)

    # Save overlay visualizations for first N samples
    overlay_dir = output_dir / "segmentation_overlays"
    overlay_dir.mkdir(exist_ok=True)
    for i, (img_path, gt_path) in enumerate(pairs[:save_overlays]):
        image = np.array(Image.open(img_path).convert("RGB"))
        gt_mask = (np.array(Image.open(gt_path).convert("L")) > 127).astype(np.uint8)
        pred_mask = segmenter.segment(image)

        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        axes[0].imshow(image)
        axes[0].set_title("Original")
        axes[1].imshow(gt_mask, cmap="gray")
        axes[1].set_title(f"Ground Truth (Dice: {results[i]['dice']:.3f})")
        axes[2].imshow(pred_mask, cmap="gray")
        axes[2].set_title("Predicted Mask")
        for ax in axes:
            ax.axis("off")
        plt.savefig(overlay_dir / f"{img_path.stem}_overlay.png", dpi=100, bbox_inches="tight")
        plt.close()

    print("\n--- Segmentation Results ---")
    for m in metric_names:
        print(f"  {m:>12s}: {aggregate[m]['mean']:.4f} ± {aggregate[m]['std']:.4f}")

    return report
