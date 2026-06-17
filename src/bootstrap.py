from __future__ import annotations

from pathlib import Path

# 全局服务单例
_app_service = None


def create_app(base_dir: Path):
    global _app_service

    try:
        from flask import Flask
    except ImportError as exc:
        raise RuntimeError(
            "Flask is not installed. Install dependencies from requirements.txt first."
        ) from exc

    from .config import AppConfig
    from .web import register_routes
    from .service import AppService

    config = AppConfig.from_base_dir(base_dir)
    app = Flask(
        __name__,
        template_folder=str(config.templates_dir),
        static_folder=str(config.static_dir),
    )
    app.config["APP_CONFIG"] = config

    # 预加载服务（单例模式，避免重复加载TTL）
    if _app_service is None:
        print("正在加载知识图谱数据...")
        _app_service = AppService(config)
        print("[OK] 知识图谱加载完成")

    app.config["APP_SERVICE"] = _app_service

    register_routes(app, config)
    return app
