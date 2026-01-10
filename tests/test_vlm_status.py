def test_environment_includes_vlm_status():
    import app as app_module

    app_module.app.testing = True
    client = app_module.app.test_client()

    r = client.get("/api/environment")
    assert r.status_code == 200
    data = r.get_json()
    assert isinstance(data, dict)
    assert "vlm_status" in data
    assert isinstance(data["vlm_status"], dict)
    assert "status" in data["vlm_status"]
    assert "ready" in data["vlm_status"]
