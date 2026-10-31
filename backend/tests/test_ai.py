"""
Tests for Ollama AI integration and graceful offline handling.
"""
def test_ai_status_offline_graceful(client):
    # Tests that when Ollama is offline or uninstalled, endpoint gracefully responds with offline status
    res = client.get("/api/ai/status")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "configured_model" in data
    assert data["configured_model"] == "qwen2.5:3b"
    assert "setup_instructions" in data
    assert "ollama" in data["setup_instructions"].lower()


def test_ai_models_endpoint(client):
    res = client.get("/api/ai/models")
    assert res.status_code == 200
    data = res.json()
    assert "models" in data
    assert isinstance(data["models"], list)
    assert data["configured_model"] == "qwen2.5:3b"

