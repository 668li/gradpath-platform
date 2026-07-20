"""Metrics API 测试。"""
import pytest


class TestMetricsEndpoint:
    def test_metrics_returns_prometheus_format(self, client):
        """Metrics 端点返回 Prometheus 格式"""
        resp = client.get("/api/metrics")
        assert resp.status_code == 200
        assert "text/plain" in resp.headers["content-type"]

    def test_metrics_contains_request_count(self, client):
        """Metrics 包含请求计数"""
        resp = client.get("/api/metrics")
        content = resp.text
        assert "gradpath_requests_total" in content

    def test_metrics_contains_error_count(self, client):
        """Metrics 包含错误计数"""
        resp = client.get("/api/metrics")
        content = resp.text
        assert "gradpath_errors_total" in content

    def test_metrics_contains_error_rate(self, client):
        """Metrics 包含错误率"""
        resp = client.get("/api/metrics")
        content = resp.text
        assert "gradpath_error_rate" in content

    def test_metrics_contains_response_time_histogram(self, client):
        """Metrics 包含响应时间直方图"""
        resp = client.get("/api/metrics")
        content = resp.text
        assert "gradpath_response_time_ms" in content

    def test_metrics_histogram_buckets(self, client):
        """Metrics 直方图包含桶"""
        resp = client.get("/api/metrics")
        content = resp.text
        assert 'gradpath_response_time_ms_bucket{le="50"}' in content
        assert 'gradpath_response_time_ms_bucket{le="+Inf"}' in content

    def test_metrics_sum_and_count(self, client):
        """Metrics 包含总和和计数"""
        resp = client.get("/api/metrics")
        content = resp.text
        assert "gradpath_response_time_ms_sum" in content
        assert "gradpath_response_time_ms_count" in content


class TestMetricsRecording:
    def test_record_request_increments_counter(self):
        """记录请求应增加计数器"""
        from app.api.metrics import _request_count, record_request

        initial_total = _request_count.get("__total__", 0)
        record_request("GET", "/api/test", 200, 10.0)
        assert _request_count.get("__total__", 0) == initial_total + 1

    def test_record_error_increments_error_counter(self):
        """记录错误应增加错误计数器"""
        from app.api.metrics import _error_count, record_request

        initial_errors = _error_count.get("__total__", 0)
        record_request("GET", "/api/test", 500, 100.0)
        assert _error_count.get("__total__", 0) == initial_errors + 1

    def test_record_response_time(self):
        """记录响应时间"""
        from app.api.metrics import _response_times, record_request

        initial_count = len(_response_times)
        record_request("POST", "/api/test", 201, 50.0)
        assert len(_response_times) == initial_count + 1
