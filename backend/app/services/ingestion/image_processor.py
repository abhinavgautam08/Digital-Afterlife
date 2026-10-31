"""
Image processing module for Phase 2.
Extracts dimensions, EXIF dates, applies orientation correction for previews,
strips GPS coordinates for privacy, and generates thumbnails.
Preserves original uploaded photograph bytes completely unaltered.
"""
from typing import Dict, Any, Tuple, Optional
from datetime import datetime
import io
from PIL import Image, ImageOps, ExifTags

from backend.app.services.ingestion.thumbnail_service import thumbnail_service
from backend.app.services.ingestion.validator import IngestionValidationError
from backend.app.core.logging import logger

MAX_IMAGE_PIXELS = 100_000_000  # 100 Megapixels max
MAX_IMAGE_DIMENSION = 16_000     # 16,000 px max width or height

Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS


class ImageProcessingError(IngestionValidationError):
    """Raised when an image is corrupt, truncated, or unreadable."""
    pass


def parse_exif_date(date_str: str) -> Optional[datetime]:
    """Parses standard EXIF datetime formats (YYYY:MM:DD HH:MM:SS)."""
    if not date_str or not isinstance(date_str, str):
        return None
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(date_str.strip()[:19], fmt)
        except ValueError:
            pass
    return None


def process_image(
    file_bytes: bytes,
    uuid_name: str
) -> Dict[str, Any]:
    """
    Safely processes an image artifact without modifying the original bytes:
    - Verifies image integrity and rejects corrupt/truncated images
    - Protects against decompression bombs and excessive dimensions
    - Extracts width and height
    - Extracts EXIF capture date if present
    - Strips GPS tags from derivatives to protect user physical privacy
    - Generates separate orientation-corrected thumbnail in data/thumbnails/
    """
    try:
        # Load and verify image with Pillow
        with Image.open(io.BytesIO(file_bytes)) as img:
            # 1. Dimension and pixel count bounds check
            orig_width, orig_height = img.size
            if orig_width > MAX_IMAGE_DIMENSION or orig_height > MAX_IMAGE_DIMENSION:
                raise ImageProcessingError(
                    f"Image dimensions ({orig_width}x{orig_height}) exceed maximum allowed dimension of {MAX_IMAGE_DIMENSION}px."
                )

            total_pixels = orig_width * orig_height
            if total_pixels > MAX_IMAGE_PIXELS:
                raise ImageProcessingError(
                    f"Image total pixels ({total_pixels}) exceed safety limit of {MAX_IMAGE_PIXELS} pixels (possible decompression bomb)."
                )

            img.load()  # Verifies image is not truncated or corrupt

            # 2. Safe EXIF metadata extraction
            original_created_at: Optional[datetime] = None
            safe_exif: Dict[str, Any] = {}

            try:
                exif_data = img.getexif()
                if exif_data:
                    for tag_id, value in exif_data.items():
                        tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                        # Explicitly omit GPSInfo to protect family location privacy
                        if "GPS" in tag_name:
                            continue
                        if tag_name in ("DateTimeOriginal", "DateTime", "DateTimeDigitized"):
                            parsed = parse_exif_date(str(value))
                            if parsed and not original_created_at:
                                original_created_at = parsed
                        elif isinstance(value, (str, int, float)) and len(str(value)) < 100:
                            safe_exif[tag_name] = value
            except Exception as exif_err:
                logger.debug(f"Non-fatal EXIF read notice: {exif_err}")

            # 3. Correct orientation for thumbnail generation only (original remains untouched)
            try:
                oriented_img = ImageOps.exif_transpose(img)
                oriented_bytes = io.BytesIO()
                img_format = "PNG" if img.format == "PNG" else "JPEG"
                # Save without EXIF dict ensures thumbnail is completely GPS-free
                oriented_img.save(oriented_bytes, format=img_format)
                thumb_source_bytes = oriented_bytes.getvalue()
            except Exception:
                thumb_source_bytes = file_bytes

            # 4. Generate thumbnail in data/thumbnails/
            thumb_name = thumbnail_service.create_image_thumbnail(
                thumb_source_bytes,
                target_name_prefix=uuid_name
            )

            return {
                "width": orig_width,
                "height": orig_height,
                "original_created_at": original_created_at,
                "thumbnail_path": thumb_name,
                "metadata": safe_exif,
                "extracted_text": None,
                "duration_seconds": None,
            }

    except Image.DecompressionBombError as e:
        logger.error(f"Image decompression bomb rejected: {e}")
        raise ImageProcessingError(f"Image exceeds safety pixel limits (possible decompression bomb): {e}")
    except IngestionValidationError:
        raise
    except Exception as e:
        logger.error(f"Image processing failure: {e}")
        raise ImageProcessingError(f"Malformed or unreadable image file: {e}")
