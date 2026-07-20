# backend/pipeline/cli.py
"""管道 CLI 入口"""
import asyncio

import click
from uuid import UUID

from app.database import SessionLocal
from pipeline.extractor import extract_report
from pipeline.fetcher import fetch_report
from pipeline.reviewer import publish_report, review_report


@click.group()
def cli():
    """GradPath 就业报告数据管道"""
    pass


@cli.command()
@click.option("--school", required=True, help="学校 slug（如 tsinghua）")
@click.option("--year", required=True, type=int, help="报告年份")
@click.option("--url", default=None, help="直接提供报告 URL（可选）")
def fetch(school: str, year: int, url: str | None):
    """抓取高校就业质量报告"""
    db = SessionLocal()
    try:
        report = fetch_report(db, school_slug=school, year=year, direct_url=url)
        if report is None:
            click.echo(f"学校 '{school}' 不存在")
        else:
            click.echo(f"报告已创建: id={report.id}, status={report.parse_status}")
    finally:
        db.close()


@cli.command()
@click.option("--report-id", required=True, help="ReportRecord UUID")
def extract(report_id: str):
    """LLM 解析报告"""
    db = SessionLocal()
    try:
        report = asyncio.run(extract_report(db, report_id=UUID(report_id)))
        if report is None:
            click.echo("报告不存在")
        else:
            click.echo(f"解析完成: status={report.parse_status}")
            if report.parse_error:
                click.echo(f"错误: {report.parse_error}")
    finally:
        db.close()


@cli.command()
@click.option("--report-id", required=True, help="ReportRecord UUID")
def review(report_id: str):
    """人工审核解析结果"""
    db = SessionLocal()
    try:
        review_report(db, report_id=UUID(report_id))
    finally:
        db.close()


@cli.command()
@click.option("--report-id", required=True, help="ReportRecord UUID")
def publish(report_id: str):
    """发布报告"""
    db = SessionLocal()
    try:
        publish_report(db, report_id=UUID(report_id))
    finally:
        db.close()


if __name__ == "__main__":
    cli()
