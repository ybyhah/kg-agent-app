from __future__ import annotations

from pathlib import Path

from src.bootstrap import create_app


BASE_DIR = Path(__file__).resolve().parent
app = create_app(BASE_DIR)
