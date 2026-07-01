"""讨论帖种子数据。"""
import uuid

from sqlalchemy.orm import Session

from app.models.post import Post, PostTopicType
from app.models.user import User


SEED_TOPICS = [
    ("清华大学|计算机科学与技术", "school_major", 5, 5),
    ("腾讯|后端开发", "company_position", 3, 2),
    ("字节跳动|算法工程师", "company_position", 0, 0),
]

SEED_CONTENTS = {
    "清华大学|计算机科学与技术": {
        "posts": [
            "请问这个专业去字节的多吗？",
            "今年秋招感觉怎么样，大家拿到的 offer 都是什么方向？",
            "想了解一下保研和就业的比例，有学长学姐分享一下吗？",
            "听说今年互联网寒冬，计算机专业还值得读吗？",
            "有没有去国企的同学，待遇和发展怎么样？",
        ],
        "replies": [
            "挺多的，今年去了好几个",
            "今年确实比往年难一些，但头部公司还是有机会的",
            "保研率大概 30% 左右，每年有波动",
            "寒冬是暂时的，长期来看还是不错的",
            "国企待遇一般但稳定，看个人选择",
        ],
    },
    "腾讯|后端开发": {
        "posts": [
            "腾讯后端面试主要考什么？算法多还是系统设计多？",
            "PCG 和 CSIG 的后端开发哪个更好？",
            "面试后多久能收到结果通知？",
        ],
        "replies": [
            "算法和系统设计都有，看部门",
            "各有优劣，看个人发展偏好",
        ],
    },
}


def seed_posts(db: Session) -> None:
    """插入讨论帖种子数据。"""
    # 获取或创建一个种子用户
    seed_user = db.query(User).filter(User.email == "demo@gradpath.com").first()
    if not seed_user:
        seed_user = User(
            email="demo@gradpath.com",
            password_hash="$2b$12$dummyhashforseeduseronly",
            name="社区达人",
        )
        db.add(seed_user)
        db.flush()

    second_user = db.query(User).filter(User.email == "demo2@gradpath.com").first()
    if not second_user:
        second_user = User(
            email="demo2@gradpath.com",
            password_hash="$2b$12$dummyhashforseeduseronly2",
            name="热心校友",
        )
        db.add(second_user)
        db.flush()

    for topic_key, topic_type_str, post_count, reply_count in SEED_TOPICS:
        if post_count == 0:
            continue
        topic_type = PostTopicType(topic_type_str)
        contents = SEED_CONTENTS[topic_key]
        users = [seed_user, second_user]

        for i in range(post_count):
            post = Post(
                topic_type=topic_type,
                topic_key=topic_key,
                content=contents["posts"][i],
                user_id=users[i % 2].id,
                parent_id=None,
            )
            db.add(post)
            db.flush()

            if i < reply_count:
                reply = Post(
                    topic_type=topic_type,
                    topic_key=topic_key,
                    content=contents["replies"][i],
                    user_id=users[(i + 1) % 2].id,
                    parent_id=post.id,
                )
                db.add(reply)

    db.commit()
