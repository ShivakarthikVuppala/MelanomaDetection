---
title: Melanoma classifier
emoji: 🩺
colorFrom: blue
colorTo: indigo
sdk: gradio
app_file: app.py
---

# Melanoma classifier

This Space packages the existing notebook inference path. It uses the checkpoint metadata for the Swin V2 model configuration, class names, preprocessing, and threshold.

The notebook's saved single-image inference function is deterministic `Resize -> Normalize -> ToTensorV2`, followed by one model forward pass and thresholding of the melanoma probability. Its evaluation-only TTA/calibration experiments are not applied here because they are not part of that current single-image inference function.

Upload `best_swin_checkpoint.pth` to this repository. The checkpoint is intentionally not converted or replaced.
