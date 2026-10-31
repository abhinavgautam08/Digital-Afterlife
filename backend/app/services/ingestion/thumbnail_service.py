"""
Thumbnail generation service for Phase 2 multimedia preservation.
Generates separate, optimized preview images in data/thumbnails without modifying originals.
"""
from pathlib import Path
from typing import Optional
import uuid
import io
from PIL import Image

from backend.app.core.config import settings
from backend.app.core.logging import logger


class ThumbnailService:
    def __init__(self, thumbnails_dir: Optional[Path] = None):
        self.thumbnails_dir = (thumbnails_dir or settings.THUMBNAILS_DIR).resolve()
        self.thumbnails_dir.mkdir(parents=True, exist_ok=True)

    def create_image_thumbnail(
        self,
        image_bytes: bytes,
        target_name_prefix: str,
        max_size: tuple = (480, 480)
    ) -> Optional[str]:
        """
        Generates an optimized JPEG thumbnail from raw image bytes.
        Returns the relative filename of the generated thumbnail (e.g., '<uuid>_thumb.jpg').
        """
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                # Handle RGBA/palette modes for clean JPEG output
                if img.mode in ("RGBA", "LA", "P"):
                    background = Image.new("RGB", img.size, (15, 18, 26))  # Dark charcoal theme background
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    background.paste(img, mask=img.split()[-1] if "A" in img.mode else None)
                    img = background
                elif img.mode != "RGB":
                    img = img.convert("RGB")

                # Generate thumbnail maintaining aspect ratio
                img.thumbnail(max_size, Image.Resampling.LANCZOS)

                thumb_filename = f"{target_name_prefix}_thumb.jpg"
                thumb_path = self.thumbnails_dir / thumb_filename

                img.save(thumb_path, "JPEG", quality=85, optimize=True)
                logger.debug(f"Created thumbnail: {thumb_filename}")
                return thumb_filename

        except Exception as e:
            logger.warning(f"Could not create image thumbnail for {target_name_prefix}: {e}")
            return None

    def get_thumbnail_path(self, thumbnail_filename: str) -> Optional[Path]:
        """Safely resolves a thumbnail path inside the thumbnails directory."""
        if not thumbnail_filename:
            return None
        safe_path = (self.thumbnails_dir / Path(thumbnail_filename).name).resolve()
        try:
            safe_path.relative_to(self.thumbnails_dir)
            if safe_path.exists():
                return safe_path
        except ValueError:
            pass
        return None


thumbnail_service = ThumbnailService()

