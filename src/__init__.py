"""
Phase 1 — Core AI Melanoma Diagnosis Engine
============================================

A robust AI-powered melanoma diagnosis system that classifies dermoscopic
skin lesion images using Swin Transformer V2, segments lesion boundaries
using SegFormer, and extracts clinically relevant ABC morphological features.

Modules:
    - data: Dataset preparation, preprocessing, and augmentation
    - classification: Swin Transformer V2 fine-tuning and inference
    - segmentation: SegFormer-based lesion segmentation
    - features: ABC (Asymmetry, Border, Color) feature extraction
    - engine: Core Diagnosis Engine orchestrating all components
    - evaluation: Comprehensive evaluation and reporting
"""

__version__ = "1.0.0"
