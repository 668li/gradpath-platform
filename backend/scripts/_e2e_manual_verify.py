"""手动 E2E 验证：/admin/research-queue 的 通过/驳回/标记重复 完整流程（计划验证节末项）。

流程：确保 admin 用户 → 登录拿 token → 造 3 条 PENDING（experience_post/kaoyan_news/dark_knowledge，
含 1 条 t_data_source 供回填断言）→ 列表查询 → approve（含 409 重复审核 + 业务表落库 + 双表回填）
→ reject → duplicate → 数据库状态核对 → 清理 E2E 数据。
"""
import hashlib
import json
import sqlite3
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

from app.core.security import hash_password

BASE = "http://localhost:8000"
DB_PATH = Path(__file__).resolve().parents[1] / "gradpath.db"
ADMIN_EMAIL = "admin-e2e@test.com"
ADMIN_PASS = "E2ePass123!"

SEED_ITEMS = [
    {
        "kind": "experience_post",
        "crawler_name": "bilibili_research",
        "source_platform": "bilibili",
        "source_url": "https://b23.tv/e2e-experience-001",
        "title": "E2E 复试经验分享（计算机）",
        "content": "复试流程：笔试 2 小时，面试 20 分钟，重点考察项目经历。",
        "meta": {"author": "E2E-UP主", "view_count": 100, "stage": "kaoyan"},
        "data_source": True,  # 额外造 t_data_source 行验证回填
    },
    {
        "kind": "kaoyan_news",
        "crawler_name": "rss_news_research",
        "source_platform": "rss",
        "source_url": "https://news.e2e.example.com/rss/2026-08-12",
        "title": "E2E 考研资讯：2026 研招政策要点",
        "content": "2026 年全国硕士研究生招生考试报名时间公布。",
        "meta": {"category": "policy", "published_at": "2026-08-12T00:00:00+08:00"},
        "data_source": False,
    },
    {
        "kind": "dark_knowledge",
        "crawler_name": "web_article_research",
        "source_platform": "web",
        "source_url": "https://e2e.example.com/article/dark-001",
        "title": "E2E 暗知识：复试线背后逻辑",
        "content": "某 985 复试线波动背后是推免比例上调。",
        "meta": {"stage": "kaoyan", "category": "复试", "importance": "high"},
        "data_source": False,
    },
]

PASS = []
FAIL = []


def check(name: str, cond: bool, detail: str = ""):
    (PASS if cond else FAIL).append(name)
    mark = "✅" if cond else "❌"
    print(f"  {mark} {name}" + (f"  — {detail}" if detail else ""))


def main() -> int:
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    cur = db.cursor()

    # 0. 确保 admin 用户存在（SQL 直插，密码用应用同款 hash）
    row = db.execute("SELECT id, is_admin FROM users WHERE email=?", (ADMIN_EMAIL,)).fetchone()
    if not row:
        db.execute(
            "INSERT INTO users (id, email, password_hash, name, is_admin) VALUES (?,?,?,?,1)",
            (uuid.uuid4().hex, ADMIN_EMAIL, hash_password(ADMIN_PASS), "E2E管理员"),
        )
        db.commit()
        print("[0] 已创建 admin 用户")
    elif not row["is_admin"]:
        db.execute("UPDATE users SET is_admin=1 WHERE email=?", (ADMIN_EMAIL,))
        db.commit()
        print("[0] admin 用户已就绪（提升为 admin）")
    else:
        print("[0] admin 用户已就绪")

    with httpx.Client(timeout=15) as client:
        # 1. 登录拿 token
        resp = client.post(
            f"{BASE}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASS},
        )
        check("登录获取 token", resp.status_code == 200, f"status={resp.status_code}")
        if resp.status_code != 200:
            print(resp.text)
            return 1
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. 清残留 → 造 3 条 PENDING（整数自增 id 由 SQLite 分配）
        for item in SEED_ITEMS:
            db.execute("DELETE FROM t_external_research_item WHERE source_url=?", (item["source_url"],))
        db.execute("DELETE FROM t_review_queue_item WHERE source_url LIKE '%e2e%'")
        db.execute("DELETE FROM t_data_source WHERE source_url LIKE '%e2e%'")
        db.execute("DELETE FROM experience_posts WHERE source_url LIKE '%e2e%'")
        db.execute("DELETE FROM kaoyan_news WHERE source_url LIKE '%e2e%'")
        db.execute("DELETE FROM dark_knowledge WHERE title LIKE '%E2E%'")
        db.commit()

        queue_ids = {}
        for item in SEED_ITEMS:
            crawl_run_id = str(uuid.uuid4())
            cur.execute(
                "INSERT INTO t_external_research_item "
                "(crawler_name, crawler_run_id, item_type, title, content, source_url, source_platform, external_meta, credibility, review_status) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    item["crawler_name"], crawl_run_id, item["kind"], item["title"],
                    item["content"], item["source_url"], item["source_platform"],
                    json.dumps(item["meta"]), "model_inferred", "PENDING",
                ),
            )
            ext_id = cur.lastrowid
            digest = hashlib.md5(item["source_url"].encode()).hexdigest()[:12]
            cur.execute(
                "INSERT INTO t_review_queue_item "
                "(item_type, ref_item_id, source_url, review_status, biz_req_no) "
                "VALUES ('external_research', ?, ?, 'PENDING', ?)",
                (ext_id, item["source_url"], f"research:{item['crawler_name']}:{digest}"),
            )
            queue_ids[item["kind"]] = cur.lastrowid
            if item.get("data_source"):
                cur.execute(
                    "INSERT INTO t_data_source "
                    "(source_system, source_url, crawled_at, credibility, review_status) "
                    "VALUES ('bilibili', ?, CURRENT_TIMESTAMP, 'user_reported', 'PENDING')",
                    (item["source_url"],),
                )
        db.commit()
        print("[2] 已造 3 条 PENDING 队列数据（id 为整数自增）")

        # 3. 列表查询
        resp = client.get(f"{BASE}/api/admin/research-queue/pending", headers=headers)
        check("列表查询 200", resp.status_code == 200, f"status={resp.status_code}")
        data = resp.json()
        check("列表 total=3", data["total"] == 3, f"total={data['total']}")
        titles = {i["title"] for i in data["items"]}
        check("列表含 3 条 E2E 标题", all(
            t in titles for t in
            ["E2E 复试经验分享（计算机）", "E2E 考研资讯：2026 研招政策要点", "E2E 暗知识：复试线背后逻辑"]
        ))
        exp = next(i for i in data["items"] if i["title"].startswith("E2E 复试"))
        check("列表带 credibility/source_platform",
              exp["credibility"] == "model_inferred" and exp["source_platform"] == "bilibili",
              f"credibility={exp['credibility']} platform={exp['source_platform']}")
        resp = client.get(
            f"{BASE}/api/admin/research-queue/pending?source_platform=bilibili", headers=headers
        )
        check("平台筛选 bilibili=1", resp.json()["total"] == 1, f"total={resp.json()['total']}")

        # 4. approve 第一条（experience_post）
        q_id = queue_ids["experience_post"]
        resp = client.post(f"{BASE}/api/admin/research-queue/{q_id}/approve", json={"note": "E2E 通过"}, headers=headers)
        body = resp.json()
        check("approve 200 + promoted=1", resp.status_code == 200 and body["promoted"] == 1,
              f"status={resp.status_code} promoted={body.get('promoted')} review_status={body.get('review_status')}")
        resp2 = client.post(f"{BASE}/api/admin/research-queue/{q_id}/approve", json={}, headers=headers)
        check("重复 approve 409", resp2.status_code == 409, f"status={resp2.status_code} detail={resp2.json().get('detail')}")
        # 业务表落库
        ep = db.execute(
            "SELECT title, status, source_url, source_platform FROM experience_posts WHERE source_url=?",
            ("https://b23.tv/e2e-experience-001",),
        ).fetchone()
        check("ExperiencePost 落库 status=approved", ep is not None and ep["status"] == "approved",
              f"title={ep['title'] if ep else None} status={ep['status'] if ep else None}")
        ext = db.execute(
            "SELECT review_status FROM t_external_research_item WHERE id=?",
            (body["ref_item_id"],),
        ).fetchone()
        check("ext 回填 APPROVED", ext["review_status"] == "APPROVED",
              f"review_status={ext['review_status']}")
        qrow = db.execute(
            "SELECT reviewed_by, review_status FROM t_review_queue_item WHERE id=?", (q_id,)
        ).fetchone()
        check("队列回填 reviewer + APPROVED",
              qrow["reviewed_by"] == ADMIN_EMAIL and qrow["review_status"] == "APPROVED",
              f"reviewed_by={qrow['reviewed_by']} review_status={qrow['review_status']}")
        ds = db.execute(
            "SELECT review_status FROM t_data_source WHERE source_url=?",
            ("https://b23.tv/e2e-experience-001",),
        ).fetchone()
        check("t_data_source 回填 APPROVED", ds is not None and ds["review_status"] == "APPROVED",
              f"review_status={ds['review_status'] if ds else None}")

        # 5. reject 第二条（kaoyan_news）
        q_id2 = queue_ids["kaoyan_news"]
        resp = client.post(
            f"{BASE}/api/admin/research-queue/{q_id2}/reject",
            json={"reject_reason": "E2E 验证：信息无来源佐证"},
            headers=headers,
        )
        body = resp.json()
        check("reject 200 + REJECTED", resp.status_code == 200 and body["review_status"] == "REJECTED",
              f"status={resp.status_code} review_status={body.get('review_status')}")
        ext2 = db.execute(
            "SELECT review_status FROM t_external_research_item WHERE id=?",
            (body["ref_item_id"],),
        ).fetchone()
        check("ext 回填 REJECTED", ext2["review_status"] == "REJECTED",
              f"review_status={ext2['review_status']}")
        qrow2 = db.execute(
            "SELECT review_status, reject_reason FROM t_review_queue_item WHERE id=?", (q_id2,)
        ).fetchone()
        check("队列回填 REJECTED + 原因",
              qrow2["review_status"] == "REJECTED" and qrow2["reject_reason"],
              f"review_status={qrow2['review_status']} reason={qrow2['reject_reason']}")
        check("reject 不落业务表", db.execute(
            "SELECT count(*) FROM kaoyan_news WHERE source_url=?",
            ("https://news.e2e.example.com/rss/2026-08-12",),
        ).fetchone()[0] == 0)

        # 6. duplicate 第三条（dark_knowledge）
        q_id3 = queue_ids["dark_knowledge"]
        resp = client.post(
            f"{BASE}/api/admin/research-queue/{q_id3}/duplicate",
            json={"duplicate_of": "https://e2e.example.com/original-post"},
            headers=headers,
        )
        body = resp.json()
        check("duplicate 200 + DUPLICATED", resp.status_code == 200 and body["review_status"] == "DUPLICATED",
              f"status={resp.status_code} review_status={body.get('review_status')}")
        ext3 = db.execute(
            "SELECT review_status FROM t_external_research_item WHERE id=?",
            (body["ref_item_id"],),
        ).fetchone()
        check("ext 回填 DUPLICATED", ext3["review_status"] == "DUPLICATED",
              f"review_status={ext3['review_status']}")

        # 7. 按状态过滤复查
        for status_name, expect in [("APPROVED", 1), ("REJECTED", 1), ("DUPLICATED", 1), ("PENDING", 0)]:
            resp = client.get(
                f"{BASE}/api/admin/research-queue/pending?review_status={status_name}", headers=headers
            )
            check(f"状态过滤 {status_name}={expect}", resp.json()["total"] == expect,
                  f"total={resp.json()['total']}")

    # 8. 清理 E2E 数据（仅删本脚本造的）
    for item in SEED_ITEMS:
        db.execute("DELETE FROM t_external_research_item WHERE source_url=?", (item["source_url"],))
        db.execute("DELETE FROM t_data_source WHERE source_url=?", (item["source_url"],))
    db.execute("DELETE FROM t_review_queue_item WHERE source_url LIKE '%e2e%'")
    db.execute("DELETE FROM experience_posts WHERE source_url LIKE '%e2e%'")
    db.execute("DELETE FROM kaoyan_news WHERE source_url LIKE '%e2e%'")
    db.execute("DELETE FROM dark_knowledge WHERE title LIKE '%E2E%'")
    db.commit()
    db.close()
    print(f"\n结果：{len(PASS)} 通过 / {len(FAIL)} 失败")
    if FAIL:
        print("失败项：", FAIL)
        return 1
    print("全部通过 ✅")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
