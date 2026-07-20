"""爬虫配置加载器 — 从YAML文件加载爬虫配置。"""
import os
from pathlib import Path
from typing import Any
import yaml

CONFIG_DIR = Path(__file__).parent / "config"

def load_config(name: str) -> dict:
    """加载指定爬虫的YAML配置文件。
    Args:
        name: 爬虫名称（对应config目录下的 name.yaml）
    Returns:
        配置字典，文件不存在则返回空字典
    """
    config_path = CONFIG_DIR / f"{name}.yaml"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}

def list_configs() -> list[dict]:
    """列出所有配置文件。"""
    configs = []
    if CONFIG_DIR.exists():
        for f in CONFIG_DIR.glob("*.yaml"):
            cfg = load_config(f.stem)
            cfg["_name"] = f.stem
            configs.append(cfg)
    return configs
