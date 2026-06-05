# Replit 部署说明

## 当前结构为什么适合 Replit

- 本地/工作区启动脚本为 `run_replit.py`
- 部署入口为 `wsgi:app`
- 启动时自动读取 `PORT`
- 服务监听 `0.0.0.0`
- 依赖集中写在 `requirements.txt`
- 页面资源使用 Flask 的 `templates/` 和 `static/` 目录

## 部署前需要准备

1. 安装依赖
2. 把 `schema.ttl`、`core.ttl`、`aligned.ttl` 放进 `data/kg/`
3. 如果后续接入大模型，再把 API Key 配成 Replit Secrets

## 在 Replit 上建议怎么做

1. 把整个 `kg_agent_app` 目录作为项目根目录
2. 确认 `run` 命令是 `python run_replit.py`
3. 先在 Workspace 内跑通
4. 再发布为可访问的 Web 应用

## 演示兜底建议

- 线上部署一份 Replit 版本
- 本地电脑保留一份可直接运行的 Flask 版本
- 不要把现场演示完全压在联网 API 上
