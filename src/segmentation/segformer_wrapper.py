"""
SegFormer Segmentation Wrapper
==============================

Wraps the pretrained SegFormer model for lesion segmentation on
2D dermoscopic images. Does not require a bounding box prompt.
"""

import numpy as np
import torch
import cv2
from skimage import transform as sk_transform
import segmentation_models_pytorch as smp

class SegFormerSegmenter:
    """
    SegFormer-based lesion segmentation for dermoscopic images.

    Loads the pretrained checkpoint and generates binary
    segmentation masks given an input image.

    Args:
        checkpoint_path: Path to the .pt checkpoint.
        device: Torch device (auto-detected if None).
        encoder_name: Encoder name (e.g. "mit_b2").
        input_size: Expected input resolution (default: 512).
        closing_kernel: Morphological closing kernel size for post-processing.
    """

    def __init__(
        self,
        checkpoint_path: str,
        device: torch.device = None,
        encoder_name: str = "mit_b2",
        input_size: int = 512,
        closing_kernel: int = 5,
    ):
        self.device = device or torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        self.input_size = input_size
        self.closing_kernel = closing_kernel

        # Load SegFormer model
        self.model = smp.Segformer(
            encoder_name=encoder_name,
            encoder_weights=None,
            in_channels=3,
            classes=1,
        )
        
        # Load weights
        ckpt = torch.load(checkpoint_path, map_location="cpu")
        state_dict = ckpt["model"] if "model" in ckpt else ckpt
        
        # Remove "model." prefix if present
        clean_state_dict = {}
        for k, v in state_dict.items():
            if k.startswith("model."):
                clean_state_dict[k.replace("model.", "", 1)] = v
            else:
                clean_state_dict[k] = v
                
        self.model.load_state_dict(clean_state_dict)
        self.model = self.model.to(self.device)
        self.model.eval()

    @torch.no_grad()
    def segment(self, image: np.ndarray) -> np.ndarray:
        """
        Segment the lesion region given an image.

        Args:
            image: RGB image as numpy array (H, W, 3), uint8.

        Returns:
            Binary mask as numpy array (H, W), uint8, values 0 or 1.
        """
        H, W = image.shape[:2]

        # 1. Preprocess image to input_size
        img_resized = sk_transform.resize(
            image, (self.input_size, self.input_size),
            order=3, preserve_range=True, anti_aliasing=True,
        ).astype(np.float32)

        # Normalize to [0, 1] using standard ImageNet mean and std as smp often expects
        img_norm = img_resized / 255.0
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        img_norm = (img_norm - mean) / std

        # Convert to tensor (1, 3, H, W)
        img_tensor = (
            torch.tensor(img_norm, dtype=torch.float32)
            .permute(2, 0, 1)
            .unsqueeze(0)
            .to(self.device)
        )

        # 2. Generate mask
        logits = self.model(img_tensor)
        
        # Resize logits back to original dimensions before thresholding
        # SegFormer outputs logits at 1/4 resolution, smp automatically upsamples to input_size
        low_res_mask = torch.sigmoid(logits[0, 0]).cpu().numpy()

        mask_full = sk_transform.resize(
            low_res_mask, (H, W),
            order=1, preserve_range=True, anti_aliasing=False,
        )

        # 3. Binarize
        binary_mask = (mask_full > 0.5).astype(np.uint8)

        # Morphological closing to fill small holes
        if self.closing_kernel > 0:
            kernel = cv2.getStructuringElement(
                cv2.MORPH_ELLIPSE,
                (self.closing_kernel, self.closing_kernel),
            )
            binary_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_CLOSE, kernel)

        return binary_mask
