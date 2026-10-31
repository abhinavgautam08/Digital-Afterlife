"""
File signature and security validator for Phase 2 multimedia ingestion.
Validates magic numbers, detects MIME/extension spoofing, prevents execution of malicious payloads,
and rejects malformed files without trusting browser headers.
"""
from pathlib import Path
from typing import Tuple
import re
import io
import zipfile

from backend.app.core.config import settings
from backend.app.core.security import SecurityValidationError, sanitize_filename

try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

# Magic signatures for binary verification
MAGIC_SIGNATURES = {
    # Images
    "jpeg": [b"\xFF\xD8\xFF"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "gif": [b"GIF87a", b"GIF89a"],
    "webp": [b"RIFF"],  # With 'WEBP' at offset 8
    # Audio
    "mp3": [b"ID3", b"\xFF\xFB", b"\xFF\xF3", b"\xFF\xF2"],
    "wav": [b"RIFF"],  # With 'WAVE' at offset 8
    "ogg": [b"OggS"],
    "flac": [b"fLaC"],
    "m4a": [b"ftyp"],  # At offset 4
    # Video
    "mp4": [b"ftyp"],  # At offset 4
    "mov": [b"ftyp", b"\x00\x00\x00\x14moov"],
    "webm": [b"\x1A\x45\xDF\xA3"],
    # Documents
    "pdf": [b"%PDF"],
    "docx": [b"PK\x03\x04"],  # Standard Zip container
}

# Malicious signatures to explicitly reject
DANGEROUS_SIGNATURES = [
    (b"MZ", "Windows executable (PE/EXE/DLL)"),
    (b"\x7FELF", "Linux ELF executable"),
    (b"\xFE\xED\xFA\xCE", "Mach-O executable"),
    (b"\xCF\xFA\xED\xFE", "Mach-O 64-bit executable"),
    (b"#!", "Shell script"),
]

DANGEROUS_ARCHIVE_EXTENSIONS = {
    ".exe", ".dll", ".bat", ".cmd", ".sh", ".vbs", ".js",
    ".ps1", ".jar", ".com", ".scr", ".pif", ".hta", ".cpl"
}

HTML_INDICATORS = [
    b"<!doctype html", b"<html", b"<script", b"<body", b"<head",
    b"<?php", b"<iframe", b"<object", b"<embed", b"javascript:"
]


class IngestionValidationError(SecurityValidationError):
    """Raised when an ingested file violates format, size, or safety rules."""
    pass


def validate_docx_archive(file_bytes: bytes) -> None:
    """
    Validates that a DOCX file is a genuine, safe ZIP archive containing valid
    Microsoft WordprocessingML structures and no suspicious payloads or path traversal.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
            namelist = zf.namelist()
            if not namelist:
                raise IngestionValidationError("DOCX archive is empty.")

            # Check for suspicious members (path traversal, absolute paths, or executable files)
            total_uncompressed = 0
            for info in zf.infolist():
                name = info.filename
                if ".." in name or name.startswith("/") or name.startswith("\\"):
                    raise IngestionValidationError("Suspicious archive member path traversal detected in DOCX.")

                member_ext = Path(name).suffix.lower()
                if member_ext in DANGEROUS_ARCHIVE_EXTENSIONS:
                    raise IngestionValidationError(
                        f"DOCX archive contains suspicious executable member: '{name}'."
                    )

                total_uncompressed += info.file_size
                # Guard against ZIP decompression bombs
                if total_uncompressed > 250 * 1024 * 1024:  # 250 MB max uncompressed
                    raise IngestionValidationError("DOCX archive exceeds safe uncompressed size limits.")

            # Verify presence of essential WordprocessingML structure
            has_content_types = "[Content_Types].xml" in namelist
            has_word_doc = any(n.startswith("word/") for n in namelist) or "word/document.xml" in namelist
            if not (has_content_types and has_word_doc):
                raise IngestionValidationError(
                    "ZIP archive is not a valid Microsoft Word (.docx) document (missing document XML)."
                )

    except zipfile.BadZipFile as e:
        raise IngestionValidationError(f"Malformed or corrupted DOCX ZIP archive: {e}")


def validate_pdf_structure(file_bytes: bytes) -> None:
    """
    Validates that a PDF file has valid header structure and readable pages.
    """
    if len(file_bytes) < 32:
        raise IngestionValidationError("PDF file is too small or truncated.")

    if not file_bytes.startswith(b"%PDF"):
        raise IngestionValidationError("Missing %PDF header signature.")

    # Check for basic PDF structural markers
    trailer_sample = file_bytes[-2048:] if len(file_bytes) > 2048 else file_bytes
    if b"%%EOF" not in trailer_sample and b"xref" not in file_bytes and b"obj" not in file_bytes:
        raise IngestionValidationError("Malformed or truncated PDF document (missing structural markers).")

    if HAS_PYPDF:
        try:
            reader = pypdf.PdfReader(io.BytesIO(file_bytes), strict=False)
            if len(reader.pages) == 0:
                raise IngestionValidationError("PDF document contains no readable pages.")
        except IngestionValidationError:
            raise
        except Exception as e:
            raise IngestionValidationError(f"Malformed or unreadable PDF document: {e}")


def detect_magic_format(file_bytes: bytes, filename: str) -> str:
    """
    Inspects leading bytes and internal structures to determine real file format
    independent of client headers.
    Returns format code: 'jpeg', 'png', 'gif', 'webp', 'mp3', 'wav', 'ogg', 'flac',
    'm4a', 'mp4', 'mov', 'webm', 'pdf', 'docx', 'text'
    """
    if len(file_bytes) < 4:
        raise IngestionValidationError("File is too small or truncated.")

    # 1. Check dangerous executable signatures
    for sig, desc in DANGEROUS_SIGNATURES:
        if file_bytes.startswith(sig):
            raise IngestionValidationError(f"Dangerous file rejected: {desc}.")

    # 2. Check HTML / JavaScript / Script payload indicators in leading sample
    sample_text = file_bytes[:2048].lower()
    for tag in HTML_INDICATORS:
        if tag in sample_text:
            raise IngestionValidationError(
                "HTML, script, or executable text payload detected and rejected."
            )

    # 3. Binary Magic Signatures
    # JPEG
    if file_bytes.startswith(b"\xFF\xD8\xFF"):
        return "jpeg"

    # PNG
    if file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"

    # GIF
    if file_bytes.startswith(b"GIF87a") or file_bytes.startswith(b"GIF89a"):
        return "gif"

    # PDF
    if file_bytes.startswith(b"%PDF"):
        validate_pdf_structure(file_bytes)
        return "pdf"

    # FLAC
    if file_bytes.startswith(b"fLaC"):
        return "flac"

    # OGG
    if file_bytes.startswith(b"OggS"):
        return "ogg"

    # WEBM
    if file_bytes.startswith(b"\x1A\x45\xDF\xA3"):
        return "webm"

    # RIFF containers (WEBP or WAV)
    if file_bytes.startswith(b"RIFF") and len(file_bytes) >= 12:
        riff_type = file_bytes[8:12]
        if riff_type == b"WEBP":
            return "webp"
        if riff_type == b"WAVE":
            return "wav"

    # ISO Media containers (MP4, M4A, MOV)
    if len(file_bytes) >= 12 and file_bytes[4:8] == b"ftyp":
        major_brand = file_bytes[8:12].lower()
        ext = Path(filename).suffix.lower()
        if major_brand in (b"m4a ", b"m4b ", b"mp42", b"isom"):
            return "m4a" if ext == ".m4a" else "mp4"
        if major_brand in (b"qt  ", b"moov"):
            return "mov"
        if ext == ".mov":
            return "mov"
        if ext == ".m4a":
            return "m4a"
        return "mp4"

    # MP3 (ID3v2 tag or MPEG frame sync)
    if file_bytes.startswith(b"ID3") or (
        len(file_bytes) >= 2 and file_bytes[0] == 0xFF and (file_bytes[1] & 0xE0) == 0xE0
    ):
        return "mp3"

    # DOCX (ZIP archive with valid word structure)
    if file_bytes.startswith(b"PK\x03\x04"):
        validate_docx_archive(file_bytes)
        return "docx"

    # Plain text / Markdown
    ext = Path(filename).suffix.lower()
    if ext in (".txt", ".md"):
        # Text size guardrail
        if len(file_bytes) > 20 * 1024 * 1024:  # 20 MB max for text
            raise IngestionValidationError("Text document exceeds maximum allowed size of 20 MB.")

        # Null byte check
        if b"\x00" in file_bytes:
            raise IngestionValidationError("Text document contains binary null bytes.")

        # Strict UTF-8 validation
        try:
            decoded_text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raise IngestionValidationError("Invalid or non-UTF-8 encoded text file.")

        # Scan text document for disguised HTML/scripts
        lower_decoded = decoded_text[:4096].lower().strip()
        for tag_str in ("<!doctype html", "<html", "<script", "<body", "<head", "<?php", "<iframe"):
            if tag_str in lower_decoded:
                raise IngestionValidationError("HTML or script payload disguised as text document rejected.")

        return "text"

    raise IngestionValidationError(
        f"Unsupported file format or unrecognized magic signature for file '{filename}'."
    )


def validate_file_content(file_bytes: bytes, filename: str, declared_mime: str) -> Tuple[str, str]:
    """
    Validates file size, path traversal, extension, and verifies that the content's
    real signature matches an allowed extension and category.
    Returns: (detected_format, canonical_mime_type)
    """
    file_size = len(file_bytes)
    if file_size <= 0:
        raise IngestionValidationError("File is empty (0 bytes).")

    if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
        max_mb = settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
        raise IngestionValidationError(f"File size exceeds maximum allowed limit of {max_mb} MB.")

    clean_name = sanitize_filename(filename)
    ext = Path(clean_name).suffix.lower()

    if ext not in settings.ALLOWED_EXTENSIONS:
        raise IngestionValidationError(
            f"Extension '{ext}' is not permitted. Supported (17 formats): {sorted(list(settings.ALLOWED_EXTENSIONS))}"
        )

    # Validate declared MIME if provided and not generic octet-stream
    clean_declared = declared_mime.lower().split(";")[0].strip()
    if clean_declared and clean_declared != "application/octet-stream":
        if clean_declared not in settings.ALLOWED_MIME_TYPES:
            raise IngestionValidationError(f"Disallowed MIME type: {clean_declared}")

    # Detect actual format from magic numbers and structural validation
    fmt = detect_magic_format(file_bytes, clean_name)

    # Format to MIME and allowed extensions mapping (17 extensions total)
    format_map = {
        "jpeg": ("image/jpeg", [".jpg", ".jpeg"]),
        "png": ("image/png", [".png"]),
        "webp": ("image/webp", [".webp"]),
        "gif": ("image/gif", [".gif"]),
        "mp3": ("audio/mpeg", [".mp3"]),
        "wav": ("audio/wav", [".wav"]),
        "ogg": ("audio/ogg", [".ogg"]),
        "flac": ("audio/flac", [".flac"]),
        "m4a": ("audio/x-m4a", [".m4a", ".mp4"]),
        "mp4": ("video/mp4", [".mp4"]),
        "mov": ("video/quicktime", [".mov", ".mp4"]),
        "webm": ("video/webm", [".webm"]),
        "pdf": ("application/pdf", [".pdf"]),
        "docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", [".docx"]),
        "text": ("text/plain" if ext == ".txt" else "text/markdown", [".txt", ".md"]),
    }

    if fmt not in format_map:
        raise IngestionValidationError(f"File signature resolved to unsupported format: {fmt}")

    canonical_mime, valid_exts = format_map[fmt]

    # Detect MIME/extension spoofing (e.g. executable renamed to .jpg or png renamed to .pdf)
    if ext not in valid_exts:
        raise IngestionValidationError(
            f"MIME spoofing detected: file extension '{ext}' does not match real content format '{fmt}'."
        )

    return fmt, canonical_mime
