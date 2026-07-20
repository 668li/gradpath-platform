"""数据向量化脚本 — 将数据库中的文本数据转换为 Embedding 并存入 pgvector。

使用方法:
    docker exec gradpath-backend-1 python scripts/vectorize_data.py

功能:
    1. 导出各表的文本数据
    2. 文本分块
    3. 生成 Embedding
    4. 存入 document_embeddings 表
"""
import json
import logging
import sys
import time
from typing import Any

import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    DarkKnowledge,
    ExperiencePost,
    GradAdjustmentInfo,
    GradSchoolIntel,
    GradScorelineRecord,
    GradYanzhaoProgram,
    KnowledgeArticle,
    QA,
    QAAnswer,
    SalaryBenchmark,
    School,
)
from app.models.embedding_model import DocumentEmbedding

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Embedding 模型（延迟加载）
_model = None


def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("BAAI/bge-large-zh-v1.5")
        logger.info("Embedding 模型加载完成")
    return _model


def chunk_text(text_content: str, max_length: int = 500, overlap: int = 50) -> list[str]:
    """将长文本分块。"""
    if not text_content or len(text_content) <= max_length:
        return [text_content] if text_content else []

    chunks = []
    start = 0
    while start < len(text_content):
        end = start + max_length
        chunk = text_content[start:end]

        # 尝试在句号处断开
        if end < len(text_content):
            last_period = chunk.rfind("。")
            if last_period > max_length * 0.5:
                chunk = chunk[: last_period + 1]
                end = start + last_period + 1

        chunks.append(chunk.strip())
        start = end - overlap

    return chunks


def save_embedding(
    db: Session,
    source_table: str,
    source_id,
    content: str,
    embedding: list[float],
    doc_metadata: dict,
    chunk_index: int = 0,
):
    """保存单条 Embedding。"""
    embedding_str = str(embedding)

    record = DocumentEmbedding(
        source_table=source_table,
        source_id=source_id,
        chunk_index=chunk_index,
        content=content,
        doc_metadata=doc_metadata,
        embedding_vector=embedding_str,
    )
    db.add(record)


def vectorize_qa(db: Session, model) -> int:
    """向量化 QA + QAAnswer 数据。"""
    logger.info("开始向量化 QA 数据...")
    count = 0

    # 联表查询
    results = (
        db.query(QA, QAAnswer)
        .join(QAAnswer, QA.id == QAAnswer.qa_id)
        .filter(QA.status == "approved")
        .all()
    )

    batch_embeddings = []
    batch_contents = []
    batch_ids = []

    for qa, answer in results:
        content = f"问题: {qa.title}\n{qa.content}\n回答: {answer.content}"
        if len(content) > 2000:
            content = content[:2000]

        batch_contents.append(content)
        batch_ids.append((qa.id, "qa"))

    # 批量生成 Embedding
    if batch_contents:
        embeddings = model.encode(batch_contents, normalize_embeddings=True, show_progress_bar=True)
        for i, (embedding, content) in enumerate(zip(embeddings, batch_contents)):
            qa_id, source = batch_ids[i]
            save_embedding(
                db, source, qa_id, content, embedding.tolist(),
                {"tags": [], "type": "qa"}, 0
            )
            count += 1

    logger.info("QA 数据向量化完成: %d 条", count)
    return count


def vectorize_intel(db: Session, model) -> int:
    """向量化 GradSchoolIntel 数据。"""
    logger.info("开始向量化院校情报数据...")
    count = 0

    records = db.query(GradSchoolIntel).all()
    batch_contents = []
    batch_ids = []

    for record in records:
        content = f"""
院校: {record.school_name}
专业: {record.major_name}
年份: {record.year}
院校层次: {record.school_tier}
卡第一学历: {record.background_discrimination}
保护第一志愿: {record.first_choice_protection}
报录比: {record.admission_ratio or '未知'}
推免占比: {record.push_ratio or '未知'}
实际统考名额: {record.actual_quota or '未知'}
复试分数线: {record.score_line or '未知'}
复试占比: {record.retest_weight or '未知'}
复试形式: {record.retest_format or '未知'}
压分现象: {record.score_suppression}
调剂友好度: {record.transfer_friendly}
内部消息: {record.insider_notes or '无'}
""".strip()

        batch_contents.append(content)
        batch_ids.append(record.id)

    if batch_contents:
        embeddings = model.encode(batch_contents, normalize_embeddings=True, show_progress_bar=True)
        for i, (embedding, content) in enumerate(zip(embeddings, batch_contents)):
            record_id = batch_ids[i]
            record = records[i]
            save_embedding(
                db, "grad_school_intel", record_id, content, embedding.tolist(),
                {
                    "school_name": record.school_name,
                    "major_name": record.major_name,
                    "year": record.year,
                    "type": "intel",
                }, 0
            )
            count += 1

    logger.info("院校情报向量化完成: %d 条", count)
    return count


def vectorize_knowledge(db: Session, model) -> int:
    """向量化 KnowledgeArticle 数据。"""
    logger.info("开始向量化知识文章...")
    count = 0

    records = db.query(KnowledgeArticle).all()

    for record in records:
        chunks = chunk_text(record.content or record.title, max_length=500)
        for i, chunk in enumerate(chunks):
            if not chunk.strip():
                continue
            embedding = model.encode(chunk, normalize_embeddings=True)
            save_embedding(
                db, "knowledge_article", record.id, chunk, embedding.tolist(),
                {"title": record.title, "chunk_index": i, "type": "knowledge"}, i
            )
            count += 1

    logger.info("知识文章向量化完成: %d 条", count)
    return count


def vectorize_experience(db: Session, model) -> int:
    """向量化 ExperiencePost 数据。"""
    logger.info("开始向量化经验帖...")
    count = 0

    records = db.query(ExperiencePost).all()

    for record in records:
        content = f"标题: {record.title}\n{record.content or ''}"
        chunks = chunk_text(content, max_length=500)
        for i, chunk in enumerate(chunks):
            if not chunk.strip():
                continue
            embedding = model.encode(chunk, normalize_embeddings=True)
            save_embedding(
                db, "experience_post", record.id, chunk, embedding.tolist(),
                {"title": record.title, "chunk_index": i, "type": "experience"}, i
            )
            count += 1

    logger.info("经验帖向量化完成: %d 条", count)
    return count


def vectorize_dark_knowledge(db: Session, model) -> int:
    """向量化 DarkKnowledge 数据。"""
    logger.info("开始向量化暗知识...")
    count = 0

    records = db.query(DarkKnowledge).all()
    batch_contents = []
    batch_ids = []

    for record in records:
        content = f"""
阶段: {record.stage}
类别: {record.category}
标题: {record.title}
内容: {record.content}
重要性: {record.importance}
常见误区: {record.common_misconception or '无'}
行动建议: {record.actionable_advice or '无'}
验证方法: {record.verification_method or '无'}
""".strip()

        batch_contents.append(content)
        batch_ids.append(record.id)

    if batch_contents:
        embeddings = model.encode(batch_contents, normalize_embeddings=True, show_progress_bar=True)
        for i, (embedding, content) in enumerate(zip(embeddings, batch_contents)):
            record_id = batch_ids[i]
            record = records[i]
            save_embedding(
                db, "dark_knowledge", record_id, content, embedding.tolist(),
                {
                    "stage": record.stage,
                    "category": record.category,
                    "type": "dark_knowledge",
                }, 0
            )
            count += 1

    logger.info("暗知识向量化完成: %d 条", count)
    return count


def vectorize_scorelines(db: Session, model) -> int:
    """向量化 GradScorelineRecord 数据。"""
    logger.info("开始向量化分数线数据...")
    count = 0

    records = db.query(GradScorelineRecord).all()
    batch_contents = []
    batch_ids = []

    for record in records:
        content = f"""
院校: {record.university_name}
专业: {record.major_name}
年份: {record.year}
学位类型: {record.degree_type or '未知'}
总分线: {record.total_score_line or '未知'}
政治: {record.politics_score or '未知'}
英语: {record.foreign_language_score or '未知'}
业务课一: {record.business_1_score or '未知'}
业务课二: {record.business_2_score or '未知'}
招生人数: {record.enrollment_count or '未知'}
报考人数: {record.application_count or '未知'}
调剂人数: {record.adjustment_count or '未知'}
""".strip()

        batch_contents.append(content)
        batch_ids.append(record.id)

    if batch_contents:
        embeddings = model.encode(batch_contents, normalize_embeddings=True, show_progress_bar=True)
        for i, (embedding, content) in enumerate(zip(embeddings, batch_contents)):
            record_id = batch_ids[i]
            record = records[i]
            save_embedding(
                db, "scoreline", record_id, content, embedding.tolist(),
                {
                    "university_name": record.university_name,
                    "major_name": record.major_name,
                    "year": record.year,
                    "type": "scoreline",
                }, 0
            )
            count += 1

    logger.info("分数线数据向量化完成: %d 条", count)
    return count


def vectorize_salary(db: Session, model) -> int:
    """向量化 SalaryBenchmark 数据。"""
    logger.info("开始向量化薪资数据...")
    count = 0

    records = db.query(SalaryBenchmark).all()
    batch_contents = []
    batch_ids = []

    for record in records:
        content = f"""
公司: {record.company}
岗位: {record.position}
城市: {record.city or '未知'}
经验等级: {record.experience_level}
薪资范围: {record.salary_min}-{record.salary_max} (中位数: {record.salary_median})
来源: {record.source}
年份: {record.year}
""".strip()

        batch_contents.append(content)
        batch_ids.append(record.id)

    if batch_contents:
        embeddings = model.encode(batch_contents, normalize_embeddings=True, show_progress_bar=True)
        for i, (embedding, content) in enumerate(zip(embeddings, batch_contents)):
            record_id = batch_ids[i]
            record = records[i]
            save_embedding(
                db, "salary_benchmark", record_id, content, embedding.tolist(),
                {
                    "company": record.company,
                    "position": record.position,
                    "city": record.city,
                    "type": "salary",
                }, 0
            )
            count += 1

    logger.info("薪资数据向量化完成: %d 条", count)
    return count


def main():
    """主函数 — 执行全量向量化。"""
    logger.info("=== 开始数据向量化 ===")
    start_time = time.time()

    db = SessionLocal()
    model = get_model()

    # 清空现有向量（可选）
    if "--clear" in sys.argv:
        logger.info("清空现有向量数据...")
        db.execute(text("DELETE FROM document_embeddings"))
        db.commit()

    # 执行向量化
    total = 0
    total += vectorize_qa(db, model)
    db.commit()

    total += vectorize_intel(db, model)
    db.commit()

    total += vectorize_knowledge(db, model)
    db.commit()

    total += vectorize_experience(db, model)
    db.commit()

    total += vectorize_dark_knowledge(db, model)
    db.commit()

    total += vectorize_scorelines(db, model)
    db.commit()

    total += vectorize_salary(db, model)
    db.commit()

    elapsed = time.time() - start_time
    logger.info("=== 向量化完成 ===")
    logger.info("总计: %d 条向量", total)
    logger.info("耗时: %.1f 秒", elapsed)

    db.close()


if __name__ == "__main__":
    main()
