import time


def test_error_codes_present():
    import app as app_module

    app_module.app.testing = True
    client = app_module.app.test_client()

    r = client.get("/api/logs/metrics/download")
    assert r.status_code in (404, 500)
    data = r.get_json()
    assert isinstance(data, dict)
    assert data.get("status") == "error"
    assert isinstance(data.get("error_code"), str)

    r2 = client.get("/this-route-does-not-exist")
    assert r2.status_code == 404
    data2 = r2.get_json()
    assert data2.get("status") == "error"
    assert data2.get("error_code") == "NOT_FOUND"

    r3 = client.post("/api/quality", json={"preset": "balanced"})
    assert r3.status_code in (200, 500)


def test_no_time_tracking_during_calibration():
    from state_manager import SessionState
    from improved_webcam_processor import ImprovedWebcamProcessor

    s = SessionState()
    s.calibration_in_progress = True
    s.focused_time_seconds = 0.0
    s.unfocused_time_seconds = 0.0
    s.last_tracking_update = time.time() - 10.0
    s.last_focus_status = "focused"

    p = ImprovedWebcamProcessor.__new__(ImprovedWebcamProcessor)
    p.state = s

    p._update_time_tracking("focused")
    assert s.focused_time_seconds == 0.0
    assert s.unfocused_time_seconds == 0.0
