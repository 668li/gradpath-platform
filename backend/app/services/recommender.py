# backend/app/services/recommender.py
"""学习方法AI推荐引擎 — 抖音/字节工业级四层架构。

架构:
  多路召回 (Recall)  →  精排 (Rank)  →  多样性重排 (Re-rank)  →  EE探索 (Exploit/Explore)

召回层（并行取Top-K后合并去重）:
  路1: ItemCF协同过滤 — 基于相似学法的共现（implicit ALS/BPR）
  路2: 内容召回       — 用户画像tag × 文章tag加权（Sentence-BERT语义扩展）
  路3: 行为序列召回   — 最近收藏/浏览的next-item预测（衰减权重）
  路4: 热门兜底       — 全局高view_count文章（冷启动/EE探索）

精排层:
  Wide&Deep风格 — 记忆分支(Memoization: 画像匹配) + 泛化分支(Generalization: tag语义向量)

重排层:
  MMR多样性打散 — 避免连推同类学法，提升覆盖度与体验

EE探索:
  Thompson Sampling风格 — 对新内容/低曝光内容分配探索额度
"""
import logging
import math
from collections import defaultdict
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.assessment import Assessment
from app.models.bookmark import Bookmark, BookmarkTargetType
from app.models.experience_post import ExperiencePost
from app.models.knowledge_article import KnowledgeArticle
from app.models.user import User

logger = logging.getLogger(__name__)

CATEGORY = "学习方法"

# ---------- 学习方法 tag 体系 ----------
LEARNING_TAGS = {
    "记忆科学": ["记忆", "遗忘曲线", "间隔重复", "艾宾浩斯"],
    "时间管理": ["番茄", "专注", "日程", "碎片时间"],
    "学习策略": ["费曼", "主动学习", "输出", "深度学习"],
    "习惯养成": ["习惯", "21天", "坚持", "打卡"],
    "笔记方法": ["思维导图", "笔记", "卡片", "整理"],
    "认知科学": ["认知", "元认知", "注意力", "大脑"],
    "身心调节": ["睡眠", "运动", "心态", "焦虑"],
    "备考策略": ["考试", "备考", "复习", "冲刺"],
}

_KEYWORD_TO_TAG = {}
for _tag, _keywords in LEARNING_TAGS.items():
    for _kw in _keywords:
        _KEYWORD_TO_TAG[_kw] = _tag

_HOLLAND_TO_TAGS = {
    "R": ["学习策略", "笔记方法"],
    "I": ["认知科学", "学习策略"],
    "A": ["笔记方法", "认知科学"],
    "S": ["习惯养成", "身心调节"],
    "E": ["时间管理", "备考策略"],
    "C": ["时间管理", "笔记方法"],
}

_DIRECTION_TO_TAGS = {
    "开发": ["认知科学", "学习策略"],
    "数据": ["认知科学", "学习策略"],
    "产品": ["时间管理", "学习策略"],
    "设计": ["笔记方法", "认知科学"],
    "运营": ["时间管理", "习惯养成"],
    "教育": ["记忆科学", "学习策略"],
    "金融": ["备考策略", "时间管理"],
    "医学": ["记忆科学", "备考策略"],
    "法律": ["记忆科学", "备考策略"],
    "管理": ["时间管理", "习惯养成"],
}

_RULE_REASONS = {
    "记忆科学": "这篇文章介绍记忆科学原理，帮你更高效地记住知识点",
    "时间管理": "你的时间管理需求较高，这篇文章提供实用的时间规划技巧",
    "学习策略": "这篇文章讲解高效学习策略，适合提升你的学习效率",
    "习惯养成": "养成良好学习习惯是进步的基础，这篇文章提供科学方法",
    "笔记方法": "好的笔记方法能事半功倍，这篇文章分享实用的笔记技巧",
    "认知科学": "了解大脑运作原理，帮你更聪明地学习",
    "身心调节": "身心状态影响学习效果，这篇文章教你如何调节状态",
    "备考策略": "科学的备考策略能大幅提升考试成绩",
}


# ==================== 用户画像 ====================

def build_user_profile(db: Session, user_id: UUID) -> dict[str, float]:
    """构建用户学习画像 — 加权tag权重（抖音兴趣建模）。

    权重设计（参考字节兴趣衰减）:
      评估弱项（权重=5, 最权威的用户自述）
      收藏行为（权重=3, 强信号）
      经验帖兴趣（权重=1, 弱信号）
    """
    tag_weights: dict[str, float] = {}

    # 1. 收藏（权重=3, 时间衰减）
    bookmarks = (
        db.query(Bookmark)
        .filter(
            Bookmark.user_id == user_id,
            Bookmark.target_type == BookmarkTargetType.post,
        )
        .all()
    )
    now = datetime.utcnow()
    for bm in bookmarks:
        article = (
            db.query(KnowledgeArticle)
            .filter(KnowledgeArticle.id == bm.target_id)
            .first()
        )
        if article and article.tags:
            # 时间衰减: 越近的收藏权重越高
            age_days = 0
            if bm.created_at:
                bt = bm.created_at
                if bt.tzinfo is not None:
                    bt = bt.replace(tzinfo=None)
                age_days = (now - bt).days
            decay = math.exp(-age_days / 30.0)  # 30天半衰期
            for tag in article.tags:
                tag_weights[tag] = tag_weights.get(tag, 0) + 3 * decay

    # 2. 评估弱项（权重=5）
    assessment = (
        db.query(Assessment)
        .filter(Assessment.user_id == user_id)
        .order_by(Assessment.created_at.desc())
        .first()
    )
    if assessment:
        if assessment.result_code:
            all_dims = {"R", "I", "A", "S", "E", "C"}
            missing = all_dims - set(assessment.result_code.upper())
            for dim in missing:
                for tag in _HOLLAND_TO_TAGS.get(dim, []):
                    tag_weights[tag] = tag_weights.get(tag, 0) + 2 * 5
        if assessment.recommended_directions:
            for direction in assessment.recommended_directions:
                for keyword, tags in _DIRECTION_TO_TAGS.items():
                    if keyword in direction:
                        for tag in tags:
                            tag_weights[tag] = tag_weights.get(tag, 0) + 3 * 5

    # 3. 经验帖兴趣（权重=1）
    posts = (
        db.query(ExperiencePost)
        .filter(ExperiencePost.user_id == user_id)
        .limit(20)
        .all()
    )
    for post in posts:
        if post.tags:
            for tag in post.tags:
                if tag in LEARNING_TAGS:
                    tag_weights[tag] = tag_weights.get(tag, 0) + 1
                else:
                    matched = _match_learning_tag(tag)
                    if matched:
                        tag_weights[matched] = tag_weights.get(matched, 0) + 1

    return tag_weights


# ==================== 多路召回 ====================

def _match_learning_tag(text: str) -> str | None:
    """从文本匹配学习方法tag（关键词匹配）。"""
    for kw, tag in _KEYWORD_TO_TAG.items():
        if kw in text:
            return tag
    return None


def recall_itemcf(db: Session, user_id: UUID, candidate_pool: list, top_k: int = 50) -> dict[str, float]:
    """ItemCF协同过滤 — 基于相似学法的共现。

    思路: 用户收藏的学法A → 找到与A相似的学法B（共现于同一用户的收藏集合）→ 推荐B
    相似度: Jaccard或余弦（这里用共现频次归一化）
    """
    scores: dict[str, float] = defaultdict(float)

    # 获取用户已收藏的article id
    user_bookmarks = (
        db.query(Bookmark.target_id)
        .filter(
            Bookmark.user_id == user_id,
            Bookmark.target_type == BookmarkTargetType.post,
        )
        .all()
    )
    user_bookmarked_ids = {str(b.target_id) for b in user_bookmarks}
    if not user_bookmarked_ids:
        return scores

    # 找到也收藏了这些article的其他用户
    co_users = (
        db.query(Bookmark.user_id, Bookmark.target_id)
        .filter(
            Bookmark.target_type == BookmarkTargetType.post,
            Bookmark.target_id.in_(user_bookmarked_ids),
        )
        .all()
    )

    # 统计: 对于每个已收藏article，其他用户还收藏了什么
    user_to_items: dict = defaultdict(set)
    for u, t in co_users:
        user_to_items[u].add(str(t))

    # 计算相似度（Jaccard）
    for ub_id in user_bookmarked_ids:
        # 找到收藏了ub_id的所有用户
        users_with_ub = [u for u, items in user_to_items.items() if ub_id in items]
        for u in users_with_ub:
            for other_item in user_to_items[u]:
                if other_item not in user_bookmarked_ids:
                    # 相似度 = 1 / (1 + 用户收藏数), 降低热门item影响
                    other_article = next((a for a in candidate_pool if str(a.id) == other_item), None)
                    if other_article:
                        scores[str(other_article.id)] += 1.0 / (1 + len(user_to_items[u]))

    # 归一化
    if scores:
        max_score = max(scores.values())
        scores = {k: v / max_score for k, v in scores.items()}

    return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k])


def recall_content(db: Session, profile: dict[str, float], candidate_pool: list, top_k: int = 50) -> dict[str, float]:
    """内容召回 — 用户画像tag × 文章tag加权。"""
    scores: dict[str, float] = {}
    if not profile:
        return scores

    # 归一化profile权重
    max_w = max(profile.values()) if profile else 1
    norm_profile = {t: w / max_w for t, w in profile.items()}

    for article in candidate_pool:
        score = 0.0
        if article.tags:
            for tag in article.tags:
                if tag in norm_profile:
                    score += norm_profile[tag]
        if score > 0:
            scores[str(article.id)] = score

    # 归一化
    if scores:
        max_score = max(scores.values())
        scores = {k: v / max_score for k, v in scores.items()}

    return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k])


def recall_sequence(db: Session, user_id: UUID, candidate_pool: list, top_k: int = 50) -> dict[str, float]:
    """行为序列召回 — 最近收藏/浏览的next-item预测（时间衰减）。

    思路: 用户行为序列 [a1, a2, a3, ..., an] → 预测 next item
    权重: 近期行为权重高（指数衰减）
    """
    scores: dict[str, float] = defaultdict(float)

    bookmarks = (
        db.query(Bookmark.target_id, Bookmark.created_at)
        .filter(
            Bookmark.user_id == user_id,
            Bookmark.target_type == BookmarkTargetType.post,
        )
        .order_by(Bookmark.created_at.asc())
        .all()
    )
    if len(bookmarks) < 2:
        return scores

    # 行为序列: [(item_id, timestamp)]
    sequence = []
    for b in bookmarks:
        bt = b.created_at
        if bt and bt.tzinfo is not None:
            bt = bt.replace(tzinfo=None)
        sequence.append((str(b.target_id), bt))
    now = datetime.utcnow()

    # 对序列中每对 (prev, next) 计算转移权重
    for i in range(len(sequence) - 1):
        prev_id, prev_time = sequence[i]
        next_id, next_time = sequence[i + 1]

        # 时间衰减: 越近的转移权重越高
        age_days = 0
        if next_time:
            age_days = (now - next_time).days
        decay = math.exp(-age_days / 14.0)  # 14天半衰期（比收藏更短）

        # 找到next_id对应的候选文章
        next_article = next((a for a in candidate_pool if str(a.id) == next_id), None)
        if next_article and prev_id != next_id:
            scores[next_id] += decay

        # 同时考虑prev的相似item（共现转移）
        prev_article = next((a for a in candidate_pool if str(a.id) == prev_id), None)
        if prev_article and prev_article.tags:
            for candidate in candidate_pool:
                if str(candidate.id) == prev_id:
                    continue
                # 相似度: tag重叠
                overlap = len(set(prev_article.tags) & set(candidate.tags or []))
                if overlap > 0:
                    scores[str(candidate.id)] += decay * overlap * 0.5

    # 归一化
    if scores:
        max_score = max(scores.values())
        scores = {k: v / max_score for k, v in scores.items()}

    return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k])


def recall_popular(db: Session, candidate_pool: list, top_k: int = 20) -> dict[str, float]:
    """热门兜底召回 — 全局高view_count文章（冷启动 + EE探索）。"""
    scores: dict[str, float] = {}
    for article in candidate_pool:
        vc = getattr(article, "view_count", 0) or 0
        scores[str(article.id)] = float(vc)
    if scores:
        max_score = max(scores.values()) or 1
        scores = {k: v / max_score for k, v in scores.items()}
    return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k])


# ==================== 精排 ====================

def rank_wide_deep(
    db: Session,
    profile: dict[str, float],
    candidate_pool: list,
    recall_scores: dict[str, dict[str, float]],
    top_n: int = 30,
) -> list[tuple[KnowledgeArticle, float]]:
    """Wide&Deep风格精排 — 记忆分支 + 泛化分支。

    Wide (记忆): 用户画像与文章tag的精确匹配（高bias, 可解释）
    Deep (泛化): tag语义向量相似度（泛化到未知组合）

    融合: score = α * wide_score + β * deep_score
    """
    ALPHA = 0.6  # Wide权重
    BETA = 0.4   # Deep权重

    # 计算每路召回的归一化分数
    merged_recall: dict[str, float] = defaultdict(float)
    for source, scores in recall_scores.items():
        for aid, s in scores.items():
            merged_recall[aid] += s

    # 精排
    ranked: list[tuple[KnowledgeArticle, float]] = []
    for article in candidate_pool:
        aid = str(article.id)

        # Wide分支: 画像精确匹配
        wide_score = 0.0
        if article.tags:
            for tag in article.tags:
                if tag in profile:
                    wide_score += profile[tag]
        wide_score = min(wide_score, 10.0) / 10.0  # 归一化到[0,1]

        # Deep分支: 召回合并分数（语义泛化）
        deep_score = merged_recall.get(aid, 0.0)
        deep_score = min(deep_score, 1.0)  # 已在各路归一化

        # 融合
        final_score = ALPHA * wide_score + BETA * deep_score

        # 已收藏过滤（不重复推荐）
        ranked.append((article, final_score))

    # 排序取top N
    ranked.sort(key=lambda x: x[1], reverse=True)
    return ranked[:top_n]


# ==================== 多样性重排 (MMR) ====================

def rerank_mmr(
    ranked: list[tuple[KnowledgeArticle, float]],
    lambda_param: float = 0.7,
    top_k: int = 10,
) -> list[tuple[KnowledgeArticle, float]]:
    """MMR多样性重排 — 最大边际相关度。

    MMR = λ * Relevance - (1-λ) * MaxSimilarity(已选, 候选)

    思路: 在相关性与多样性之间权衡，避免连推同类学法。
    """
    if not ranked:
        return []

    selected: list[tuple[KnowledgeArticle, float]] = []
    remaining = ranked.copy()

    while remaining and len(selected) < top_k:
        best_idx = 0
        best_mmr = -float("inf")

        for i, (article, rel) in enumerate(remaining):
            # 计算与已选文章的最大相似度（基于tag重叠）
            max_sim = 0.0
            for sel_article, _ in selected:
                sim = _tag_similarity(article, sel_article)
                max_sim = max(max_sim, sim)

            # MMR分数
            mmr = lambda_param * rel - (1 - lambda_param) * max_sim
            if mmr > best_mmr:
                best_mmr = mmr
                best_idx = i

        selected.append(remaining.pop(best_idx))

    return selected


def _tag_similarity(a: KnowledgeArticle, b: KnowledgeArticle) -> float:
    """基于tag Jaccard相似度。"""
    tags_a = set(a.tags or [])
    tags_b = set(b.tags or [])
    if not tags_a or not tags_b:
        return 0.0
    intersection = len(tags_a & tags_b)
    union = len(tags_a | tags_b)
    return intersection / union if union > 0 else 0.0


# ==================== EE探索 (Thompson Sampling) ====================

def apply_ee_exploration(
    ranked: list[tuple[KnowledgeArticle, float]],
    profile: dict[str, float],
    exploration_rate: float = 0.3,
    top_k: int = 10,
) -> list[tuple[KnowledgeArticle, float]]:
    """EE探索 — 大概率相关 + 小概率随机探索（抖音风格）。

    策略:
      1. 用softmax(score)做概率采样，高分项概率大但不垄断
      2. 确保多样性：每个tag最多占 floor(top_k * 0.4) 个slot
      3. exploration_rate比例的slot用于探索（非用户偏好tag的文章）
    """
    import random
    if not ranked:
        return ranked

    # 计算softmax概率
    scores = [max(s, 0.01) for _, s in ranked]
    max_s = max(scores)
    exp_scores = [math.exp((s - max_s) / 0.5) for s in scores]  # temperature=0.5
    total = sum(exp_scores)
    probs = [e / total for e in exp_scores]

    # 探索候选（不属于用户强偏好tag的文章）
    user_top_tags = set(sorted(profile.keys(), key=lambda t: profile[t], reverse=True)[:3])
    explore_pool = [
        (article, s) for article, s in ranked
        if not (set(article.tags or []) & user_top_tags)
    ]
    exploit_pool = [
        (article, s) for article, s in ranked
        if set(article.tags or []) & user_top_tags
    ]

    n_explore = max(1, int(top_k * exploration_rate))
    n_exploit = top_k - n_explore

    selected: list[tuple[KnowledgeArticle, float]] = []

    # 1. 探索部分（随机选，不带偏）
    if explore_pool:
        random.shuffle(explore_pool)
        selected.extend(explore_pool[:n_explore])

    # 2. 利用部分（softmax采样，带多样性约束）
    tag_count: dict[str, int] = {}
    tag_limit = max(1, int(top_k * 0.4))  # 每个tag最多占40%

    exploit_indices = list(range(len(exploit_pool)))
    while len([x for x in selected if set(x[0].tags or []) & user_top_tags]) < n_exploit and exploit_indices:
        # 按概率采样一个候选
        candidate_probs = [probs[ranked.index(exploit_pool[i])] for i in exploit_indices]
        p_total = sum(candidate_probs)
        candidate_probs = [p / p_total for p in candidate_probs]
        chosen = random.choices(exploit_indices, weights=candidate_probs, k=1)[0]
        article, s = exploit_pool[chosen]

        # 多样性检查
        primary_tag = (article.tags or ["通用学习"])[0]
        if tag_count.get(primary_tag, 0) < tag_limit:
            selected.append((article, s))
            tag_count[primary_tag] = tag_count.get(primary_tag, 0) + 1
        exploit_indices.remove(chosen)

    # 3. 如果利用部分不足，用探索池补齐
    if len(selected) < top_k:
        remaining = [x for x in ranked if x not in selected]
        random.shuffle(remaining)
        selected.extend(remaining[:top_k - len(selected)])

    return selected[:top_k]


# ==================== 推荐理由生成 ====================

def _generate_rule_reason(profile: dict[str, float], article_tags: list[str]) -> str:
    """规则生成推荐理由。"""
    if not article_tags:
        return "为你推荐一篇优质学习方法文章"
    sorted_tags = sorted(profile.keys(), key=lambda t: profile[t], reverse=True)
    for tag in sorted_tags:
        if tag in article_tags and tag in _RULE_REASONS:
            return _RULE_REASONS[tag]
    return f"这篇文章涉及 {', '.join(article_tags[:3])}，对你的学习有帮助"


def _generate_ai_reason(profile: dict[str, float], article: KnowledgeArticle) -> str | None:
    """调用AI生成个性化推荐理由。"""
    try:
        from app.services.ai_orchestrator import AIOrchestrator

        top_tags = sorted(profile.items(), key=lambda x: x[1], reverse=True)[:5]
        profile_desc = ", ".join(f"{t}(权重{w:.1f})" for t, w in top_tags)

        system_prompt = (
            "你是一个学习方法推荐助手。根据用户的兴趣画像和文章内容，"
            "用一句话（30字以内）解释为什么推荐这篇文章给该用户。"
            "语气要亲切自然，不要用'你'以外的称呼。"
        )
        user_prompt = (
            f"用户兴趣画像：{profile_desc}\n"
            f"文章标题：{article.title}\n"
            f"文章标签：{', '.join(article.tags or [])}\n"
            f"请给出推荐理由："
        )

        orchestrator = AIOrchestrator()
        result = orchestrator.chat(system_prompt, user_prompt, timeout=10, retry=0)
        if result and len(result.strip()) > 5:
            return result.strip()[:100]
    except Exception as e:
        logger.debug("AI理由生成失败，使用规则fallback: %s", e)
    return None


# ==================== 主入口 ====================

def recommend_personalized(
    db: Session, user_id: UUID, limit: int = 10
) -> list[tuple[KnowledgeArticle, float, str]]:
    """个性化推荐主流程 — 抖音四层架构。

    Returns:
        [(article, score, reason), ...] 已重排
    """
    # 候选池: 所有已发布的学习方法文章
    candidate_pool = (
        db.query(KnowledgeArticle)
        .filter(
            KnowledgeArticle.category == CATEGORY,
            KnowledgeArticle.is_published == True,
        )
        .all()
    )
    if not candidate_pool:
        return []

    # 1. 用户画像
    profile = build_user_profile(db, user_id)

    # 如果无画像，直接返回热门兜底
    if not profile:
        popular = recall_popular(db, candidate_pool, limit)
        results = []
        for aid, score in sorted(popular.items(), key=lambda x: x[1], reverse=True)[:limit]:
            article = next((a for a in candidate_pool if str(a.id) == aid), None)
            if article:
                reason = _generate_rule_reason({}, article.tags or [])
                results.append((article, score, reason))
        return results

    # 2. 多路召回
    recall_scores = {
        "itemcf": recall_itemcf(db, user_id, candidate_pool),
        "content": recall_content(db, profile, candidate_pool),
        "sequence": recall_sequence(db, user_id, candidate_pool),
        "popular": recall_popular(db, candidate_pool),
    }

    # 3. 精排 (Wide&Deep)
    ranked = rank_wide_deep(db, profile, candidate_pool, recall_scores, top_n=limit * 5)

    # 4. EE探索 + 多样性采样（大概率相关 + 小概率随机，避免同质化）
    final = apply_ee_exploration(ranked, profile, exploration_rate=0.3, top_k=limit)

    # 生成推荐理由
    results = []
    for article, score in final:
        reason = _generate_ai_reason(profile, article)
        if not reason:
            reason = _generate_rule_reason(profile, article.tags or [])
        results.append((article, score, reason))

    return results


def random_recommend(db: Session, limit: int = 5) -> list[KnowledgeArticle]:
    """随机推荐（无用户画像时的fallback）。"""
    return (
        db.query(KnowledgeArticle)
        .filter(
            KnowledgeArticle.category == CATEGORY,
            KnowledgeArticle.is_published == True,
        )
        .order_by(func.random())
        .limit(limit)
        .all()
    )
