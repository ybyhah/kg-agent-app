# 印人传知识图谱智能问答系统

基于知识图谱和大语言模型的智能问答系统，支持人物关系查询、流派分析、图谱可视化等功能。

## 项目简介

本项目是《印人传》篆刻艺术领域的知识图谱问答系统，包含：
- 📚 知识图谱构建（人物、流派、关系）
- 🤖 智能问答（固定工具 + 生成式SPARQL + LLM fallback）
- 📊 关系图谱可视化
- 🔍 图结构分析（中心性、社区发现、路径分析）

## 技术栈

### 后端
- **Python 3.10+**
- **Flask** - Web框架
- **RDFLib** - RDF图谱操作
- **LangGraph** - 工作流编排
- **LangChain** - LLM工具调用
- **DeepSeek API** - 大语言模型

### 前端
- **原生HTML/CSS/JavaScript**
- **Lucide Icons**
- **力导向图布局**

### 知识图谱
- **Turtle (TTL)** 格式
- **SPARQL** 查询语言
- **RDF/RDFS/OWL** 本体

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd yinrenzhuan-kg-qa

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，配置API密钥：

```env
FLASK_DEBUG=1
PORT=5000
KG_AGENT_LLM_MODE=openai
DEEPSEEK_API_KEY=你的DeepSeek_API密钥
KG_AGENT_OPENAI_MODEL=deepseek-v4-flash
KG_AGENT_OPENAI_BASE_URL=https://api.deepseek.com
```

### 3. 准备知识图谱数据

确保 `data/kg/` 目录下有以下文件：
- `schema.ttl` - 本体定义（~12KB）
- `core.ttl` - 核心数据（~25MB）
- `aligned.ttl` - 对齐数据（~650KB）

### 4. 启动服务

```bash
python app.py
```

**首次启动**需要30-60秒加载知识图谱数据，看到以下提示后即可访问：
```
正在加载知识图谱数据...
[OK] 知识图谱加载完成
 * Running on http://127.0.0.1:5000
```

访问 http://127.0.0.1:5000

## 项目结构

```
yinrenzhuan-kg-qa/
├── src/                          # 源代码
│   ├── bootstrap.py              # 应用初始化
│   ├── config.py                 # 配置管理
│   ├── service.py                # 服务层
│   ├── web.py                    # Flask路由
│   ├── workflow.py               # 查询工作流
│   ├── tool_calling_workflow.py  # 工具调用工作流
│   ├── tools.py                  # 固定查询工具
│   ├── langchain_tools.py        # LangChain工具适配
│   ├── fewshot_sparql.py         # Few-shot SPARQL生成
│   ├── llm_workflow_support.py   # LLM支持
│   ├── openai_llm.py             # OpenAI客户端
│   ├── graph_store.py            # 图谱存储
│   ├── graph_analysis.py         # 图结构分析
│   ├── models.py                 # 数据模型
│   └── agent_tools.py            # Agent工具箱
├── templates/                    # HTML模板
│   └── index.html                # 主页面
├── static/                       # 静态资源
│   └── styles.css                # 样式表
├── data/                         # 数据目录
│   ├── kg/                       # 知识图谱数据
│   │   ├── schema.ttl            # 本体定义
│   │   ├── core.ttl              # 核心数据
│   │   └── aligned.ttl           # 对齐数据
│   └── examples/                 # 示例数据
│       └── fewshot_sparql.md     # Few-shot示例
├── docs/                         # 文档
│   ├── README.md                 # 项目说明
│   ├── ARCHITECTURE.md           # 架构设计
│   ├── WORKFLOW.md               # 工作流说明
│   ├── API.md                    # API文档
│   └── DEPLOYMENT.md             # 部署指南
├── tests/                        # 测试脚本
│   ├── test_api_key.py           # API密钥测试
│   ├── test_all_routes.py        # 所有链路测试
│   └── quick_test.py             # 快速测试
├── .env.example                  # 环境变量示例
├── .gitignore                    # Git忽略文件
├── requirements.txt              # Python依赖
├── app.py                        # 应用入口
├── wsgi.py                       # WSGI入口
└── README.md                     # 本文档
```

## 核心功能

### 1. 智能问答

系统支持三条查询链路：

#### 链路1: 固定工具（Function Calling）
适用于简单事实查询，响应速度快（2-5秒）：
- "文彭的字和号是什么？"
- "文彭的师承关系有哪些？"
- "文彭的师兄弟有哪些人？"
- "谁开创了吴门印派？"

#### 链路2: 生成式SPARQL
适用于复杂查询，LLM生成SPARQL（10-15秒）：
- "文彭的师兄弟中有哪些人也是吴门印派的？"
- "哪个流派的人物最多？"
- "吴门印派的代表人物中，谁的交游关系最广？"

#### 链路3: Fallback
当前两条链路都失败时，LLM给出谨慎说明。

### 2. 图谱查询台

支持直接编写SPARQL查询，实时返回结果。

### 3. 关系图谱可视化

- 全量图谱加载
- 单人物扩展（1跳/2跳）
- 关系类型筛选
- 节点交互（点击查看详情）

### 4. 图结构分析

- **中心性分析** - 度中心性、介数中心性
- **社区发现** - 交游群体、师承群体
- **路径分析** - 人物可达路径
- **流派演变** - 流派核心人物与关联

## 团队协作指南

### 分工建议

#### 前端开发
**负责**: UI/UX、可视化、交互
- `templates/index.html` - 页面结构和交互逻辑
- `static/styles.css` - 样式和动画
- 图谱可视化优化（力导向布局、动画效果）
- 响应式设计

#### 后端开发
**负责**: API、工作流、工具
- `src/web.py` - Flask路由和API
- `src/workflow.py` - 查询工作流
- `src/tools.py` - 固定查询工具
- 性能优化、错误处理

#### 知识图谱
**负责**: 本体设计、数据构建、SPARQL
- `data/kg/schema.ttl` - 本体定义
- `data/kg/core.ttl` - 数据实例
- `data/examples/fewshot_sparql.md` - Few-shot示例
- 数据质量保证

#### 算法/NLP
**负责**: LLM集成、SPARQL生成、图分析
- `src/llm_workflow_support.py` - LLM支持
- `src/fewshot_sparql.py` - SPARQL生成
- `src/graph_analysis.py` - 图结构分析
- Prompt优化

### Git工作流

#### 分支策略
```
main              # 主分支（稳定版本）
├── develop       # 开发分支（集成分支）
├── feature/xxx   # 功能分支
├── bugfix/xxx    # 修复分支
└── hotfix/xxx    # 紧急修复
```

#### 开发流程

1. **创建功能分支**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/your-feature-name
   ```

2. **开发并提交**
   ```bash
   git add .
   git commit -m "feat: 添加xxx功能"
   ```

3. **推送到远程**
   ```bash
   git push origin feature/your-feature-name
   ```

4. **创建Pull Request**
   - 在GitHub上创建PR
   - 目标分支: `develop`
   - 填写PR模板（功能说明、测试结果）

5. **代码审查**
   - 至少1人审查通过
   - 所有讨论解决
   - CI检查通过

6. **合并到develop**
   - Squash and merge
   - 删除功能分支

#### Commit规范

使用Conventional Commits规范：

```
feat: 新增功能
fix: 修复bug
docs: 文档更新
style: 代码格式（不影响功能）
refactor: 重构
perf: 性能优化
test: 测试相关
chore: 构建/工具链相关
```

示例：
```
feat: 添加师兄弟查询工具
fix: 修复API密钥验证错误
docs: 更新README部署说明
perf: 优化TTL加载性能
```

### Code Review清单

#### Python代码
- [ ] 遵循PEP 8规范
- [ ] 类型注解完整
- [ ] 错误处理妥当
- [ ] 无硬编码配置
- [ ] 有必要的注释

#### 前端代码
- [ ] 变量命名清晰
- [ ] 函数职责单一
- [ ] 避免全局变量
- [ ] 事件监听正确清理
- [ ] 兼容性考虑

#### 知识图谱
- [ ] 符合本体定义
- [ ] 数据格式一致
- [ ] SPARQL查询测试
- [ ] 性能可接受

## 测试

### 运行测试

```bash
# API密钥测试
python tests/test_api_key.py

# 快速功能测试
python tests/quick_test.py

# 所有链路测试
python tests/test_all_routes.py
```

### 手动测试

启动服务后，测试以下场景：

1. **固定工具链路**
   - 文彭的字和号
   - 师承关系
   - 师兄弟查询

2. **生成式SPARQL链路**
   - 复杂关系查询
   - 统计聚合查询

3. **图谱可视化**
   - 全量加载
   - 单人扩展
   - 节点交互

4. **图结构分析**
   - 中心性分析
   - 社区发现
   - 路径分析

## 常见问题

### Q: 首次启动很慢？
A: 需要加载25MB的知识图谱数据，首次启动30-60秒正常。加载完成后，所有查询都会快速响应（2-5秒）。

### Q: API调用失败？
A: 检查 `.env` 文件中的 `DEEPSEEK_API_KEY` 是否正确，运行 `python tests/test_api_key.py` 验证。

### Q: SPARQL查询无结果？
A: 检查：
1. TTL文件是否完整加载
2. SPARQL语法是否正确
3. 使用的属性名是否在本体中定义

### Q: 如何添加新的查询工具？
A: 参考 `src/tools.py` 中的现有工具：
1. 在 `QueryTools` 类中添加方法
2. 在 `src/langchain_tools.py` 中注册
3. 更新 `src/tool_calling_workflow.py` 的repair逻辑

## 部署

### 开发环境
```bash
python app.py
```

### 生产环境（使用Gunicorn）
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
```

### Docker部署
```bash
# 构建镜像
docker build -t yinrenzhuan-kg-qa .

# 运行容器
docker run -d -p 5000:5000 --env-file .env yinrenzhuan-kg-qa
```

## 性能优化

- ✅ 服务单例模式 - 避免重复加载TTL
- ✅ GraphStore缓存 - 图谱数据复用
- ✅ API超时控制 - 防止长时间等待
- ✅ 固定工具优先 - 快速响应简单查询

## 贡献指南

1. Fork本项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'feat: 添加某个功能'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建Pull Request

## 许可证

[MIT License](LICENSE)

## 联系方式

项目负责人: [你的名字]
项目地址: [GitHub Repository URL]
