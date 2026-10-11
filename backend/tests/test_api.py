import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root() -> None:
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["app_name"] == "Voice Agent"
    assert "websocket" in data["endpoints"]


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ws_ready_and_echo() -> None:
    with client.websocket_connect("/ws") as ws:
        ready = ws.receive_json()
        assert ready["type"] == "ready"

        payload = b"\x00\x01\x02\x03"
        ws.send_bytes(payload)
        assert ws.receive_bytes() == payload


def test_ws_control_ping_pong() -> None:
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_text(json.dumps({"type": "ping"}))
        assert ws.receive_json() == {"type": "pong"}


def test_ws_invalid_json() -> None:
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_text("not json")
        assert ws.receive_json() == {"type": "error", "reason": "invalid_json"}
