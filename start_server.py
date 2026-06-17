#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""启动服务器的辅助脚本"""

import os
import sys
from pathlib import Path

# 确保使用UTF-8编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

if __name__ == "__main__":
    from wsgi import app

    port = int(os.environ.get("PORT", "5000"))

    print("=" * 60)
    print("印人传知识图谱智能体")
    print("=" * 60)
    print(f"启动服务器 http://127.0.0.1:{port}")
    print("按 Ctrl+C 停止服务器")
    print("=" * 60)

    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)
