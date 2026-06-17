# 《印人传》知识抽取模块 - 实现文档

## 一、模块概述

本模块负责从《印人传》文本中进行**命名实体识别（NER）**和**关系抽取**，使用 LangChain + DeepSeek API 实现。

### 1.1 任务目标

| 任务 | 说明 |
|------|------|
| NER | 抽取人物、地名、时间、字号、流派、印章、作品、书体印风等实体 |
| 关系抽取 | 抽取父子、师承、交游、籍贯、流派归属等关系 |
| 结构化输出 | 将抽取结果转换为 JSON 格式 |

### 1.2 交付物清单

| 交付物 | 说明 | 文件位置 |
|--------|------|----------|
| `entities.json` | 所有实体的JSON文件（15673个实体） | 根目录 |
| `relations.json` | 所有关系的JSON文件（12498条关系） | 根目录 |
| `extraction_prompt.txt` | 抽取提示词模板 | 根目录 |
| `evaluation_sample.json` | 评测样本数据（5条） | 根目录 |
| `extraction_schema.json` | 实体和关系类型定义 | 根目录 |
| `关系抽取.md` | 实现方法文档 | 根目录 |

---

## 二、所有文件说明

### 2.1 交付物文件

| 文件 | 类型 | 大小 | 用途 |
|------|------|------|------|
| `entities.json` | JSON | ~8MB | 包含所有抽取的实体，供成员C构建图谱使用 |
| `relations.json` | JSON | ~6MB | 包含所有抽取的关系，供成员C构建图谱使用 |
| `extraction_prompt.txt` | TXT | ~3KB | LLM抽取使用的提示词模板，可复用 |
| `evaluation_sample.json` | JSON | ~4KB | 5条评测样本，用于质量评估 |
| `extraction_schema.json` | JSON | ~5KB | 实体和关系类型的Schema定义 |
| `关系抽取.md` | MD | ~10KB | 本实现文档 |

### 2.2 脚本文件

| 文件 | 用途 | 使用方式 |
|------|------|----------|
| `batch_extract_langchain.py` | LangChain交互式批处理脚本 | `python batch_extract_langchain.py` |
| `auto_extract_langchain.py` | 自动批处理脚本（不间断运行） | `python auto_extract_langchain.py` |
| `rule_based_extract.py` | 规则抽取器（当API不可用时使用） | 自动调用或手动调用 |

### 2.3 输入数据文件

| 文件 | 用途 | 说明 |
|------|------|------|
| `person_records_v5.json` | 输入数据 | 包含1673条人物传记记录 |

### 2.4 输出目录

| 目录 | 内容 | 用途 |
|------|------|------|
| `extraction_results/` | 1673个JSON文件 | 每条记录独立的抽取结果，便于调试和追溯 |

---

## 三、技术实现

### 3.1 技术栈

| 组件 | 版本 | 说明 |
|------|------|------|
| Python | 3.8+ | 编程语言 |
| LangChain | 0.1.x | LLM编排框架 |
| DeepSeek API | v4 | 大语言模型服务 |
| requests | 2.x | HTTP请求库 |

### 3.2 核心流程

输入文本 → 构造Prompt → 调用DeepSeek API → 解析JSON → 规范化输出 → 保存文件

### 3.3 关键代码

#### 3.3.1 LangChain Pipeline

```python
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

# 配置LLM
llm = ChatOpenAI(
    model="deepseek-chat",
    base_url="https://api.deepseek.com",
    api_key="sk-xxx",
    temperature=0.2
)

# 定义Prompt
prompt = PromptTemplate(
    input_variables=["person_name", "text"],
    template=PROMPT_TEMPLATE
)

# 构建Chain
chain = prompt | llm | StrOutputParser()

# 调用
result = chain.invoke({
    "person_name": "文彭",
    "text": "文彭，字寿承，号三桥..."
})
```

---

## 四、数据格式

### 4.1 实体格式

```json
{
  "id": "YRZ_00001_e1",
  "type": "人物",
  "name": "方仲芝",
  "attributes": {},
  "source_text": "方仲芝，以其工象牙黄杨也。",
  "confidence": 0.9,
  "source_record": "YRZ_00001"
}
```

### 4.2 关系格式

```json
{
  "id": "YRZ_00001_r1",
  "type": "父子",
  "source": "许采",
  "target": "玉史",
  "source_text": "玉史学宪讳豸者之长子",
  "confidence": 0.9,
  "source_record": "YRZ_00001"
}
```

### 4.3 实体类型统计

| 类型 | 数量 |
|------|------|
| 人物 | 5,300 |
| 字号 | 3,811 |
| 地名 | 2,907 |
| 作品 | 1,783 |
| 书体印风 | 804 |
| 时间 | 422 |
| 印章 | 194 |
| 流派 | 108 |

### 4.4 关系类型统计

| 类型 | 数量 |
|------|------|
| 字号对应 | 3,834 |
| 籍贯 | 2,139 |
| 擅长 | 1,462 |
| 著有 | 1,064 |
| 交游 | 920 |
| 师承 | 734 |
| 创作 | 574 |
| 活动于 | 428 |
| 父子 | 424 |
| 任职于 | 283 |

---

## 五、使用说明

### 5.1 环境配置

```bash
# 安装依赖
pip install langchain langchain-openai requests
```

### 5.2 运行批处理

```bash
# 使用LangChain批处理脚本（交互式）
python batch_extract_langchain.py

# 使用自动批处理脚本（不间断）
python auto_extract_langchain.py
```

### 5.3 输出文件结构

```
知识图谱2/
├── entities.json                    # 所有实体
├── relations.json                   # 所有关系
├── extraction_schema.json           # 类型定义
├── extraction_prompt.txt            # 提示词
├── evaluation_sample.json           # 评测样本
├── 关系抽取.md                       # 实现文档
├── person_records_v5.json           # 输入数据
├── batch_extract_langchain.py       # 批处理脚本
├── auto_extract_langchain.py        # 自动批处理脚本
├── rule_based_extract.py            # 规则抽取器
└── extraction_results/              # 单条记录结果
    ├── YRZ_00001_extraction.json
    ├── YRZ_00002_extraction.json
    └── ... (共1673个文件)
```

---

## 六、评测方法

### 6.1 评测指标

| 指标 | 计算方式 |
|------|----------|
| 实体准确率 | 正确实体数/总实体数 |
| 实体召回率 | 正确实体数/标注实体数 |
| 关系准确率 | 正确关系数/总关系数 |
| 关系召回率 | 正确关系数/标注关系数 |

### 6.2 评测样本

评测样本包含5条典型记录：YRZ_00001、YRZ_00101、YRZ_00501、YRZ_01001、YRZ_01501

---

## 七、注意事项

1. **API调用限制**：DeepSeek API有调用频率限制，建议每请求间隔0.8秒
2. **文本截断**：单条文本超过3000字符时自动截断
3. **错误处理**：API调用失败时自动重试3次
4. **进度保存**：支持断点续跑

---

## 八、附录

### 8.1 关系类型定义表

| 关系类型 | 头实体类型 | 尾实体类型 |
|----------|------------|------------|
| 父子 | 人物 | 人物 |
| 师承 | 人物 | 人物 |
| 交游 | 人物 | 人物 |
| 字号对应 | 人物 | 字号 |
| 籍贯 | 人物 | 地名 |
| 活动于 | 人物 | 地名 |
| 任职于 | 人物 | 地名 |
| 生于 | 人物 | 时间 |
| 卒于 | 人物 | 时间 |
| 擅长 | 人物 | 书体印风 |
| 创作 | 人物 | 印章 |
| 著有 | 人物 | 作品 |
| 流派归属 | 人物 | 流派 |
| 开创 | 人物 | 流派 |

### 8.2 文件用途速查表

| 文件 | 用途分类 | 使用场景 |
|------|----------|----------|
| `entities.json` | 输出数据 | 成员C构建图谱时读取 |
| `relations.json` | 输出数据 | 成员C构建图谱时读取 |
| `extraction_schema.json` | 配置文件 | 定义实体和关系类型 |
| `extraction_prompt.txt` | 配置文件 | LLM抽取时使用 |
| `evaluation_sample.json` | 测试数据 | 质量评估时使用 |
| `implementation_doc.md` | 文档 | 技术说明和使用指南 |
| `batch_extract_langchain.py` | 脚本 | 手动运行批处理 |
| `auto_extract_langchain.py` | 脚本 | 自动运行批处理 |
| `rule_based_extract.py` | 脚本 | API不可用时备用 |
| `person_records_v5.json` | 输入数据 | 抽取的数据源 |
| `extraction_results/` | 输出目录 | 单条记录详细结果 |
