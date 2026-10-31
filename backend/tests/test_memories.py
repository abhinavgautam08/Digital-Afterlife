"""
Tests for Memory vault operations: upload, duplicate prevention, pagination, filtering, deletion.
Updated for Phase 2 strict signature validation.
"""
import io
import pytest
from backend.tests.test_multimedia import (
    create_valid_jpeg,
    create_valid_mp3,
    create_valid_wav,
)


def test_upload_and_retrieve_photograph(client):
    valid_jpeg = create_valid_jpeg()
    file = ("grandfather_1975.jpg", io.BytesIO(valid_jpeg), "image/jpeg")

    response = client.post(
        "/api/memories",
        data={
            "title": "Grandfather in 1975",
            "memory_type": "photograph",
            "description": "Found in attic album.",
            "event_date": "1975-06-15",
            "privacy_level": "family",
            "tags": "family, vintage, portrait"
        },
        files={"file": file}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Grandfather in 1975"
    assert data["memory_type"] == "photograph"
    assert data["original_filename"] == "grandfather_1975.jpg"
    assert data["file_size"] == len(valid_jpeg)
    assert len(data["tags"]) == 3
    memory_id = data["id"]

    # Verify retrieval
    get_res = client.get(f"/api/memories/{memory_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == memory_id

    # Verify file content streaming
    file_res = client.get(f"/api/memories/{memory_id}/file")
    assert file_res.status_code == 200
    assert file_res.content == valid_jpeg


def test_prevent_duplicate_upload(client):
    unique_content = create_valid_mp3()
    file1 = ("interview.mp3", io.BytesIO(unique_content), "audio/mpeg")

    res1 = client.post(
        "/api/memories",
        data={"title": "Oral History Part 1", "memory_type": "audio"},
        files={"file": file1}
    )
    assert res1.status_code == 201

    # Attempt to upload identical content with different title
    file2 = ("interview_copy.mp3", io.BytesIO(unique_content), "audio/mpeg")
    res2 = client.post(
        "/api/memories",
        data={"title": "Duplicate Oral History", "memory_type": "audio"},
        files={"file": file2}
    )
    assert res2.status_code == 409
    detail = res2.json()["detail"]
    assert "already exists" in detail["message"].lower()


def test_pagination_and_filtering(client):
    # Upload 3 items
    types = ["photograph", "audio", "document"]
    for i, m_type in enumerate(types):
        if m_type == "photograph":
            content = create_valid_jpeg()
            ext = "jpg"
            mime = "image/jpeg"
        elif m_type == "audio":
            content = create_valid_wav()
            ext = "wav"
            mime = "audio/wav"
        else:
            content = f"Historical letter manuscript content #{i}".encode("utf-8")
            ext = "txt"
            mime = "text/plain"

        client.post(
            "/api/memories",
            data={"title": f"Item {i} {m_type}", "memory_type": m_type},
            files={"file": (f"test_{i}.{ext}", io.BytesIO(content), mime)}
        )

    # Filter by audio
    res_audio = client.get("/api/memories?memory_type=audio")
    assert res_audio.status_code == 200
    items_audio = res_audio.json()["items"]
    assert len(items_audio) == 1
    assert items_audio[0]["memory_type"] == "audio"

    # Search by title
    res_search = client.get("/api/memories?search=Item 0")
    assert res_search.status_code == 200
    assert len(res_search.json()["items"]) == 1

    # Pagination
    res_page = client.get("/api/memories?page=1&size=2")
    assert res_page.status_code == 200
    page_data = res_page.json()
    assert page_data["page"] == 1
    assert page_data["size"] == 2
    assert page_data["total"] == 3
    assert page_data["total_pages"] == 2
    assert len(page_data["items"]) == 2


def test_delete_memory(client):
    content = b"TEMPORARY_RECORD_TEXT"
    file = ("temp.txt", io.BytesIO(content), "text/plain")

    create_res = client.post(
        "/api/memories",
        data={"title": "Temp Record", "memory_type": "document"},
        files={"file": file}
    )
    assert create_res.status_code == 201
    memory_id = create_res.json()["id"]

    # Delete
    del_res = client.delete(f"/api/memories/{memory_id}")
    assert del_res.status_code == 200

    # Ensure 404 now
    assert client.get(f"/api/memories/{memory_id}").status_code == 404
    assert client.get(f"/api/memories/{memory_id}/file").status_code == 404
