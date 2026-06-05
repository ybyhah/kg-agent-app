from __future__ import annotations

import os
from pathlib import Path

from src.bootstrap import create_app


BASE_DIR = Path(__file__).resolve().parent
app = create_app(BASE_DIR)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
