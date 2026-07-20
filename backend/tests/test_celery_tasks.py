"""Celery 任务测试 — 验证任务可被序列化、路由正确。"""
import json


class TestCeleryApp:
    def test_celery_app_importable(self):
        """Celery 应用实例可正常导入。"""
        from app.celery_app import celery_app
        assert celery_app.main == "gradpath"

    def test_task_serializer_is_json(self):
        """任务序列化器为 json（确保跨平台/跨语言兼容）。"""
        from app.celery_app import celery_app
        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.result_serializer == "json"
        assert "json" in celery_app.conf.accept_content

    def test_task_routes_configured(self):
        """crawler_tasks 路由到 crawler 队列，ai_tasks 路由到 ai 队列。"""
        from app.celery_app import celery_app
        routes = celery_app.conf.task_routes
        assert "app.tasks.crawler_tasks.*" in routes
        assert routes["app.tasks.crawler_tasks.*"]["queue"] == "crawler"
        assert "app.tasks.ai_tasks.*" in routes
        assert routes["app.tasks.ai_tasks.*"]["queue"] == "ai"

    def test_reliability_settings(self):
        """关键可靠性配置已开启。"""
        from app.celery_app import celery_app
        # acks_late + reject_on_worker_lost 保证 worker 崩溃后任务重投
        assert celery_app.conf.task_acks_late is True
        assert celery_app.conf.task_reject_on_worker_lost is True
        # 超时配置
        assert celery_app.conf.task_time_limit == 30 * 60
        assert celery_app.conf.task_soft_time_limit == 25 * 60


class TestCrawlerTasks:
    def test_run_crawler_task_registered(self):
        """爬虫任务已注册到 Celery。"""
        from app.celery_app import celery_app
        from app.tasks.crawler_tasks import run_crawler_task
        # 任务名在 Celery 注册表中
        assert "app.tasks.crawler_tasks.run_crawler_task" in celery_app.tasks

    def test_run_scheduled_crawler_task_registered(self):
        """定时爬虫任务已注册。"""
        from app.celery_app import celery_app
        from app.tasks.crawler_tasks import run_scheduled_crawler_task
        assert (
            "app.tasks.crawler_tasks.run_scheduled_crawler_task"
            in celery_app.tasks
        )

    def test_crawler_task_args_json_serializable(self):
        """任务参数必须可 JSON 序列化（Celery 的硬约束）。"""
        args = ("task123", "real_data", False)
        serialized = json.dumps(args)
        assert json.loads(serialized) == list(args)

    def test_crawler_task_signature(self):
        """任务签名与 API 层调用约定一致。"""
        from app.tasks.crawler_tasks import run_crawler_task
        # 检查 task 对象存在且具有 delay 方法
        assert hasattr(run_crawler_task, "delay")
        assert hasattr(run_crawler_task, "apply_async")


class TestAITasks:
    def test_generate_ai_advice_task_registered(self):
        """AI 建议任务已注册。"""
        from app.celery_app import celery_app
        from app.tasks.ai_tasks import generate_ai_advice_async
        assert "app.tasks.ai_tasks.generate_ai_advice_async" in celery_app.tasks

    def test_ai_task_args_json_serializable(self):
        """AI 任务参数（user_id/decision_id 字符串）可 JSON 序列化。"""
        args = (
            "550e8400-e29b-41d4-a716-446655440000",
            "550e8400-e29b-41d4-a716-446655440001",
        )
        serialized = json.dumps(args)
        assert json.loads(serialized) == list(args)

    def test_batch_generate_advice_registered(self):
        """批量 AI 任务已注册。"""
        from app.celery_app import celery_app
        from app.tasks.ai_tasks import batch_generate_advice
        assert "app.tasks.ai_tasks.batch_generate_advice" in celery_app.tasks


class TestCeleryFallback:
    def test_fallback_function_exists(self):
        """Celery 不可用时的兼容入口存在且可调用。"""
        from app.tasks.crawler_tasks import (
            _run_crawler_background_compat,
            _run_scheduled_crawler_compat,
        )
        assert callable(_run_crawler_background_compat)
        assert callable(_run_scheduled_crawler_compat)

    def test_api_dispatcher_exists(self):
        """API 层 Celery 投递辅助函数存在。"""
        from app.api.crawlers import _celery_available, _dispatch_crawler_task
        assert callable(_celery_available)
        assert callable(_dispatch_crawler_task)
