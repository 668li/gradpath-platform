"""社区假数据清理（2026-09-05）回归测试。

背景：用户拍板"社区只能有用户自己发的信息"，生产清除了 2187 条脚本注入的
假社区内容。本文件锁住两个防回归点：
1. 社区列表在空表上必须 200 + 空列表（诚实冷启动）。
2. 缓存路径不得把 pydantic 模型序列化成字符串（曾致生产缓存命中 500，
   dev 无 Redis 掩盖了该 bug）。
"""

import json

from app.core.cache import _json_default
from app.schemas.experience_post import ExperiencePostListResponse


def test_experience_posts_empty_list_ok(client):
    """清空社区数据后列表端点必须正常返回空态，而不是 500。"""
    resp = client.get("/api/kaoyan/experience-posts")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_experience_posts_cache_hit_second_call_ok(client):
    """第一次请求填充缓存，第二次（缓存命中）也必须 200 且内容一致。"""
    first = client.get("/api/kaoyan/experience-posts")
    assert first.status_code == 200
    second = client.get("/api/kaoyan/experience-posts")
    assert second.status_code == 200
    assert second.json() == first.json()


def test_cache_json_default_dumps_pydantic_as_dict():
    """json.dumps(default=_json_default) 必须把 pydantic 模型存成 dict。

    事故：default=str 会把整个模型 str() 成字符串存进 Redis，缓存命中后
    response_model 校验失败 -> 500。dev 环境走内存 fallback 存原对象，
    测不出该 bug；只有生产 Redis 路径会炸。
    """
    model = ExperiencePostListResponse(items=[], total=0, page=1, page_size=20)
    serialized = json.dumps(model, ensure_ascii=False, default=_json_default)
    parsed = json.loads(serialized)
    assert isinstance(parsed, dict)
    assert parsed["total"] == 0
    assert parsed["items"] == []
