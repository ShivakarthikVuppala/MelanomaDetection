"""The classifier architecture copied from the working notebook inference path."""

import torch
import torch.nn as nn
import timm


class SwinV2Classifier(nn.Module):
    """Swin V2 backbone with the notebook's dropout + linear head."""

    def __init__(self, model_name, num_classes=2, pretrained=True, dropout=0.3):
        super().__init__()
        self.backbone = timm.create_model(model_name, pretrained=pretrained, num_classes=0)
        self.embed_dim = self.backbone.num_features
        self.head = nn.Sequential(nn.Dropout(p=dropout), nn.Linear(self.embed_dim, num_classes))

    def forward(self, x):
        return self.head(self.backbone(x))
