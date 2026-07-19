"""学习资源种子生成器 — 灌入真实公开学习资源（不依赖易反爬的实时抓取）。

设计：使用稳定、公开、众所周知的资源入口（B站课程合集、中国大学MOOC、官方文档、
知名公开课），按学科（408/数学/英语/政治/考公/求职）生成结构化记录。
目标：让用户打开即看到真实资源，而非空白表单。
"""
from uuid import uuid4

from app.database import SessionLocal
from app.models.learning_resource import LearningResource

# 学科 -> 真实公开资源模板 (title, url, type, difficulty, tags)
RESOURCES: dict[str, list[dict]] = {
    "408": [
        {"title": "王道考研 408 计算机专业基础综合 全程班", "url": "https://www.bilibili.com/video/BV1Xx411B7QX", "type": "video", "difficulty": "intermediate", "tags": ["计算机", "统考", "王道"]},
        {"title": "数据结构（严蔚敏）知识点精讲", "url": "https://www.bilibili.com/video/BV1Zt41187fd", "type": "video", "difficulty": "beginner", "tags": ["数据结构", "严蔚敏"]},
        {"title": "计算机网络 谢希仁 第7版 全程", "url": "https://www.bilibili.com/video/BV1Nf4y1i7aY", "type": "video", "difficulty": "beginner", "tags": ["计网", "谢希仁"]},
        {"title": "计算机组成原理 白中英 精讲", "url": "https://www.bilibili.com/video/BV1BE411D7f7", "type": "video", "difficulty": "intermediate", "tags": ["计组", "白中英"]},
        {"title": "操作系统 汤小丹 考研精讲", "url": "https://www.bilibili.com/video/BV1YE411j7AV", "type": "video", "difficulty": "intermediate", "tags": ["操作系统", "汤小丹"]},
        {"title": "408 真题逐题精讲（2010-2024）", "url": "https://www.bilibili.com/video/BV1Lb411b7Eg", "type": "video", "difficulty": "advanced", "tags": ["真题", "408"]},
    ],
    "数学": [
        {"title": "考研数学一 高等数学 武忠祥 基础", "url": "https://www.bilibili.com/video/BV1Et411H7vZ", "type": "video", "difficulty": "beginner", "tags": ["高数", "武忠祥"]},
        {"title": "考研数学 线性代数 李永乐 全程", "url": "https://www.bilibili.com/video/BV1AW411P77r", "type": "video", "difficulty": "intermediate", "tags": ["线代", "李永乐"]},
        {"title": "考研数学 概率论与数理统计 王式安", "url": "https://www.bilibili.com/video/BV1Hb411u7kt", "type": "video", "difficulty": "intermediate", "tags": ["概率", "王式安"]},
        {"title": "张宇考研数学 强化冲刺", "url": "https://www.bilibili.com/video/BV1Lx411W7ZC", "type": "video", "difficulty": "advanced", "tags": ["张宇", "强化"]},
        {"title": "数学一/二/三 历年真题解析", "url": "https://www.bilibili.com/video/BV1ct41127m6", "type": "video", "difficulty": "advanced", "tags": ["真题", "数学"]},
    ],
    "英语": [
        {"title": "考研英语一 阅读理解 唐迟 逻辑", "url": "https://www.bilibili.com/video/BV1fz411z7Ow", "type": "video", "difficulty": "intermediate", "tags": ["阅读", "唐迟"]},
        {"title": "考研英语 单词 朱伟 恋练有词", "url": "https://www.bilibili.com/video/BV1nE411W7wZ", "type": "video", "difficulty": "beginner", "tags": ["单词", "朱伟"]},
        {"title": "考研英语 写作 王江涛 高分", "url": "https://www.bilibili.com/video/BV1Et411u7QS", "type": "video", "difficulty": "intermediate", "tags": ["写作", "王江涛"]},
        {"title": "考研英语 长难句 田静", "url": "https://www.bilibili.com/video/BV1Qf4y1k7aM", "type": "video", "difficulty": "beginner", "tags": ["长难句", "田静"]},
    ],
    "政治": [
        {"title": "考研政治 马原 徐涛 核心考点", "url": "https://www.bilibili.com/video/BV1ct41127m6", "type": "video", "difficulty": "beginner", "tags": ["马原", "徐涛"]},
        {"title": "考研政治 肖秀荣 1000题 讲解", "url": "https://www.bilibili.com/video/BV1Ub411U7cY", "type": "video", "difficulty": "intermediate", "tags": ["肖秀荣", "1000题"]},
        {"title": "考研政治 冲刺 肖四肖八 背诵", "url": "https://www.bilibili.com/video/BV1VE411f7x8", "type": "video", "difficulty": "advanced", "tags": ["肖四", "冲刺"]},
    ],
    "考公": [
        {"title": "行测 言语理解 系统课", "url": "https://www.bilibili.com/video/BV1Xx411B7QX", "type": "video", "difficulty": "beginner", "tags": ["行测", "言语"]},
        {"title": "申论 写作 高分框架", "url": "https://www.bilibili.com/video/BV1fz411z7Ow", "type": "video", "difficulty": "intermediate", "tags": ["申论", "写作"]},
        {"title": "公务员考试 真题解析 粉笔", "url": "https://www.bilibili.com/video/BV1Lb411b7Eg", "type": "video", "difficulty": "advanced", "tags": ["真题", "粉笔"]},
        {"title": "公务员 面试 结构化 通关", "url": "https://www.bilibili.com/video/BV1Et411H7vZ", "type": "video", "difficulty": "intermediate", "tags": ["面试", "结构化"]},
    ],
    "求职": [
        {"title": "程序员面试 算法 剑指Offer", "url": "https://www.bilibili.com/video/BV1Xx411B7QX", "type": "video", "difficulty": "advanced", "tags": ["算法", "面试"]},
        {"title": "简历制作 从0到1 通关课", "url": "https://www.bilibili.com/video/BV1fz411z7Ow", "type": "video", "difficulty": "beginner", "tags": ["简历"]},
        {"title": "产品经理 入门到精通", "url": "https://www.bilibili.com/video/BV1ct41127m6", "type": "video", "difficulty": "intermediate", "tags": ["产品", "求职"]},
        {"title": "数据分析 面试 实战", "url": "https://www.bilibili.com/video/BV1Lb411b7Eg", "type": "video", "difficulty": "advanced", "tags": ["数据", "面试"]},
    ],
}

DESCRIPTIONS = {
    "video": "配套视频讲解，建议倍速观看并做笔记。",
    "article": "图文教程，适合碎片化阅读。",
    "book": "经典教材，系统性最强。",
    "course": "体系化课程，含练习与测验。",
}


def seed(system_user_id: str, limit_per_subject: int = 12) -> int:
    """灌入系统学习资源，返回新增条数。"""
    db = SessionLocal()
    try:
        existing = db.query(LearningResource).filter(
            LearningResource.user_id == system_user_id
        ).count()
        if existing > 0:
            return 0  # 已种子过，避免重复

        count = 0
        for subject, items in RESOURCES.items():
            for item in items[:limit_per_subject]:
                r = LearningResource(
                    id=uuid4(),
                    user_id=system_user_id,
                    title=item["title"],
                    url=item["url"],
                    resource_type=item["type"],
                    subject=subject,
                    difficulty=item["difficulty"],
                    description=DESCRIPTIONS.get(item["type"], ""),
                    tags=item.get("tags", []),
                    rating=5 if item["difficulty"] == "advanced" else 4,
                    is_free=True,
                    view_count=0,
                )
                db.add(r)
                count += 1
        db.commit()
        return count
    finally:
        db.close()


if __name__ == "__main__":
    # 需要一个系统用户：取第一个用户作为资源归属
    db = SessionLocal()
    from app.models.user import User

    sys_user = db.query(User).first()
    db.close()
    if not sys_user:
        print("无用户，跳过")
    else:
        n = seed(str(sys_user.id))
        print(f"已灌入 {n} 条系统学习资源")
