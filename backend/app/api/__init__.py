"""自动发现并注册 app.api 下所有 APIRouter。

替换 main.py 中 50+ 行手动 import + include_router，
新增 API 端点只需在 app/api/ 创建带 router 的 .py 文件即可自动注册。
"""
import importlib
import logging
import pkgutil
from pathlib import Path

from fastapi import FastAPI

logger = logging.getLogger("gradpath.api_discovery")

# 跳过不需要自动注册的模块
_SKIP_MODULES = frozenset({"__init__"})


def auto_discover_routers(app: FastAPI) -> None:
    """扫描 app.api 包下所有含 router 的模块并注册。"""
    api_dir = Path(__file__).parent
    registered = 0

    for finder, module_name, is_pkg in pkgutil.iter_modules([str(api_dir)]):
        if module_name in _SKIP_MODULES:
            continue
        try:
            module = importlib.import_module(f"app.api.{module_name}")
            router = getattr(module, "router", None)
            if router is not None:
                app.include_router(router)
                registered += 1
        except Exception as exc:
            logger.warning("跳过 app.api.%s: %s", module_name, exc)

    # 扫描子包 (如 app.api.admin)
    for sub_dir in api_dir.iterdir():
        if sub_dir.is_dir() and sub_dir.name != "__pycache__":
            pkg_name = sub_dir.name
            try:
                pkg = importlib.import_module(f"app.api.{pkg_name}")
                for finder2, sub_name, _ in pkgutil.iter_modules([str(sub_dir)]):
                    if sub_name in _SKIP_MODULES:
                        continue
                    try:
                        sub_mod = importlib.import_module(f"app.api.{pkg_name}.{sub_name}")
                        router = getattr(sub_mod, "router", None)
                        if router is not None:
                            app.include_router(router)
                            registered += 1
                    except Exception as exc:
                        logger.warning("跳过 app.api.%s.%s: %s", pkg_name, sub_name, exc)
            except Exception as exc:
                logger.warning("跳过子包 app.api.%s: %s", pkg_name, exc)

    logger.info("已自动注册 %d 个 API 路由模块", registered)
