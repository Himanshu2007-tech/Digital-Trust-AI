import io
import logging
from typing import Tuple, Dict, Any
from PIL import Image, ImageOps, ImageEnhance

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """
    Optimizes images for high-accuracy OCR extraction:
    - Normalizes EXIF orientation
    - Grayscale conversion
    - Contrast stretching & auto-contrast
    - Resolution normalization
    """

    def __init__(
        self,
        min_width: int = 1000,
        max_width: int = 3000,
        contrast_factor: float = 1.4,
    ):
        self.min_width = min_width
        self.max_width = max_width
        self.contrast_factor = contrast_factor

    def process(self, image_bytes: bytes) -> Tuple[Image.Image, Dict[str, Any]]:
        """
        Executes preprocessing pipeline on raw image bytes.
        Returns preprocessed PIL Image and dictionary of applied operations.
        """
        operations: Dict[str, Any] = {
            "orientation_corrected": False,
            "grayscale_applied": False,
            "contrast_enhanced": False,
            "rescaled": False,
            "original_size": (0, 0),
            "processed_size": (0, 0),
        }

        # 1. Open image
        raw_image = Image.open(io.BytesIO(image_bytes))
        operations["original_size"] = raw_image.size

        # 2. Correct EXIF orientation
        try:
            oriented_image = ImageOps.exif_transpose(raw_image)
            if oriented_image is not None and oriented_image.size != raw_image.size:
                operations["orientation_corrected"] = True
                image = oriented_image
            else:
                image = raw_image
        except Exception as exc:
            logger.debug(f"Orientation correction skipped: {exc}")
            image = raw_image

        # 3. Convert to Grayscale
        if image.mode != "L":
            image = image.convert("L")
            operations["grayscale_applied"] = True

        # 4. Enhance contrast & normalize histogram
        try:
            image = ImageOps.autocontrast(image, cutoff=1)
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(self.contrast_factor)
            operations["contrast_enhanced"] = True
        except Exception as exc:
            logger.debug(f"Contrast enhancement skipped: {exc}")

        # 5. Smart resolution scaling
        curr_w, curr_h = image.size
        target_w, target_h = curr_w, curr_h

        if curr_w < self.min_width and curr_w > 0:
            scale = self.min_width / curr_w
            target_w = int(curr_w * scale)
            target_h = int(curr_h * scale)
            operations["rescaled"] = True
        elif curr_w > self.max_width:
            scale = self.max_width / curr_w
            target_w = int(curr_w * scale)
            target_h = int(curr_h * scale)
            operations["rescaled"] = True

        if operations["rescaled"]:
            image = image.resize((target_w, target_h), Image.Resampling.LANCZOS)

        operations["processed_size"] = image.size
        return image, operations
