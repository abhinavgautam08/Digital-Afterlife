"""
Tests for health and system endpoints.
"""
def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "Digital Afterlife" in data["app"]
    assert data["database"] == "connected"


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "memories" in data["philosophy"].lower()


def test_system_status_empty_db(client):
    response = client.get("/api/system/status")
    assert response.status_code == 200
    data = response.json()
    assert data["database_connected"] is True
    assert data["statistics"]["total_memories"] == 0
    assert data["statistics"]["total_people"] == 0
    assert "storage" in data

