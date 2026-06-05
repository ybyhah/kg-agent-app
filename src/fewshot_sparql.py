from __future__ import annotations

import re
from dataclasses import dataclass


PREFIX_BLOCK = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX ex: <http://example.org/kg/>
""".strip()


@dataclass(frozen=True)
class FewShotExample:
    name: str
    question: str
    template: str
    description: str


@dataclass(frozen=True)
class FewShotDraft:
    example_name: str
    question: str
    sparql: str
    note: str


class FewShotSparqlGenerator:
    def __init__(self):
        self.examples = [
            FewShotExample(
                name="查询字",
                question="文彭的字是什么？",
                template="""
{prefixes}
SELECT ?person ?label ?courtesyName
WHERE {{
  ?person rdfs:label ?label ;
          ex:hasCourtesyName ?courtesyName .
  FILTER(CONTAINS(STR(?label), "{person}"))
}}
LIMIT 20
""".strip(),
                description="适合查询人物的字。",
            ),
            FewShotExample(
                name="查询号",
                question="文彭的号是什么？",
                template="""
{prefixes}
SELECT ?person ?label ?artName
WHERE {{
  ?person rdfs:label ?label ;
          ex:hasArtName ?artName .
  FILTER(CONTAINS(STR(?label), "{person}"))
}}
LIMIT 20
""".strip(),
                description="适合查询人物的号。",
            ),
            FewShotExample(
                name="查询生卒年",
                question="文彭的生卒年是什么？",
                template="""
{prefixes}
SELECT ?person ?label ?birthYear ?deathYear
WHERE {{
  ?person rdfs:label ?label .
  OPTIONAL {{ ?person ex:birthYear ?birthYear . }}
  OPTIONAL {{ ?person ex:deathYear ?deathYear . }}
  FILTER(CONTAINS(STR(?label), "{person}"))
}}
LIMIT 20
""".strip(),
                description="适合查询人物的生卒年。",
            ),
            FewShotExample(
                name="查询两人关系",
                question="文徵明与文彭是什么关系？",
                template="""
{prefixes}
SELECT ?sourceLabel ?targetLabel ?relation ?relationLabel
WHERE {{
  ?source rdfs:label ?sourceLabel .
  ?target rdfs:label ?targetLabel .
  ?source ?relation ?target .
  OPTIONAL {{ ?relation rdfs:label ?relationLabel . }}
  FILTER(CONTAINS(STR(?sourceLabel), "{person_a}") && CONTAINS(STR(?targetLabel), "{person_b}"))
}}
LIMIT 20
""".strip(),
                description="适合查询两个人物的直接关系。",
            ),
            FewShotExample(
                name="查询流派开创者",
                question="谁开创了吴门印派？",
                template="""
{prefixes}
SELECT ?founder ?founderLabel ?school ?schoolLabel
WHERE {{
  ?founder ex:foundsSchool ?school ;
           rdfs:label ?founderLabel .
  ?school rdfs:label ?schoolLabel .
  FILTER(CONTAINS(STR(?schoolLabel), "{school}"))
}}
LIMIT 20
""".strip(),
                description="适合查询某流派的开创者。",
            ),
        ]

    def try_generate(self, question: str) -> FewShotDraft | None:
        normalized = question.strip().rstrip("？?。")
        if not normalized:
            return None

        pair_match = re.match(r"^(.+?)[与和](.+?)是什么关系$", normalized)
        if pair_match:
            person_a = pair_match.group(1).strip()
            person_b = pair_match.group(2).strip()
            return self._build_from_example(
                "查询两人关系",
                question,
                person_a=person_a,
                person_b=person_b,
            )

        if "谁开创了" in normalized:
            school = normalized.split("谁开创了", 1)[-1].strip()
            return self._build_from_example("查询流派开创者", question, school=school)

        for suffix, example_name in [
            ("的字是什么", "查询字"),
            ("的号是什么", "查询号"),
            ("的生卒年是什么", "查询生卒年"),
        ]:
            if normalized.endswith(suffix):
                person = normalized[: -len(suffix)].strip()
                return self._build_from_example(example_name, question, person=person)

        return None

    def build_prompt(self, question: str) -> str:
        example_blocks = []
        for example in self.examples:
            example_blocks.append(
                f"问题：{example.question}\nSPARQL：\n{example.template}"
            )
        joined_examples = "\n\n".join(example_blocks)
        return (
            "你是《印人传》知识图谱问答系统的 SPARQL 生成模块。\n"
            "请严格基于 RDF/SPARQL 生成可执行查询，优先复用已有命名空间和属性。\n\n"
            f"{joined_examples}\n\n"
            f"现在请为这个问题生成 SPARQL：{question}"
        )

    def _build_from_example(self, example_name: str, question: str, **kwargs: str) -> FewShotDraft | None:
        example = next((item for item in self.examples if item.name == example_name), None)
        if example is None:
            return None

        safe_kwargs = {key: self._escape_literal(value) for key, value in kwargs.items()}
        sparql = example.template.format(prefixes=PREFIX_BLOCK, **safe_kwargs)
        return FewShotDraft(
            example_name=example.name,
            question=question,
            sparql=sparql,
            note=f"{example.description} 当前属于 few-shot 骨架版本，后续可直接接入 LLM 生成链。",
        )

    def _escape_literal(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')
