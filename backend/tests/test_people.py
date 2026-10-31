"""
Tests for People directory and associated memories.
"""
import io
from backend.tests.test_multimedia import create_valid_jpeg


def test_create_and_list_people(client):
    res = client.post(
        "/api/people",
        json={
            "full_name": "Eleanor Vance",
            "relationship": "Maternal Grandmother",
            "biography": "Born in 1928 in Yorkshire. Master weaver and storyteller."
        }
    )
    assert res.status_code == 201
    person = res.json()
    assert person["full_name"] == "Eleanor Vance"
    person_id = person["id"]

    # List people
    list_res = client.get("/api/people")
    assert list_res.status_code == 200
    people = list_res.json()
    assert any(p["id"] == person_id for p in people)


def test_person_associated_memories(client):
    # 1. Create person
    p_res = client.post(
        "/api/people",
        json={"full_name": "Arthur Vance", "relationship": "Grandfather"}
    )
    person_id = p_res.json()["id"]

    # 2. Upload memory tagged with person using valid JPEG
    file_bytes = create_valid_jpeg()
    upload_res = client.post(
        "/api/memories",
        data={
            "title": "Arthur in Workshop",
            "memory_type": "photograph",
            "person_ids": person_id
        },
        files={"file": ("arthur.jpg", io.BytesIO(file_bytes), "image/jpeg")}
    )
    assert upload_res.status_code == 201

    # 3. Retrieve memories for person
    mem_res = client.get(f"/api/people/{person_id}/memories")
    assert mem_res.status_code == 200
    memories = mem_res.json()
    assert len(memories) == 1
    assert memories[0]["title"] == "Arthur in Workshop"
