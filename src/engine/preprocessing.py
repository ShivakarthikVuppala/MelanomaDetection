"""
Dermoscopy Image Preprocessing
================================

Preprocessing pipeline for dermoscopic images that removes common
artifacts (hair, uneven illumination) before classification and
segmentation. Applied as Step 0 in the inference pipeline.

Techniques:
    1. Hair Removal — DullRazor-inspired algorithm using black-hat
       morphological filtering to detect dark thin structures (hair),
       followed by OpenCV inpainting to reconstruct the underlying skin.
    2. Illumination Normalization — CLAHE on the L-channel of LAB
       color space to correct for uneven lighting across the image.
"""

import numpy as np
import cv2


class DermoscopyPreprocessor:
    """
    Preprocessing pipeline for dermoscopic images.

    Removes hair artifacts and normalizes illumination before the
    image is passed to the classifier and segmenter.

    Args:
        hair_removal: Enable DullRazor-style hair removal.
        illumination_normalization: Enable CLAHE illumination correction.
        hair_kernel_size: Size of the morphological kernel for hair detection.
            Larger values detect thicker hair but may affect lesion edges.
        hair_threshold: Intensity threshold for the black-hat output.
            Lower values are more aggressive (detect more hair).
        inpaint_radius: Radius (in pixels) for the inpainting algorithm.
        clahe_clip_limit: Contrast limiting parameter for CLAHE.
        clahe_grid_size: Tile grid size for CLAHE.
    """

    def __init__(
        self,
        hair_removal: bool = True,
        illumination_normalization: bool = True,
        preserve_scale_reference: bool = True,
        hair_kernel_size: int = 17,
        hair_threshold: int = 10,
        inpaint_radius: int = 6,
        clahe_clip_limit: float = 2.0,
        clahe_grid_size: int = 8,
        max_processing_dimension: int = 1600,
    ):
        self.hair_removal = hair_removal
        self.illumination_normalization = illumination_normalization
        self.preserve_scale_reference = preserve_scale_reference
        self.hair_kernel_size = hair_kernel_size
        self.hair_threshold = hair_threshold
        self.inpaint_radius = inpaint_radius
        self.clahe_clip_limit = clahe_clip_limit
        self.clahe_grid_size = clahe_grid_size
        # The classifier/segmenter resize internally.  Running morphology and
        # Telea inpainting over a 4K/8K upload wastes time and can smear the
        # reference object.  Keep the result at the original shape after doing
        # artifact cleanup at a bounded working resolution.
        self.max_processing_dimension = max(512, int(max_processing_dimension))
        self._last_hair_removed: np.ndarray | None = None
        self._last_input_shape: tuple[int, int] | None = None
        self._last_working_shape: tuple[int, int] | None = None

    def process(self, image: np.ndarray) -> np.ndarray:
        """
        Apply the full preprocessing pipeline.

        Args:
            image: RGB image as numpy array (H, W, 3), uint8.

        Returns:
            Preprocessed RGB image as numpy array (H, W, 3), uint8.
        """
        original_shape = image.shape[:2]
        self._last_input_shape = original_shape
        scale = min(1.0, self.max_processing_dimension / max(original_shape))
        if scale < 1.0:
            work = cv2.resize(
                image,
                (max(1, int(round(image.shape[1] * scale))),
                 max(1, int(round(image.shape[0] * scale)))),
                interpolation=cv2.INTER_AREA,
            )
        else:
            work = image.copy()
        self._last_working_shape = work.shape[:2]
        result = work

        if self.hair_removal:
            result = self._remove_hair(result)
        self._last_hair_removed = (
            cv2.resize(result, (image.shape[1], image.shape[0]), interpolation=cv2.INTER_LINEAR)
            if result.shape[:2] != original_shape else result.copy()
        )

        if self.illumination_normalization:
            result = self._normalize_illumination(result)
        if result.shape[:2] != original_shape:
            result = cv2.resize(result, (image.shape[1], image.shape[0]), interpolation=cv2.INTER_LINEAR)

        return result

    def get_hair_removed_image(self, fallback: np.ndarray) -> np.ndarray:
        """Return the pre-CLAHE image for geometry/artifact cleanup."""
        return self._last_hair_removed if self._last_hair_removed is not None else fallback

    def _remove_hair(self, image: np.ndarray) -> np.ndarray:
        """
        DullRazor-inspired hair removal.

        Process:
            1. Convert to grayscale
            2. Black-hat morphological transform with an elongated kernel
               to isolate dark, thin structures (hair) against lighter skin
            3. Threshold the black-hat output to create a binary hair mask
            4. Dilate the mask slightly to cover hair edges
            5. Inpaint the masked regions using Telea's algorithm

        Args:
            image: RGB image (H, W, 3), uint8.

        Returns:
            Hair-removed RGB image (H, W, 3), uint8.
        """
        # Convert RGB to BGR for OpenCV operations
        bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

        # Black-hat transform: isolates dark structures smaller than kernel
        kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT,
            (self.hair_kernel_size, self.hair_kernel_size),
        )
        blackhat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, kernel)

        # Threshold to create binary hair mask
        _, hair_mask = cv2.threshold(
            blackhat, self.hair_threshold, 255, cv2.THRESH_BINARY
        )

        # Dilate the mask to ensure full hair coverage
        dilate_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        hair_mask = cv2.dilate(hair_mask, dilate_kernel, iterations=1)

        # Do not run scale detection from preprocessing.  Calibration is
        # performed once, later, on the original image; invoking it here made
        # every request pay for a second ruler scan and the inpainted preview
        # could still lose reference pixels.

        # Inpaint the hair regions
        inpainted = cv2.inpaint(
            bgr, hair_mask, self.inpaint_radius, cv2.INPAINT_TELEA
        )

        # Convert back to RGB
        return cv2.cvtColor(inpainted, cv2.COLOR_BGR2RGB)

    @staticmethod
    def _detect_scale_reference_region(image: np.ndarray) -> np.ndarray | None:
        """Return a mask for a detected ruler region, if one is present."""
        try:
            # Import lazily to keep preprocessing usable as a standalone
            # module and avoid importing the heavier engine at module load.
            from .scale_detection import ScaleDetector

            calibration = ScaleDetector()._detect_ruler(image)
            bbox = calibration.reference_bbox_px
            if not calibration.detected or bbox is None:
                return None

            height, width = image.shape[:2]
            x, y, w, h = [int(value) for value in bbox]
            pad = max(6, int(round(min(height, width) * 0.012)))
            x0, y0 = max(0, x - pad), max(0, y - pad)
            x1, y1 = min(width, x + w + pad), min(height, y + h + pad)
            protected = np.zeros((height, width), dtype=np.uint8)
            protected[y0:y1, x0:x1] = 255
            return protected
        except Exception:
            # Reference protection is a best-effort safeguard.  It must never
            # make the primary preprocessing path fail.
            return None

    def _normalize_illumination(self, image: np.ndarray) -> np.ndarray:
        """
        CLAHE-based illumination normalization.

        Applies Contrast Limited Adaptive Histogram Equalization to
        the Lightness channel in LAB color space. This corrects for
        uneven illumination (common in dermoscopy) without distorting
        the chrominance (color) information.

        Args:
            image: RGB image (H, W, 3), uint8.

        Returns:
            Illumination-normalized RGB image (H, W, 3), uint8.
        """
        # Convert to LAB
        lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)

        # Apply CLAHE to L-channel only
        clahe = cv2.createCLAHE(
            clipLimit=self.clahe_clip_limit,
            tileGridSize=(self.clahe_grid_size, self.clahe_grid_size),
        )
        lab[:, :, 0] = clahe.apply(lab[:, :, 0])

        # Convert back to RGB
        return cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)

    def get_applied_steps(self) -> dict:
        """Return applied operations plus the bounded working-image geometry."""
        original_height, original_width = self._last_input_shape or (None, None)
        working_height, working_width = self._last_working_shape or (None, None)
        return {
            "hair_removal": self.hair_removal,
            "illumination_normalization": self.illumination_normalization,
            "preserve_scale_reference": self.preserve_scale_reference,
            "resized_for_preprocessing": bool(
                self._last_input_shape and self._last_working_shape
                and self._last_input_shape != self._last_working_shape
            ),
            "original_size": {"width": original_width, "height": original_height},
            "working_size": {"width": working_width, "height": working_height},
        }
