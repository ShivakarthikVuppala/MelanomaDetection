"""
Image Augmentation & Preprocessing Transforms
===============================================

Provides Albumentations-based transform pipelines for the classification
task. All transforms are dermoscopy-safe with conservative color
adjustments to preserve clinically significant features.

Usage:
    train_tfm = get_classification_transforms("train", img_size=256)
    val_tfm = get_classification_transforms("val", img_size=256)
"""

import albumentations as A
from albumentations.pytorch import ToTensorV2

# ImageNet normalization statistics
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


def get_classification_transforms(split: str, img_size: int = 256) -> A.Compose:
    """
    Get augmentation pipeline for the classification task.

    Args:
        split: One of 'train', 'val', or 'test'.
        img_size: Target image size (square).

    Returns:
        Albumentations Compose pipeline.
    """
    if split == "train":
        return A.Compose([
            A.RandomResizedCrop(
                size=(img_size, img_size),
                scale=(0.8, 1.0),
                ratio=(0.9, 1.1),
                p=1.0,
            ),
            A.HorizontalFlip(p=0.5),
            A.VerticalFlip(p=0.5),
            A.RandomRotate90(p=0.5),
            A.Transpose(p=0.3),
            # Conservative color augmentation for dermoscopy
            A.OneOf([
                A.RandomBrightnessContrast(
                    brightness_limit=0.1,
                    contrast_limit=0.1,
                    p=1.0,
                ),
                A.CLAHE(clip_limit=2.0, tile_grid_size=(8, 8), p=1.0),
            ], p=0.3),
            A.OneOf([
                A.GaussianBlur(blur_limit=(3, 5), p=1.0),
                A.GaussNoise(p=1.0),
            ], p=0.2),
            A.HueSaturationValue(
                hue_shift_limit=8,
                sat_shift_limit=12,
                val_shift_limit=8,
                p=0.2,
            ),
            A.CoarseDropout(
                max_holes=4,
                max_height=int(img_size * 0.08),
                max_width=int(img_size * 0.08),
                fill_value=0,
                p=0.2,
            ),
            A.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
            ToTensorV2(),
        ])
    else:
        # val / test — deterministic
        return A.Compose([
            A.Resize(height=img_size, width=img_size),
            A.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
            ToTensorV2(),
        ])
