"""
Swin Transformer V2 Classifier
================================

Wraps a pretrained Swin Transformer V2 backbone from timm with a
custom classification head for binary melanoma classification.

Exposes separate parameter groups for differential learning rates
(lower LR for pretrained backbone, higher LR for new head).
"""

import torch
import torch.nn as nn
import timm


class SwinV2Classifier(nn.Module):
    """
    Binary classifier for melanoma vs. benign using Swin Transformer V2.

    Architecture:
        - Pretrained Swin V2 backbone (from timm)
        - Replaced classification head: Linear(embed_dim, num_classes)
        - Optional dropout before the head

    Args:
        model_name: timm model identifier for Swin V2.
        num_classes: Number of output classes (default: 2).
        pretrained: Whether to load ImageNet pretrained weights.
        dropout_rate: Dropout probability before the classification head.
    """

    def __init__(
        self,
        model_name: str = "swinv2_base_window12to16_192to256",
        num_classes: int = 2,
        pretrained: bool = True,
        dropout_rate: float = 0.3,
    ):
        super().__init__()

        # Load the full pretrained model from timm
        self.backbone = timm.create_model(
            model_name,
            pretrained=pretrained,
            num_classes=0,  # Remove the original head; returns features
        )

        # Get the feature dimension from the backbone
        self.embed_dim = self.backbone.num_features

        # Custom classification head
        self.head = nn.Sequential(
            nn.Dropout(p=dropout_rate),
            nn.Linear(self.embed_dim, num_classes),
        )

        self.num_classes = num_classes

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.

        Args:
            x: Input tensor of shape (B, 3, H, W).

        Returns:
            Logits of shape (B, num_classes).
        """
        features = self.backbone(x)
        # timm normally returns pooled vectors when num_classes=0, but some
        # model versions expose a spatial feature map instead.  Pooling here
        # keeps the Swin V2 architecture unchanged while making checkpoint
        # inference robust across timm versions.
        if features.ndim > 2:
            features = features.mean(dim=tuple(range(2, features.ndim)))
        logits = self.head(features)  # (B, num_classes)
        return logits

    def get_backbone_params(self):
        """Return backbone parameters (for lower learning rate)."""
        return self.backbone.parameters()

    def get_head_params(self):
        """Return classification head parameters (for higher learning rate)."""
        return self.head.parameters()

    def freeze_backbone(self):
        """Freeze all backbone parameters (useful for initial head training)."""
        for param in self.backbone.parameters():
            param.requires_grad = False

    def unfreeze_backbone(self):
        """Unfreeze all backbone parameters (for full fine-tuning)."""
        for param in self.backbone.parameters():
            param.requires_grad = True
