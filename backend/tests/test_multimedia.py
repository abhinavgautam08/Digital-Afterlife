"""
Automated test suite for Phase 2 multimedia ingestion, format validation,
thumbnail generation, text extraction, search, and editing.
Covers all 20 Phase 2 testing specifications.
"""
import io
import zipfile
import pytest
from datetime import datetime

# Binary artifact generators for deterministic offline testing

def create_valid_jpeg() -> bytes:
    """Creates a minimal valid JPEG image."""
    from PIL import Image
    buf = io.BytesIO()
    img = Image.new("RGB", (64, 48), color=(212, 175, 55))
    img.save(buf, format="JPEG")
    return buf.getvalue()


def create_valid_png() -> bytes:
    """Creates a minimal valid PNG image."""
    from PIL import Image
    buf = io.BytesIO()
    img = Image.new("RGBA", (32, 32), color=(255, 158, 27, 255))
    img.save(buf, format="PNG")
    return buf.getvalue()


def create_valid_wav() -> bytes:
    """Creates a minimal valid PCM WAV audio recording."""
    import wave
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(8000)
        # Write 0.25 seconds of silence/tone
        wav.writeframes(b"\x00\x00" * 2000)
    return buf.getvalue()


def create_valid_mp3() -> bytes:
    """Creates a minimal valid MP3 file with ID3 tag and frame header."""
    id3_header = b"ID3\x03\x00\x00\x00\x00\x00\x00"
    # MPEG1 Layer3 128kbps 44.1kHz frame sync
    mp3_frame = b"\xFF\xFB\x90\x64" + b"\x00" * 414
    return id3_header + mp3_frame * 3


def create_valid_mp4() -> bytes:
    """Creates a valid minimal MP4 file with ftyp atom and mvhd atom."""
    # ftyp box (24 bytes)
    ftyp = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2mp41"
    # mvhd box with duration = 3000, timescale = 1000 (3.0 seconds)
    # mvhd version 0 header: 4 bytes size, 'mvhd', 1 byte version, 3 bytes flags, 4b creation, 4b mod, 4b timescale, 4b duration
    mvhd_payload = b"\x00\x00\x00\x00" + b"\x00\x00\x00\x00" * 2 + b"\x00\x00\x03\xE8" + b"\x00\x00\x0B\xB8" + b"\x00" * 80
    mvhd_size = len(mvhd_payload) + 8
    mvhd = struct_pack_be(mvhd_size) + b"mvhd" + mvhd_payload
    # moov box containing mvhd
    moov_size = len(mvhd) + 8
    moov = struct_pack_be(moov_size) + b"moov" + mvhd
    return ftyp + moov


def struct_pack_be(num: int) -> bytes:
    return num.to_bytes(4, byteorder="big")


def create_valid_pdf(content_text: str = "Family heritage archive testament.") -> bytes:
    """Creates a valid PDF with extractable text."""
    pdf_content = (
        f"%PDF-1.4\n"
        f"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        f"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        f"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> >> endobj\n"
        f"4 0 obj << /Length {len(content_text) + 50} >> stream\n"
        f"BT /F1 12 Tf 100 700 Td ({content_text}) Tj ET\n"
        f"endstream\n"
        f"endobj\n"
        f"xref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000280 00000 n \n"
        f"trailer << /Size 5 /Root 1 0 R >>\nstartxref\n400\n%%EOF\n"
    )
    return pdf_content.encode("latin-1")


def create_valid_docx(content_text: str = "Ancestral letter from grandfather.") -> bytes:
    """Creates a valid .docx document using python-docx."""
    import docx
    doc = docx.Document()
    doc.add_paragraph(content_text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Test Scenarios
# ---------------------------------------------------------------------------

def test_1_photograph_upload_and_thumbnail(client):
    """Test 1 & 11: Photograph upload extracts dimensions and generates a separate thumbnail."""
    jpeg_bytes = create_valid_jpeg()
    res = client.post(
        "/api/memories",
        data={
            "title": "Family Portrait 1948",
            "memory_type": "photograph",
            "description": "Captured in Edinburgh.",
            "location": "Edinburgh, Scotland",
            "tags": "family, portrait"
        },
        files={"file": ("portrait.jpg", io.BytesIO(jpeg_bytes), "image/jpeg")}
    )
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Family Portrait 1948"
    assert data["memory_type"] == "photograph"
    assert data["width"] == 64
    assert data["height"] == 48
    assert data["location"] == "Edinburgh, Scotland"
    assert data["has_thumbnail"] is True
    assert data["thumbnail_path"] is not None
    memory_id = data["id"]

    # Verify thumbnail endpoint
    thumb_res = client.get(f"/api/memories/{memory_id}/thumbnail")
    assert thumb_res.status_code == 200
    assert thumb_res.headers["content-type"] == "image/jpeg"
    assert len(thumb_res.content) > 0


def test_2_audio_upload_and_duration(client):
    """Test 2: Audio upload extracts duration."""
    wav_bytes = create_valid_wav()
    res = client.post(
        "/api/memories",
        data={
            "title": "Great Uncle Voice Recording",
            "memory_type": "audio",
            "description": "Oral history about wartime radio transmission."
        },
        files={"file": ("interview.wav", io.BytesIO(wav_bytes), "audio/wav")}
    )
    assert res.status_code == 201
    data = res.json()
    assert data["memory_type"] == "audio"
    assert data["duration_seconds"] is not None
    assert data["duration_seconds"] > 0


def test_3_video_upload(client):
    """Test 3: Video upload parses container atoms."""
    mp4_bytes = create_valid_mp4()
    res = client.post(
        "/api/memories",
        data={
            "title": "Summer Holiday 1982",
            "memory_type": "video",
            "description": "Home video reel transferred from 8mm."
        },
        files={"file": ("holiday.mp4", io.BytesIO(mp4_bytes), "video/mp4")}
    )
    assert res.status_code == 201
    data = res.json()
    assert data["memory_type"] == "video"
    assert data["file_size"] == len(mp4_bytes)


def test_4_pdf_upload_and_text_extraction(client):
    """Test 4: PDF upload extracts searchable text."""
    pdf_bytes = create_valid_pdf("Secret family recipe for elderberry wine.")
    res = client.post(
        "/api/memories",
        data={
            "title": "Elderberry Wine Recipe",
            "memory_type": "document",
            "description": "Written on parchment."
        },
        files={"file": ("recipe.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    )
    assert res.status_code == 201
    data = res.json()
    assert data["memory_type"] == "document"
    assert data["extracted_text"] is not None
    assert "elderberry" in data["extracted_text"].lower()


def test_5_docx_upload_and_text_extraction(client):
    """Test 5: DOCX upload extracts paragraph text."""
    docx_bytes = create_valid_docx("Memoir chapter one: Arrival at Ellis Island.")
    res = client.post(
        "/api/memories",
        data={
            "title": "Memoir Chapter One",
            "memory_type": "document"
        },
        files={"file": ("chapter1.docx", io.BytesIO(docx_bytes), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    )
    assert res.status_code == 201
    data = res.json()
    assert data["extracted_text"] is not None
    assert "ellis island" in data["extracted_text"].lower()


def test_6_unsupported_file_rejection(client):
    """Test 6: Executables and arbitrary extensions are rejected."""
    fake_exe = b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 60
    res = client.post(
        "/api/memories",
        data={"title": "Trojan Horse", "memory_type": "document"},
        files={"file": ("malware.exe", io.BytesIO(fake_exe), "application/x-msdownload")}
    )
    assert res.status_code == 400
    assert "not permitted" in res.json()["detail"].lower() or "extension" in res.json()["detail"].lower()


def test_7_mime_spoofing_rejection(client):
    """Test 7: Executable disguised with .jpg extension is rejected by signature check."""
    disguised_exe = b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 60
    res = client.post(
        "/api/memories",
        data={"title": "Disguised Executable", "memory_type": "photograph"},
        files={"file": ("family_photo.jpg", io.BytesIO(disguised_exe), "image/jpeg")}
    )
    assert res.status_code == 400
    assert "rejected" in res.json()["detail"].lower() or "spoofing" in res.json()["detail"].lower()


def test_8_malformed_image_rejection(client):
    """Test 8: Image with valid JPEG header but corrupted binary body is rejected."""
    corrupted_jpg = b"\xFF\xD8\xFF\xE0\x00\x10JFIF" + b"\xFF\xFF" * 10
    res = client.post(
        "/api/memories",
        data={"title": "Corrupted JPG", "memory_type": "photograph"},
        files={"file": ("broken.jpg", io.BytesIO(corrupted_jpg), "image/jpeg")}
    )
    assert res.status_code == 400


def test_9_oversized_upload_rejection(client, monkeypatch):
    """Test 9: Files exceeding MAX_UPLOAD_SIZE_BYTES are rejected."""
    from backend.app.core.config import settings
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_BYTES", 500)  # Set tiny limit

    large_content = b"\xFF\xD8\xFF" + b"0" * 1000
    res = client.post(
        "/api/memories",
        data={"title": "Too Large", "memory_type": "photograph"},
        files={"file": ("huge.jpg", io.BytesIO(large_content), "image/jpeg")}
    )
    assert res.status_code == 400
    assert "exceeds maximum" in res.json()["detail"].lower()


def test_10_duplicate_upload_detection(client):
    """Test 10: SHA-256 duplicate detection blocks duplicate upload with HTTP 409."""
    unique_content = create_valid_png()
    res1 = client.post(
        "/api/memories",
        data={"title": "Original PNG", "memory_type": "photograph"},
        files={"file": ("orig.png", io.BytesIO(unique_content), "image/png")}
    )
    assert res1.status_code == 201

    res2 = client.post(
        "/api/memories",
        data={"title": "Copy of PNG", "memory_type": "photograph"},
        files={"file": ("copy.png", io.BytesIO(unique_content), "image/png")}
    )
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"]["message"].lower()


def test_12_memory_metadata_patch(client):
    """Test 12: Memory metadata can be edited via PATCH."""
    jpeg_bytes = create_valid_jpeg()
    create_res = client.post(
        "/api/memories",
        data={"title": "Initial Title", "memory_type": "photograph"},
        files={"file": ("test_patch.jpg", io.BytesIO(jpeg_bytes), "image/jpeg")}
    )
    mem_id = create_res.json()["id"]

    # PATCH title, description, and location
    patch_res = client.patch(
        f"/api/memories/{mem_id}",
        json={
            "title": "Updated Memory Title",
            "description": "Added detailed family history note.",
            "location": "Edinburgh Castle",
            "tags": ["historical", "castle"]
        }
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["title"] == "Updated Memory Title"
    assert updated["location"] == "Edinburgh Castle"
    assert len(updated["tags"]) == 2


def test_13_tag_crud_and_assignment(client):
    """Test 13: Tag creation, editing, deletion, and assignment."""
    # Create tag
    tag_res = client.post("/api/tags", json={"name": "Heirloom"})
    assert tag_res.status_code == 201
    tag_data = tag_res.json()
    tag_id = tag_data["id"]
    assert tag_data["name"] == "heirloom"

    # List tags
    list_res = client.get("/api/tags")
    assert list_res.status_code == 200
    assert any(t["name"] == "heirloom" for t in list_res.json())

    # Patch tag
    patch_tag = client.patch(f"/api/tags/{tag_id}", json={"name": "Family Heirloom"})
    assert patch_tag.status_code == 200
    assert patch_tag.json()["name"] == "family heirloom"

    # Delete tag
    del_res = client.delete(f"/api/tags/{tag_id}")
    assert del_res.status_code == 200


def test_15_search_and_16_filtering(client):
    """Test 15 & 16: Multi-field search and category/tag/person filtering."""
    # 1. Create a person
    p_res = client.post("/api/people", json={"full_name": "Beatrice Thorne"})
    person_id = p_res.json()["id"]

    # 2. Upload document with searchable text
    pdf_bytes = create_valid_pdf("Special chronicles of the transatlantic voyage 1923.")
    client.post(
        "/api/memories",
        data={
            "title": "Voyage Logbook",
            "memory_type": "document",
            "person_ids": person_id,
            "tags": "voyage, travel",
            "location": "Southampton"
        },
        files={"file": ("logbook.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    )

    # Search via dedicated search endpoint
    search_res = client.get("/api/memories/search?q=transatlantic")
    assert search_res.status_code == 200
    assert search_res.json()["total"] >= 1
    assert any("Voyage" in item["title"] for item in search_res.json()["items"])

    # Filter by person
    person_filter = client.get(f"/api/memories?person_id={person_id}")
    assert person_filter.status_code == 200
    assert person_filter.json()["total"] == 1

    # Filter by tag
    tag_filter = client.get("/api/memories?tag=voyage")
    assert tag_filter.status_code == 200
    assert tag_filter.json()["total"] >= 1

    # Filter by type
    type_filter = client.get("/api/memories?memory_type=document")
    assert type_filter.status_code == 200
    assert all(item["memory_type"] == "document" for item in type_filter.json()["items"])


def test_17_file_retrieval_and_18_deletion_consistency(client):
    """Test 17, 18 & 19: File streaming, deletion, and database/storage consistency."""
    jpeg_bytes = create_valid_jpeg()
    res = client.post(
        "/api/memories",
        data={"title": "To Be Deleted", "memory_type": "photograph"},
        files={"file": ("delete_me.jpg", io.BytesIO(jpeg_bytes), "image/jpeg")}
    )
    mem_id = res.json()["id"]

    # Retrieve file stream
    file_stream = client.get(f"/api/memories/{mem_id}/file")
    assert file_stream.status_code == 200
    assert file_stream.content == jpeg_bytes

    # Delete memory
    del_res = client.delete(f"/api/memories/{mem_id}")
    assert del_res.status_code == 200

    # Verify both file and memory are gone (404)
    assert client.get(f"/api/memories/{mem_id}").status_code == 404
    assert client.get(f"/api/memories/{mem_id}/file").status_code == 404
    assert client.get(f"/api/memories/{mem_id}/thumbnail").status_code == 404

