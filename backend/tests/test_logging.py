"""结构化日志与 request_id 追踪测试（Task 5）。"""
import logging


def test_request_id_header_in_response(client):
    """中间件应为每个响应注入 X-Request-ID 头。"""
    resp = client.get("/health")
    assert resp.status_code == 200
    rid = resp.headers.get("x-request-id")
    assert rid is not None, "响应缺少 X-Request-ID 头"
    assert len(rid) == 8


def test_request_id_unique_per_request(client):
    """每个请求的 request_id 应互不相同。"""
    r1 = client.get("/health")
    r2 = client.get("/health")
    rid1 = r1.headers.get("x-request-id")
    rid2 = r2.headers.get("x-request-id")
    assert rid1 is not None
    assert rid2 is not None
    assert rid1 != rid2


def test_request_log_generated(client, caplog):
    """每个请求应生成一条包含方法与路径的日志记录。"""
    with caplog.at_level(logging.INFO, logger="gradpath"):
        client.get("/health")
    messages = [record.getMessage() for record in caplog.records]
    assert any("GET" in m and "/health" in m for m in messages), messages
