from __future__ import annotations

from pathlib import Path


def create_app(base_dir: Path):
    try:
        from flask import Flask
    except ImportError as exc:
        raise RuntimeError(
            "Flask is not installed. Install dependencies from requirements.txt first."
        ) from exc

    from .config import AppConfig
    from .web import register_routes

    config = AppConfig.from_base_dir(base_dir)
    app = Flask(
        __name__,
        template_folder=str(config.templates_dir),
        static_folder=str(config.static_dir),
    )
    app.config["APP_CONFIG"] = config
    register_routes(app, config)
    return app
