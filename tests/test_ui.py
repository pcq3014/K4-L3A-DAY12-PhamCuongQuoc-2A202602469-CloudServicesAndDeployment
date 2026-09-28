"""Giao diện web và endpoint /history (phần mở rộng, không thuộc checkpoint).

Chạy: pytest tests/test_ui.py -v
"""

from __future__ import annotations


def test_trang_chu_tra_ve_html(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "<title>Day12 Agent</title>" in response.text


def test_trang_chu_khong_nhung_api_key(client, api_key):
    """Trang tĩnh ai cũng tải được — tuyệt đối không chứa secret."""
    assert api_key not in client.get("/").text


def test_history_yeu_cau_api_key(client):
    assert client.get("/history").status_code == 401
    assert client.delete("/history").status_code == 401


def test_history_tra_ve_va_xoa_duoc(client_real_store, auth_headers):
    client_real_store.post("/ask", json={"question": "xin chào"}, headers=auth_headers)

    data = client_real_store.get("/history", headers=auth_headers).json()
    assert data["user_id"] == auth_headers["X-User-Id"]
    assert [m["role"] for m in data["messages"]] == ["user", "assistant"]

    assert client_real_store.delete("/history", headers=auth_headers).status_code == 204
    assert client_real_store.get("/history", headers=auth_headers).json()["messages"] == []


def test_moi_response_co_request_id(client):
    assert client.get("/health").headers.get("X-Request-ID")
