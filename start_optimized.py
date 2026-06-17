#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""优化的服务器启动脚本 - 预加载图谱数据"""

import os
import sys
from pathlib import Path

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

    # 预加载图谱数据（这样只加载一次）
    print("正在预加载知识图谱数据...")
    with app.app_context():
        from src.service import AppService
        from src.config import AppConfig

        config = app.config["APP_CONFIG"]
        service = AppService(config)

        # 测试查询确认加载成功
        test_result = service.tools.get_person_labels("文彭")
        print(f"✓ 知识图谱加载完成，找到 {len(test_result.rows)} 条测试结果")

    print(f"✓ 服务器启动 http://127.0.0.1:{port}")
    print("按 Ctrl+C 停止服务器")
    print("=" * 60)

    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
