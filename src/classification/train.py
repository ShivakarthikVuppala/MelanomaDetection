"""
Standard PyTorch Training Loop
================================

Provides a clean, debuggable training loop for the Swin V2 classifier
with differential learning rates, mixed precision, early stopping,
and CSV logging. No framework abstractions — full control.
"""

import os
import csv
import time
from pathlib import Path
from typing import Dict, Optional

import yaml
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, WeightedRandomSampler
from torch.amp import autocast, GradScaler
from sklearn.metrics import roc_auc_score
from tqdm import tqdm

from .model import SwinV2Classifier
from ..data.dataset import MelanomaClassificationDataset
from ..data.transforms import get_classification_transforms


def _build_dataloaders(config: dict) -> tuple:
    """Create train and val DataLoaders with weighted sampling."""
    paths = config["paths"]
    cls_cfg = config["classification"]

    train_tfm = get_classification_transforms("train", cls_cfg["img_size"])
    val_tfm = get_classification_transforms("val", cls_cfg["img_size"])

    train_ds = MelanomaClassificationDataset(paths["classification_train"], train_tfm)
    val_ds = MelanomaClassificationDataset(paths["classification_val"], val_tfm)

    class_weights = train_ds.get_class_weights()
    sample_weights = [class_weights[label] for _, label in train_ds.samples]
    sampler = WeightedRandomSampler(sample_weights, len(sample_weights), replacement=True)

    train_loader = DataLoader(
        train_ds,
        batch_size=cls_cfg["batch_size"],
        sampler=sampler,
        num_workers=cls_cfg["num_workers"],
        pin_memory=True,
        drop_last=True,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=cls_cfg["batch_size"],
        shuffle=False,
        num_workers=cls_cfg["num_workers"],
        pin_memory=True,
    )
    return train_loader, val_loader, class_weights


def train_one_epoch(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    optimizer: torch.optim.Optimizer,
    scaler: GradScaler,
    device: torch.device,
) -> Dict[str, float]:
    """Run one training epoch with mixed precision."""
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0

    for images, labels in tqdm(loader, desc="  Train", leave=False):
        images = images.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)

        optimizer.zero_grad(set_to_none=True)

        with autocast(device_type=device.type, dtype=torch.float16):
            logits = model(images)
            loss = criterion(logits, labels)

        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()

        running_loss += loss.item() * images.size(0)
        preds = logits.argmax(dim=1)
        correct += (preds == labels).sum().item()
        total += labels.size(0)

    return {
        "loss": running_loss / total,
        "accuracy": correct / total,
    }


@torch.no_grad()
def validate(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
) -> Dict[str, float]:
    """Run validation and compute loss, accuracy, and AUROC."""
    model.eval()
    running_loss = 0.0
    correct = 0
    total = 0
    all_probs = []
    all_labels = []

    for images, labels in tqdm(loader, desc="  Val  ", leave=False):
        images = images.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)

        with autocast(device_type=device.type, dtype=torch.float16):
            logits = model(images)
            loss = criterion(logits, labels)

        probs = torch.softmax(logits.float(), dim=1)
        running_loss += loss.item() * images.size(0)
        preds = logits.argmax(dim=1)
        correct += (preds == labels).sum().item()
        total += labels.size(0)

        # Melanoma probability — resolve index from class_names, not hardcoded
        melanoma_idx = next(
            (i for i, n in enumerate(loader.dataset.class_names)
             if n.strip().lower().replace("-", "_").replace(" ", "_") == "melanoma"),
            1,  # fallback to index 1 if class_names unavailable
        )
        all_probs.append(probs[:, melanoma_idx].cpu())  # melanoma probability
        all_labels.append(labels.cpu())

    all_probs = torch.cat(all_probs).numpy()
    all_labels = torch.cat(all_labels).numpy()

    try:
        auroc = roc_auc_score(all_labels, all_probs)
    except ValueError:
        auroc = 0.0  # happens if only one class present in batch

    return {
        "loss": running_loss / total,
        "accuracy": correct / total,
        "auroc": auroc,
    }


def train_classifier(config_path: str = "config.yaml"):
    """
    Full training pipeline for the Swin V2 classifier.

    Reads config, builds model/data/optimizer, trains with early stopping,
    saves best checkpoint, and logs metrics to CSV.

    Args:
        config_path: Path to the YAML configuration file.
    """
    with open(config_path) as f:
        config = yaml.safe_load(f)

    cls_cfg = config["classification"]
    project_cfg = config["project"]

    # Reproducibility
    torch.manual_seed(project_cfg["seed"])

    # Device
    if project_cfg["device"] == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(project_cfg["device"])
    print(f"Using device: {device}")

    # Data
    train_loader, val_loader, class_weights = _build_dataloaders(config)
    print(f"Train: {len(train_loader.dataset)} samples | Val: {len(val_loader.dataset)} samples")
    print(f"Class weights: {class_weights}")

    # Model
    model = SwinV2Classifier(
        model_name=cls_cfg["model_name"],
        num_classes=cls_cfg["num_classes"],
        pretrained=True,
    ).to(device)

    # Loss with class weights and label smoothing
    weight_tensor = torch.tensor(class_weights, dtype=torch.float32).to(device)
    criterion = nn.CrossEntropyLoss(
        weight=weight_tensor,
        label_smoothing=cls_cfg.get("label_smoothing", 0.1),
    )

    # Optimizer with differential learning rates
    optimizer = torch.optim.AdamW([
        {"params": model.get_backbone_params(), "lr": cls_cfg["lr_backbone"]},
        {"params": model.get_head_params(), "lr": cls_cfg["lr_head"]},
    ], weight_decay=cls_cfg["weight_decay"])

    # Scheduler
    scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(
        optimizer, T_0=10, T_mult=2
    )

    # Mixed precision
    scaler = GradScaler()

    # Output directory
    output_dir = Path(config["paths"]["outputs"])
    checkpoint_dir = Path(config["paths"]["checkpoints"])
    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    # CSV logger
    log_path = output_dir / "training_log.csv"
    log_file = open(log_path, "w", newline="")
    csv_writer = csv.DictWriter(log_file, fieldnames=[
        "epoch", "train_loss", "train_acc", "val_loss", "val_acc", "val_auroc", "lr", "time_s"
    ])
    csv_writer.writeheader()

    # Training loop with early stopping
    best_auroc = 0.0
    patience_counter = 0
    patience = cls_cfg["early_stopping_patience"]

    print(f"\nStarting training for {cls_cfg['max_epochs']} epochs...\n")

    for epoch in range(1, cls_cfg["max_epochs"] + 1):
        epoch_start = time.time()

        train_metrics = train_one_epoch(model, train_loader, criterion, optimizer, scaler, device)
        val_metrics = validate(model, val_loader, criterion, device)
        scheduler.step()

        elapsed = time.time() - epoch_start
        current_lr = optimizer.param_groups[0]["lr"]

        # Log
        row = {
            "epoch": epoch,
            "train_loss": f"{train_metrics['loss']:.4f}",
            "train_acc": f"{train_metrics['accuracy']:.4f}",
            "val_loss": f"{val_metrics['loss']:.4f}",
            "val_acc": f"{val_metrics['accuracy']:.4f}",
            "val_auroc": f"{val_metrics['auroc']:.4f}",
            "lr": f"{current_lr:.2e}",
            "time_s": f"{elapsed:.1f}",
        }
        csv_writer.writerow(row)
        log_file.flush()

        print(
            f"Epoch {epoch:3d}/{cls_cfg['max_epochs']} | "
            f"Train Loss: {train_metrics['loss']:.4f} Acc: {train_metrics['accuracy']:.4f} | "
            f"Val Loss: {val_metrics['loss']:.4f} Acc: {val_metrics['accuracy']:.4f} "
            f"AUROC: {val_metrics['auroc']:.4f} | {elapsed:.1f}s"
        )

        # Checkpointing — save best by AUROC
        if val_metrics["auroc"] > best_auroc:
            best_auroc = val_metrics["auroc"]
            patience_counter = 0
            save_path = checkpoint_dir / "best_swin_checkpoint.pth"
            torch.save(model.state_dict(), save_path)
            print(f"  ✓ New best AUROC: {best_auroc:.4f} — saved to {save_path}")
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"\nEarly stopping at epoch {epoch} (no improvement for {patience} epochs)")
                break

    log_file.close()
    print(f"\nTraining complete. Best AUROC: {best_auroc:.4f}")
    print(f"Checkpoint: {checkpoint_dir / 'best_swin_checkpoint.pth'}")
    print(f"Log: {log_path}")
