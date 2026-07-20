# -*- coding: utf-8 -*-
"""Verify weibo and bilibili data import."""
import sys
sys.path.insert(0, "/app")
from sqlalchemy import text
from app.database import engine

with engine.connect() as conn:
    r1 = conn.execute(text("SELECT COUNT(*) FROM knowledge_articles WHERE category = :cat"), {"cat": "weibo"})
    print("weibo:", r1.fetchone()[0])
    r2 = conn.execute(text("SELECT COUNT(*) FROM knowledge_articles WHERE category = :cat"), {"cat": "bilibili_video"})
    print("bilibili_video:", r2.fetchone()[0])
    r3 = conn.execute(text("SELECT COUNT(*) FROM knowledge_articles"))
    print("total:", r3.fetchone()[0])
