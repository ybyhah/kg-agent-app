"""
《印人传》知识抽取 - LangChain版本
成员B - NER和关系抽取
"""
import json
import os
import time
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

# DeepSeek API配置
os.environ["OPENAI_API_KEY"] = "sk-c9cb063d31f04392b40282c5b0c7889e"
os.environ["OPENAI_BASE_URL"] = "https://api.deepseek.com"

# 初始化LLM
llm = ChatOpenAI(
    model="deepseek-chat",
    temperature=0.2,
    max_tokens=4000
)

# 实体抽取Prompt
ENTITY_PROMPT = PromptTemplate.from_template("""你是《印人传》知识抽取专家。从原文中抽取实体。

【实体类型】
- 人物：印人、文人、官员
- 地名：籍贯、活动地、任职地
- 时间：朝代、年份、生卒年
- 字号：字、号、别号
- 书体印风：篆刻风格
- 流派：篆刻流派
- 印章：印章名称
- 作品：印谱、诗文集

【原文】
{text}

【人物】
{person_name}

严格输出JSON格式：
{{"entities": [{{"type": "类型", "name": "名称", "attributes": {{}}, "source_text": "原文", "confidence": 0.9}}]}}
只输出JSON，不要其他文字。""")

# 关系抽取Prompt
RELATION_PROMPT = PromptTemplate.from_template("""你是《印人传》关系抽取专家。基于实体和原文抽取关系。

【关系类型】
父子、师承、交游、流派归属、开创、字号对应、籍贯、活动于、任职于、生于、卒于、擅长、创作、著有

【原文】
{text}

【已识别实体】
{entities}

输出JSON：
{{"relations": [{{"type": "关系类型", "source": "头实体名", "target": "尾实体名", "source_text": "原文", "confidence": 0.9}}]}}
只输出JSON。""")


def extract_entities(text, person_name):
    """抽取实体"""
    try:
        chain = ENTITY_PROMPT | llm | StrOutputParser()
        result = chain.invoke({"text": text[:3000], "person_name": person_name})
        data = parse_json(result)
        if data:
            entities = data.get("entities", [])
            for i, e in enumerate(entities):
                e["id"] = f"{person_name}_e{i+1}"
                e.setdefault("attributes", {})
                e.setdefault("source_text", text[:80])
                e.setdefault("confidence", 0.9)
            return entities
    except Exception as e:
        print(f"    实体抽取错误: {e}")
    return []


def extract_relations(text, entities, person_name):
    """抽取关系"""
    if not entities:
        return []
    try:
        chain = RELATION_PROMPT | llm | StrOutputParser()
        result = chain.invoke({
            "text": text[:3000],
            "entities": json.dumps(entities, ensure_ascii=False)
        })
        data = parse_json(result)
        if data:
            relations = data.get("relations", [])
            for i, r in enumerate(relations):
                r["id"] = f"{person_name}_r{i+1}"
                r.setdefault("source_text", text[:80])
                r.setdefault("confidence", 0.9)
            return relations
    except Exception as e:
        print(f"    关系抽取错误: {e}")
    return []


def parse_json(text):
    """解析JSON"""
    if not text:
        return None
    text = text.strip()
    # 移除代码块标记
    for marker in ["```json", "```"]:
        if text.startswith(marker):
            text = text[len(marker):]
    # 找JSON
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        json_str = text[start:end+1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # 尝试修复不完整的JSON
            pass
    # 尝试平衡括号
    if start >= 0:
        partial = text[start:]
        depth = 0
        in_str = False
        escape = False
        for c in partial:
            if escape:
                escape = False
                continue
            if c == '\\':
                escape = True
                continue
            if c == '"':
                in_str = not in_str
                continue
            if not in_str:
                if c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
        # 补充缺失的 }
        if depth > 0:
            json_str = partial + '}' * depth
            try:
                return json.loads(json_str)
            except:
                pass
    return None


def run_batch(batch_size=10):
    """处理一批数据"""
    os.makedirs("extraction_results", exist_ok=True)

    # 读取数据
    with open("person_records_v5.json", "r", encoding="utf-8") as f:
        all_records = json.load(f)

    # 读取进度
    progress_file = "extraction_results/batch_progress.json"
    if os.path.exists(progress_file):
        with open(progress_file, "r", encoding="utf-8") as f:
            progress = json.load(f)
        start = progress.get("next_index", 0)
        total_entities = progress.get("total_entities", 0)
        total_relations = progress.get("total_relations", 0)
    else:
        start = 0
        total_entities = 0
        total_relations = 0

    if start >= len(all_records):
        print("所有记录已处理完成！")
        return

    end = min(start + batch_size, len(all_records))
    records = all_records[start:end]

    print(f"=" * 50)
    print(f"LangChain版 - 处理第 {start+1} - {end} 条 (共 {len(all_records)} 条)")
    print(f"=" * 50)

    batch_entities = 0
    batch_relations = 0

    for i, r in enumerate(records):
        seq = start + i + 1
        print(f"[{seq}/{len(all_records)}] {r['record_id']} - {r['person_name']}", end="")

        # 抽取实体
        entities = extract_entities(r["source_text"], r["person_name"])
        print(f" E:{len(entities)}", end="")

        # 抽取关系
        relations = extract_relations(r["source_text"], entities, r["person_name"])
        print(f" R:{len(relations)}")

        batch_entities += len(entities)
        batch_relations += len(relations)

        # 保存单条
        result = {
            "record_id": r["record_id"],
            "person_name": r["person_name"],
            "entities": entities,
            "relations": relations
        }
        with open(f"extraction_results/{r['record_id']}_extraction.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

    # 更新进度
    total_entities += batch_entities
    total_relations += batch_relations

    with open(progress_file, "w", encoding="utf-8") as f:
        json.dump({
            "next_index": end,
            "total_entities": total_entities,
            "total_relations": total_relations
        }, f, ensure_ascii=False, indent=2)

    print(f"\n本批完成！实体 {batch_entities}, 关系 {batch_relations}")
    print(f"累计: 实体 {total_entities}, 关系 {total_relations}")
    print(f"进度: {end}/{len(all_records)} ({end*100/len(all_records):.1f}%)")


if __name__ == "__main__":
    import sys
    batch = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    run_batch(batch)
