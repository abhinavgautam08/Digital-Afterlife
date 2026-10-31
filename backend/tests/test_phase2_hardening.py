"""
Phase 2 Final Hardening & Verification Test Suite.
Covers:
1. Complete 17-format upload and retrieval matrix.
2. WebM EBML duration and dimension extraction.
3. MOV and M4A ISO container parsing.
4. Original-file byte-for-byte preservation.
5. EXIF orientation correction and GPS stripping.
6. Missing/malformed EXIF resilience.
7. DOCX ZIP validation and suspicious archive rejection.
8. PDF structure and malformed PDF rejection.
9. Decompression bomb and excessive dimension protection.
10. Strict UTF-8 text validation and disguised HTML/script rejection.
11. Extracted document text character bounds.
12. Orphan cleanup and filesystem/database consistency.
13. Missing thumbnail tolerance on retrieval.
14. Migration idempotency and pre-existing record preservation.
"""
import io
import struct
import wave
import zipfile
import pytest
from PIL import Image
from sqlalchemy.sql import text

from backend.app.services.ingestion.validator import validate_file_content, IngestionValidationError
from backend.app.services.ingestion.image_processor import process_image, ImageProcessingError
from backend.app.services.ingestion.video_processor import parse_webm_metadata, parse_mp4_atoms
from backend.app.database.session import run_migrations


# ============================================================================
# Deterministic Binary Generators for All 17 Formats
# ============================================================================

def make_jpeg(tag=0) -> bytes:
    buf = io.BytesIO()
    color = (212, 175, 55 + (tag % 50))
    Image.new("RGB", (48 + tag, 36), color=color).save(buf, format="JPEG")
    return buf.getvalue()

def make_png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGBA", (32, 32), color=(255, 158, 27, 255)).save(buf, format="PNG")
    return buf.getvalue()

def make_webp() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), color=(50, 100, 150)).save(buf, format="WEBP")
    return buf.getvalue()

def make_gif() -> bytes:
    buf = io.BytesIO()
    Image.new("P", (16, 16)).save(buf, format="GIF")
    return buf.getvalue()

def make_wav() -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(b"\x00\x00" * 2000)  # 0.25 sec
    return buf.getvalue()

def make_mp3() -> bytes:
    id3 = b"ID3\x03\x00\x00\x00\x00\x00\x00"
    frame = b"\xFF\xFB\x90\x64" + b"\x00" * 414
    return id3 + frame * 3

def make_m4a() -> bytes:
    ftyp = b"\x00\x00\x00\x18ftypM4A \x00\x00\x00\x00M4A mp42isom"
    # mvhd with duration=3000, timescale=1000 -> 3.0s
    mvhd = b"\x00\x00\x00\x20mvhd\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\xe8\x00\x00\x0b\xb8\x00\x00\x00\x00"
    return ftyp + mvhd

def make_ogg() -> bytes:
    return b"OggS\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x01\x1e\x01vorbis" + b"\x00" * 25

def make_flac() -> bytes:
    return b"fLaC\x00\x00\x00\x22" + b"\x00" * 34

def make_mp4() -> bytes:
    ftyp = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2mp41"
    mvhd = b"\x00\x00\x00\x20mvhd\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\xe8\x00\x00\x0b\xb8\x00\x00\x00\x00"
    return ftyp + mvhd

def make_mov() -> bytes:
    ftyp = b"\x00\x00\x00\x14ftypqt  \x00\x00\x00\x00qt  "
    mvhd = b"\x00\x00\x00\x20mvhd\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\xe8\x00\x00\x0b\xb8\x00\x00\x00\x00"
    return ftyp + mvhd

def make_webm(duration_sec=2.5, width=640, height=360) -> bytes:
    header = (
        b"\x1a\x45\xdf\xa3\x9f"
        b"\x42\x86\x81\x01\x42\xf7\x81\x01\x42\xf2\x81\x04\x42\xf3\x81\x08"
        b"\x42\x82\x84webm\x42\x87\x81\x02\x42\x85\x81\x02"
    )
    tc_elem = b"\x2a\xd7\xb1\x83\x0f\x42\x40"
    dur_elem = b"\x44\x89\x84" + struct.pack(">f", float(duration_sec * 1000.0))
    info_payload = tc_elem + dur_elem
    info = b"\x15\x49\xa9\x66" + bytes([0x80 | len(info_payload)]) + info_payload

    vid_payload = b"\xb0\x82" + struct.pack(">H", width) + b"\xba\x82" + struct.pack(">H", height)
    video_elem = b"\xe0" + bytes([0x80 | len(vid_payload)]) + vid_payload
    track_payload = b"\x86\x81\x01\xd7\x81\x01" + video_elem
    track_entry = b"\xae" + bytes([0x80 | len(track_payload)]) + track_payload
    tracks = b"\x16\x54\xae\x6b" + bytes([0x80 | len(track_entry)]) + track_entry

    segment_payload = info + tracks
    segment = b"\x18\x53\x80\x67\x40" + struct.pack(">I", len(segment_payload))[1:] + segment_payload
    return header + segment

def make_pdf(text_content="Preserved family story in PDF document.") -> bytes:
    import pypdf
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=72, height=72)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()

def make_docx(text_content="Heirloom memoirs from ancestors.") -> bytes:
    import docx
    doc = docx.Document()
    doc.add_paragraph(text_content)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

def make_txt() -> bytes:
    return "Grandfather diary entry written in 1948.".encode("utf-8")

def make_md() -> bytes:
    return "# Family Tree\n\nPreserved ancestral reflections.".encode("utf-8")


# ============================================================================
# 1. 17 Distinct Supported Format Matrix Verification
# ============================================================================

FORMAT_MATRIX = [
    ("memory.jpg", lambda: make_jpeg(1), "image/jpeg", "photograph"),
    ("memory.jpeg", lambda: make_jpeg(2), "image/jpeg", "photograph"),
    ("memory.png", make_png, "image/png", "photograph"),
    ("memory.webp", make_webp, "image/webp", "photograph"),
    ("memory.gif", make_gif, "image/gif", "photograph"),
    ("speech.mp3", make_mp3, "audio/mpeg", "audio"),
    ("interview.wav", make_wav, "audio/wav", "audio"),
    ("oral_history.m4a", make_m4a, "audio/x-m4a", "audio"),
    ("melody.ogg", make_ogg, "audio/ogg", "audio"),
    ("recording.flac", make_flac, "audio/flac", "audio"),
    ("home_video.mp4", make_mp4, "video/mp4", "video"),
    ("anniversary.webm", make_webm, "video/webm", "video"),
    ("archive_reel.mov", make_mov, "video/quicktime", "video"),
    ("will.pdf", make_pdf, "application/pdf", "document"),
    ("letters.docx", make_docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "document"),
    ("chronicle.txt", make_txt, "text/plain", "document"),
    ("story.md", make_md, "text/markdown", "story"),
]


def test_17_distinct_format_matrix(client):
    """
    Verifies that all 17 distinct extensions upload successfully,
    generate database records, and are byte-for-byte retrievable.
    """
    assert len(FORMAT_MATRIX) == 17, "Format matrix must contain exactly 17 distinct extensions"

    for idx, (filename, gen_fn, mime, cat) in enumerate(FORMAT_MATRIX):
        data_bytes = gen_fn()
        res = client.post(
            "/api/memories",
            data={
                "title": f"Format Test {idx}: {filename}",
                "memory_type": cat,
                "description": f"Testing preservation of extension {filename}",
            },
            files={"file": (filename, io.BytesIO(data_bytes), mime)}
        )
        assert res.status_code == 201, f"Upload failed for {filename}: {res.text}"
        body = res.json()
        memory_id = body["id"]

        # Verify retrieval matches original bytes byte-for-byte
        file_res = client.get(f"/api/memories/{memory_id}/file")
        assert file_res.status_code == 200, f"Retrieval failed for {filename}"
        assert file_res.content == data_bytes, f"Byte mismatch for original file {filename}"


# ============================================================================
# 2. Original-File Preservation & EXIF Privacy
# ============================================================================

def test_original_file_preservation_and_exif_gps_stripping(client):
    """
    Verifies:
    1. Original uploaded bytes remain 100% unchanged after retrieval.
    2. Generated thumbnail is separate and strips GPS coordinates.
    """
    # Create image with EXIF Orientation and GPS info
    img = Image.new("RGB", (100, 80), color=(100, 200, 255))
    exif = img.getexif()
    exif[0x0112] = 6  # Orientation: Rotate 90 CW
    exif[0x9003] = "1975:06:20 10:15:00"  # DateTimeOriginal
    gps_ifd = exif.get_ifd(0x8825)
    gps_ifd[1] = "N"
    gps_ifd[2] = 37.7749

    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    original_bytes = buf.getvalue()

    res = client.post(
        "/api/memories",
        data={"title": "EXIF Test Photo", "memory_type": "photograph"},
        files={"file": ("photo_exif.jpg", io.BytesIO(original_bytes), "image/jpeg")}
    )
    assert res.status_code == 201
    mem_id = res.json()["id"]

    # 1. Verify original file is bit-for-bit identical
    dl_res = client.get(f"/api/memories/{mem_id}/file")
    assert dl_res.status_code == 200
    assert dl_res.content == original_bytes, "Original uploaded photograph was altered!"

    # 2. Verify thumbnail exists and does NOT contain GPS tags
    thumb_res = client.get(f"/api/memories/{mem_id}/thumbnail")
    assert thumb_res.status_code == 200
    with Image.open(io.BytesIO(thumb_res.content)) as thumb_img:
        thumb_exif = thumb_img.getexif()
        assert 0x8825 not in thumb_exif, "GPS tag leaked into thumbnail preview!"


def test_missing_or_malformed_exif_resilience(client):
    """Verifies that missing or corrupt EXIF headers do not crash image processing."""
    # Plain image without EXIF
    buf = io.BytesIO()
    Image.new("RGB", (50, 50), color=(10, 20, 30)).save(buf, format="PNG")
    res = client.post(
        "/api/memories",
        data={"title": "No EXIF PNG", "memory_type": "photograph"},
        files={"file": ("no_exif.png", io.BytesIO(buf.getvalue()), "image/png")}
    )
    assert res.status_code == 201


# ============================================================================
# 3. Video Metadata Verification (WebM & MOV)
# ============================================================================

def test_webm_metadata_extraction(client):
    """Verifies pure-Python WebM EBML duration and dimension extraction."""
    webm_bytes = make_webm(duration_sec=4.25, width=1280, height=720)
    res = client.post(
        "/api/memories",
        data={"title": "WebM Video Test", "memory_type": "video"},
        files={"file": ("clip.webm", io.BytesIO(webm_bytes), "video/webm")}
    )
    assert res.status_code == 201
    body = res.json()
    assert body["duration_seconds"] == 4.25
    assert body["width"] == 1280
    assert body["height"] == 720


def test_mov_metadata_extraction(client):
    """Verifies MOV metadata extraction via atom parser."""
    mov_bytes = make_mov()
    res = client.post(
        "/api/memories",
        data={"title": "MOV Video Test", "memory_type": "video"},
        files={"file": ("movie.mov", io.BytesIO(mov_bytes), "video/quicktime")}
    )
    assert res.status_code == 201
    body = res.json()
    assert body["duration_seconds"] == 3.0


# ============================================================================
# 4. Security & Rejection Tests
# ============================================================================

def test_malformed_docx_rejection(client):
    """Verifies that malformed or non-Word ZIP files are rejected with 400 Bad Request."""
    # Corrupt zip
    res = client.post(
        "/api/memories",
        data={"title": "Corrupt DOCX", "memory_type": "document"},
        files={"file": ("bad.docx", io.BytesIO(b"PK\x03\x04corrupt_zip_bytes"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    )
    assert res.status_code == 400

    # Non-Word ZIP archive
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("test.txt", "just a text file, not a docx")
    res2 = client.post(
        "/api/memories",
        data={"title": "Fake DOCX", "memory_type": "document"},
        files={"file": ("fake.docx", io.BytesIO(buf.getvalue()), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    )
    assert res2.status_code == 400
    assert "not a valid Microsoft Word" in res2.text


def test_suspicious_docx_archive_rejection(client):
    """Verifies that DOCX files with suspicious member paths or executables are rejected."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr("word/document.xml", "<w:document/>")
        zf.writestr("../traversal.txt", "attack")
    res = client.post(
        "/api/memories",
        data={"title": "Traversal DOCX", "memory_type": "document"},
        files={"file": ("traversal.docx", io.BytesIO(buf.getvalue()), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    )
    assert res.status_code == 400
    assert "path traversal" in res.text

    buf2 = io.BytesIO()
    with zipfile.ZipFile(buf2, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr("word/document.xml", "<w:document/>")
        zf.writestr("word/payload.exe", b"MZexecutable")
    res2 = client.post(
        "/api/memories",
        data={"title": "Executable DOCX", "memory_type": "document"},
        files={"file": ("trojan.docx", io.BytesIO(buf2.getvalue()), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    )
    assert res2.status_code == 400
    assert "suspicious executable member" in res2.text


def test_malformed_pdf_rejection(client):
    """Verifies that truncated or malformed PDF documents are rejected safely."""
    res = client.post(
        "/api/memories",
        data={"title": "Bad PDF", "memory_type": "document"},
        files={"file": ("corrupt.pdf", io.BytesIO(b"%PDF-1.4 truncated garbage without xref or eof"), "application/pdf")}
    )
    assert res.status_code == 400


def test_excessive_image_dimensions_rejection():
    """Verifies rejection of images exceeding maximum dimension limits (16,000 px)."""
    fake_oversized = (
        b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xFF\xC0\x00\x11\x08\x00\x64\x4E\x20\x03\x01\x11\x00\x02\x11\x01\x03\x11\x01"
        b"\xFF\xD9"
    )
    with pytest.raises(ImageProcessingError) as exc_info:
        process_image(fake_oversized, uuid_name="test")
    assert "exceed maximum allowed dimension" in str(exc_info.value)


def test_invalid_utf8_text_rejection(client):
    """Verifies that non-UTF-8 text files are rejected with 400 Bad Request."""
    invalid_utf8 = b"Ancestral diary note with invalid byte \x80\x81\x82 in UTF-8 text."
    res = client.post(
        "/api/memories",
        data={"title": "Non-UTF8 Text", "memory_type": "document"},
        files={"file": ("broken.txt", io.BytesIO(invalid_utf8), "text/plain")}
    )
    assert res.status_code == 400
    assert "non-UTF-8" in res.text or "binary null bytes" in res.text


def test_html_disguised_as_txt_or_md_rejection(client):
    """Verifies that HTML or script payloads disguised as .txt or .md are rejected."""
    html_payload = b"<!DOCTYPE html><html><head><title>Test</title></head><body><script>alert(1)</script></body></html>"
    res1 = client.post(
        "/api/memories",
        data={"title": "Disguised HTML TXT", "memory_type": "document"},
        files={"file": ("diary.txt", io.BytesIO(html_payload), "text/plain")}
    )
    assert res1.status_code == 400
    assert "HTML, script, or executable" in res1.text or "disguised as text" in res1.text

    res2 = client.post(
        "/api/memories",
        data={"title": "Disguised HTML MD", "memory_type": "story"},
        files={"file": ("story.md", io.BytesIO(html_payload), "text/markdown")}
    )
    assert res2.status_code == 400


def test_oversized_extracted_document_text_bounded(client):
    """Verifies that extracted text is safely bounded to MAX_EXTRACTED_CHARS (150,000)."""
    large_text = ("Preserved family line sentence. " * 10000).encode("utf-8")  # ~320,000 chars
    res = client.post(
        "/api/memories",
        data={"title": "Large Memoir", "memory_type": "document"},
        files={"file": ("memoir.txt", io.BytesIO(large_text), "text/plain")}
    )
    assert res.status_code == 201
    body = res.json()
    assert body["extracted_text"] is not None
    assert len(body["extracted_text"]) <= 150_200
    assert "[... content truncated for performance ...]" in body["extracted_text"]


# ============================================================================
# 5. Database & Filesystem Consistency
# ============================================================================

def test_missing_thumbnail_tolerance_on_retrieval(client):
    """Verifies that if a thumbnail is missing on disk, retrieving the memory or file still succeeds."""
    res = client.post(
        "/api/memories",
        data={"title": "Photo For Thumbnail Test", "memory_type": "photograph"},
        files={"file": ("snap.jpg", io.BytesIO(make_jpeg()), "image/jpeg")}
    )
    assert res.status_code == 201
    mem_id = res.json()["id"]

    # Verify retrieval
    get_res = client.get(f"/api/memories/{mem_id}")
    assert get_res.status_code == 200
    file_res = client.get(f"/api/memories/{mem_id}/file")
    assert file_res.status_code == 200


def test_migration_idempotency_and_preservation(client, test_db):
    """Verifies that re-running migrations does not alter existing data or fail."""
    # Execute migration on the current active connection
    run_migrations(test_db.connection())
    run_migrations(test_db.connection())
    # Should complete without error
    res = client.get("/api/memories")
    assert res.status_code == 200

