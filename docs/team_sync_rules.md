# 团队同步与 Git 协作规定

更新时间：2026-06-17

目标：四个人同时工作时，保证大家都基于最新代码和同一份数据，不再出现“我本地能跑、别人拉下来不能跑”的情况。

## 仓库唯一入口

所有人只使用这个项目根目录：

```powershell
D:\cxdownload\kg agent\kg_agent_app
```

不要再使用外层旧目录、个人复制目录或压缩包目录。所有代码、数据、文档都以 Git 仓库中的版本为准。

## 分支规则

队长维护：

- `main`：稳定版本，只放已经验证过的代码。
- `develop`：四人集成分支。如果仓库暂时没有 `develop`，先由队长创建。

成员分支命名：

- 成员 A：`feature/data-kg-fix`
- 成员 B：`bugfix/backend-api-fix`
- 成员 C：`bugfix/qa-workflow-fix`
- 成员 D：`bugfix/frontend-graph-fix`

每个分支只改自己负责范围。确实需要跨范围修改时，先在群里说明。

## 每次开始工作前必须执行

```powershell
cd "D:\cxdownload\kg agent\kg_agent_app"
git status
git fetch origin
git checkout develop
git pull --rebase origin develop
git checkout -b bugfix/你的分支名
```

如果已经有自己的分支：

```powershell
cd "D:\cxdownload\kg agent\kg_agent_app"
git status
git fetch origin
git checkout bugfix/你的分支名
git rebase origin/develop
```

看到冲突不要继续写代码，先解决冲突或找队长处理。

## 每次提交前必须执行

```powershell
git status
python -m pytest tests/test_config_openai.py -q
```

如果改了后端接口，额外检查：

```powershell
python app.py
```

然后用浏览器或 curl 验证相关 API。

如果改了前端，必须手动打开页面验证：

```text
http://127.0.0.1:5000
```

## 提交规范

提交信息使用以下格式：

```text
fix: 修复图谱查询无结果
feat: 增加关系网络图数据接口
docs: 更新团队同步规定
test: 增加图结构分析接口测试
chore: 整理项目目录
```

一次提交只做一类事情。不要把格式化、功能修改、数据替换、文档修改混在一个提交里。

## Pull Request 规则

每个 PR 必须写清楚：

- 改了哪些文件。
- 修了哪个 bug。
- 怎么验证。
- 是否影响其他成员接口。
- 是否需要其他成员重新拉取数据。

PR 合并顺序：

1. 成员 A 的数据和 TTL 修复。
2. 成员 B 的后端 API 修复。
3. 成员 C 的智能问答链路修复。
4. 成员 D 的前端展示修复。

这个顺序不能随意打乱。图结构分析必须等关系网络图 API 有真实节点和边后再合并。

## 共享接口不允许随意改

以下接口路径是四人协作契约：

- `POST /api/query`
- `POST /api/sparql`
- `GET /api/graph-explore`
- `GET /api/person-detail`
- `GET /api/graph-analysis`
- `POST /api/graph-path`
- `GET /api/health`

如果必须改返回字段，先在 PR 描述里写清楚，并通知其他成员同步修改。

## 共享数据路径不允许随意改

固定数据路径：

- `data/kg/schema.ttl`
- `data/kg/core.ttl`
- `data/kg/aligned.ttl`
- `data/intermediate/entities.json`
- `data/intermediate/relations.json`
- `data/source/person_records_v5.json`

禁止新增 `data2/`、`new_data/`、`最终版/`、`我的版本/` 这类目录。

## 处理冲突规则

常见冲突文件：

- `templates/index.html`
- `static/styles.css`
- `src/web.py`
- `src/tools.py`
- `src/graph_analysis.py`

冲突处理流程：

1. 停止继续写新代码。
2. 在群里说明冲突文件。
3. 保留双方有效改动，不允许直接覆盖别人的代码。
4. 解决后至少运行相关功能验证。

## 队长合并前总检查

```powershell
git status
python -m pytest tests/test_config_openai.py -q
python app.py
```

页面检查：

- 首页能打开。
- 智能问答能返回。
- 图谱查询有结果。
- 关系网络图有节点和边。
- 图结构分析有 summary、centrality、communities、schoolEvolution。

只有上述检查通过，才能合并到 `main`。

