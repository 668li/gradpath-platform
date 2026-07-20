"""A14 prometheus_client 多进程监控测试。

验证：
1. app/metrics.py 模块可导入
2. prometheus_client 已安装
3. 5 个核心指标（REQUEST_COUNT / REQUEST_LATENCY / LLM_CALL_COUNT /
   LLM_CALL_LATENCY / ACTIVE_WEBSOCKETS）已定义
4. record_http_request / record_llm_call / set_active_websockets 函数可用
5. render_metrics 返回 prometheus 格式
6. /metrics 端点可访问（需要认证）
7. /api/metrics 旧端点仍可访问（向后兼容）
8. record_http_request 同时写入 prometheus_client 与旧版 record_request
"""
import pytest


class TestMetricsModule:
    """验证 app/metrics.py 模块基础结构。"""

    def test_metrics_module_importable(self):
        """app.metrics 模块可导入。"""
        from app import metrics
        assert hasattr(metrics, "record_http_request")
        assert hasattr(metrics, "record_llm_call")
        assert hasattr(metrics, "set_active_websockets")
        assert hasattr(metrics, "render_metrics")

    def test_prometheus_client_available(self):
        """prometheus_client 已安装。"""
        from app.metrics import is_available
        assert is_available() is True

    def test_request_count_metric_defined(self):
        """REQUEST_COUNT Counter 已定义。"""
        from app.metrics import REQUEST_COUNT
        assert REQUEST_COUNT is not None
        # Counter 应有 _metrics 属性（prometheus_client 内部结构）
        assert hasattr(REQUEST_COUNT, "labels")

    def test_request_latency_metric_defined(self):
        """REQUEST_LATENCY Histogram 已定义。"""
        from app.metrics import REQUEST_LATENCY
        assert REQUEST_LATENCY is not None
        assert hasattr(REQUEST_LATENCY, "labels")

    def test_llm_call_count_metric_defined(self):
        """LLM_CALL_COUNT Counter 已定义。"""
        from app.metrics import LLM_CALL_COUNT
        assert LLM_CALL_COUNT is not None
        assert hasattr(LLM_CALL_COUNT, "labels")

    def test_llm_call_latency_metric_defined(self):
        """LLM_CALL_LATENCY Histogram 已定义。"""
        from app.metrics import LLM_CALL_LATENCY
        assert LLM_CALL_LATENCY is not None
        assert hasattr(LLM_CALL_LATENCY, "labels")

    def test_active_websockets_metric_defined(self):
        """ACTIVE_WEBSOCKETS Gauge 已定义。"""
        from app.metrics import ACTIVE_WEBSOCKETS
        assert ACTIVE_WEBSOCKETS is not None
        assert hasattr(ACTIVE_WEBSOCKETS, "set")


class TestMetricsRendering:
    """验证指标渲染。"""

    def test_render_metrics_returns_bytes_and_content_type(self):
        """render_metrics 返回 bytes 与 content_type。"""
        from app.metrics import render_metrics
        body, content_type = render_metrics()
        assert isinstance(body, bytes)
        assert isinstance(content_type, str)
        assert "text/plain" in content_type

    def test_render_metrics_contains_gradpath_prefix(self):
        """渲染结果包含 gradpath_ 前缀的指标。"""
        from app.metrics import render_metrics, record_http_request
        # 触发一次记录
        record_http_request("GET", "/test", 200, 0.05)
        body, _ = render_metrics()
        text = body.decode("utf-8")
        # 应至少有一个 gradpath_ 开头的指标
        assert "gradpath_" in text


class TestMetricsRecordingFunctions:
    """验证便捷记录函数。"""

    def test_record_http_request_does_not_raise(self):
        """record_http_request 不抛异常。"""
        from app.metrics import record_http_request
        record_http_request("GET", "/api/test", 200, 0.05)
        record_http_request("POST", "/api/test", 500, 1.5)

    def test_record_llm_call_does_not_raise(self):
        """record_llm_call 不抛异常。"""
        from app.metrics import record_llm_call
        record_llm_call(model="gpt-4", status="success", duration_seconds=0.5)
        record_llm_call(model="gpt-4", status="error", duration_seconds=1.5)

    def test_set_active_websockets_does_not_raise(self):
        """set_active_websockets 不抛异常。"""
        from app.metrics import set_active_websockets
        set_active_websockets(0)
        set_active_websockets(5)
        set_active_websockets(0)

    def test_record_http_request_calls_legacy_record_request(self):
        """record_http_request 同时调用旧版 record_request 保持 /api/metrics 兼容。"""
        from app.metrics import record_http_request
        from app.api.metrics import _request_count

        initial = _request_count.get("__total__", 0)
        record_http_request("GET", "/api/compat-test", 200, 0.01)
        assert _request_count.get("__total__", 0) == initial + 1


class TestMetricsEndpoint:
    """验证 /metrics 端点（需要认证）。"""

    def test_metrics_endpoint_requires_auth(self, client):
        """/metrics 未认证返回 401。"""
        resp = client.get("/metrics")
        # FastAPI 默认未认证返回 401
        assert resp.status_code in (401, 403)

    def test_metrics_endpoint_accessible_with_auth(self, client, auth_headers):
        """/metrics 登录后可访问。"""
        resp = client.get("/metrics", headers=auth_headers)
        assert resp.status_code == 200
        # 应返回 prometheus 格式
        assert "text/plain" in resp.headers.get("content-type", "")

    def test_legacy_api_metrics_still_works(self, client):
        """/api/metrics 旧端点仍可访问（无需认证）。"""
        resp = client.get("/api/metrics")
        assert resp.status_code == 200
        # 应包含旧版自定义指标
        assert "gradpath_requests_total" in resp.text


class TestMultiprocessConfig:
    """验证多进程配置辅助函数。"""

    def test_ensure_multiproc_dir_function_exists(self):
        """_ensure_multiproc_dir 函数存在。"""
        from app.metrics import _ensure_multiproc_dir
        assert callable(_ensure_multiproc_dir)

    def test_prometheus_multiproc_dir_constant(self):
        """PROMETHEUS_MULTIPROC_DIR 常量已定义。"""
        from app.metrics import PROMETHEUS_MULTIPROC_DIR
        assert isinstance(PROMETHEUS_MULTIPROC_DIR, str)
        assert len(PROMETHEUS_MULTIPROC_DIR) > 0

    def test_get_registry_returns_collector_registry(self):
        """_get_registry 返回 CollectorRegistry。"""
        from app.metrics import _get_registry
        try:
            from prometheus_client import CollectorRegistry
        except ImportError:
            pytest.skip("prometheus_client 未安装")
        registry = _get_registry()
        assert isinstance(registry, CollectorRegistry)
