def test_health_ok(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["model_loaded"] is True
    assert body["database_available"] is True
    assert body["storage_writable"] is True
    assert isinstance(body["storage_free_mb"], (int, float))


def test_health_degraded_when_model_not_loaded(client):
    client.app.state.yolo_model = None

    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["model_loaded"] is False
