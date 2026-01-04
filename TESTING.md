# Testing Playbook

## Backend Suites
- 	ests/test_api.py - happy-path REST flow (calibration -> session -> metrics -> dashboard summary).
- 	ests/test_api_negative.py - validation + rate-limit coverage for critical endpoints.
- 	ests/test_models.py - ORM sanity (UUID defaults, encryption coverage, relationship integrity).
- 	ests/test_retention.py - retention soft/hard delete behaviour and regression fixes.
- 	ests/test_analytics_trends.py - /api/analytics/trends aggregation over sparse days.
- 	ests/test_integration_pipeline.py - ML pipeline harness (stub estimators + REST bridge).
- 	ests/test_ws_manager.py - WebSocket broker handshake, backpressure, heartbeat handling.

## How to Run
`ash
pytest -m smoke
`

pytest.ini scopes discovery to 	ests/ and registers the smoke marker; every module above is tagged so the command runs 19 fast-but-comprehensive cases. Use pytest (without -m smoke) for the full suite or add @pytest.mark.smoke/pytestmark = pytest.mark.smoke to include new tests in the default gate.

Set EAGLEARN_ENCRYPTION_KEY & DATABASE_URL if running outside the provided fixtures—	ests/conftest.py auto-provisions the SQLite schema and resets rate limiters between cases.
