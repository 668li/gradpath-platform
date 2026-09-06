"""对抗审查（2026-09-05）回归测试：Redis 往返语义下的缓存命中不得 500。

背景：生产 Redis 路径 json.dumps(ORM/模型) 会存成字符串垃圾，缓存命中
response 校验失败即 500。dev 无 Redis（内存 fallback 存原对象）测不出，
故本文件用 monkeypatch 模拟 Redis 的"序列化→反序列化"往返语义。

已实证并修复的三处：
- /api/kaoyan/experience-posts（模型）— 51b3e4c 修复
- /api/grad-intel/yanzhao-programs（ORM 列表）— 本轮修复
- /api/grad-intel/adjustments（ORM 列表）— 本轮修复
"""

import json

import pytest

from app.core import cache as cache_mod
from app.core.cache import _json_default


@pytest.fixture
def redis_like_cache(monkeypatch):
    """把 cache.set 改造为模拟 Redis：写入前序列化→反序列化一个来回。"""
    original_set = cache_mod.cache.set

    def redis_like_set(key, value, ttl=300):
        serialized = json.dumps(value, ensure_ascii=False, default=_json_default)
        original_set(key, json.loads(serialized), ttl=ttl)

    monkeypatch.setattr(cache_mod.cache, "set", redis_like_set)
    yield


def _double_call(client, path: str, redis_like_cache):
    first = client.get(path)
    assert first.status_code == 200, f"首次请求失败: {path}"
    second = client.get(path)
    assert second.status_code == 200, f"缓存命中请求失败（模拟 Redis 往返）: {path}"
    assert second.json() == first.json()


def test_yanzhao_programs_cache_hit_ok(client, redis_like_cache):
    _double_call(client, "/api/grad-intel/yanzhao-programs", redis_like_cache)


def test_adjustments_cache_hit_ok(client, redis_like_cache):
    _double_call(client, "/api/grad-intel/adjustments", redis_like_cache)


def test_experience_posts_cache_hit_ok(client, redis_like_cache):
    _double_call(client, "/api/kaoyan/experience-posts", redis_like_cache)


def test_create_post_forces_user_source_platform(client, auth_headers):
    """对抗审查 B：客户端声明的 source_platform 必须被服务端覆盖为 user。"""
    resp = client.post(
        "/api/kaoyan/experience-posts",
        headers=auth_headers,
        json={
            "title": "来源伪造测试",
            "content": "尝试把来源标成爬虫搬运",
            "source_platform": "crawler",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["source_platform"] == "user"
