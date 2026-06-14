from __future__ import annotations

import re
from dataclasses import dataclass


PREFIX_BLOCK = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX yrz: <http://www.yinrenzhuan.org/ontology#>
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
SELECT ?person ?label ?courtesyNode ?courtesyLabel
WHERE {{
  ?person rdf:type yrz:Person ;
          rdfs:label ?label .
  ?relation rdf:type yrz:Relation ;
            yrz:relationType yrz:hasCourtesyName ;
            yrz:sourceEntity ?person ;
            yrz:targetEntity ?courtesyNode .
  OPTIONAL {{ ?courtesyNode rdfs:label ?courtesyLabel . }}
  FILTER(CONTAINS(STR(?label), "{person}"))
}}
LIMIT 20
""".strip(),
                description="适合查询人物的字，已对齐成员 C 的关系实例建模。",
            ),
            FewShotExample(
                name="查询号",
                question="文彭的号是什么？",
                template="""
{prefixes}
SELECT ?person ?label ?artNode ?artLabel
WHERE {{
  ?person rdf:type yrz:Person ;
          rdfs:label ?label .
  ?relation rdf:type yrz:Relation ;
            yrz:relationType yrz:hasArtName ;
            yrz:sourceEntity ?person ;
            yrz:targetEntity ?artNode .
  OPTIONAL {{ ?artNode rdfs:label ?artLabel . }}
  FILTER(CONTAINS(STR(?label), "{person}"))
}}
LIMIT 20
""".strip(),
                description="适合查询人物的号，已对齐成员 C 的关系实例建模。",
            ),
            FewShotExample(
                name="查询生卒年",
                question="文彭的生卒年是什么？",
                template="""
{prefixes}
SELECT ?person ?label
       (GROUP_CONCAT(DISTINCT ?birthText; separator=" / ") AS ?birthYear)
       (GROUP_CONCAT(DISTINCT ?deathText; separator=" / ") AS ?deathYear)
WHERE {{
  ?person rdf:type yrz:Person ;
          rdfs:label ?label .

  OPTIONAL {{
    {{
      ?birthRelation rdf:type yrz:Relation ;
                     yrz:relationType yrz:bornIn ;
                     yrz:sourceEntity ?person ;
                     yrz:targetEntity ?birthNode .
      OPTIONAL {{ ?birthNode rdfs:label ?birthNodeLabel . }}
      BIND(COALESCE(?birthNodeLabel, STR(?birthNode)) AS ?birthText)
    }}
    UNION
    {{
      ?person yrz:bornIn ?birthLiteral .
      FILTER(isLiteral(?birthLiteral))
      BIND(STR(?birthLiteral) AS ?birthText)
    }}
  }}

  OPTIONAL {{
    {{
      ?deathRelation rdf:type yrz:Relation ;
                     yrz:relationType yrz:diedIn ;
                     yrz:sourceEntity ?person ;
                     yrz:targetEntity ?deathNode .
      OPTIONAL {{ ?deathNode rdfs:label ?deathNodeLabel . }}
      BIND(COALESCE(?deathNodeLabel, STR(?deathNode)) AS ?deathText)
    }}
    UNION
    {{
      ?person yrz:diedIn ?deathLiteral .
      FILTER(isLiteral(?deathLiteral))
      BIND(STR(?deathLiteral) AS ?deathText)
    }}
  }}

  FILTER(CONTAINS(STR(?label), "{person}"))
}}
GROUP BY ?person ?label
LIMIT 20
""".strip(),
                description="适合查询人物的生卒年，同时兼容 core.ttl 与 aligned.ttl。",
            ),
            FewShotExample(
                name="查询两人关系",
                question="文徵明与文彭是什么关系？",
                template="""
{prefixes}
SELECT ?sourceLabel ?targetLabel ?relation ?relationLabel ?direction
WHERE {{
  {{
    ?source rdf:type yrz:Person ;
            rdfs:label ?sourceLabel .
    ?target rdf:type yrz:Person ;
            rdfs:label ?targetLabel .
    ?relationFact rdf:type yrz:Relation ;
                  yrz:relationType ?relation ;
                  yrz:sourceEntity ?source ;
                  yrz:targetEntity ?target .
    OPTIONAL {{ ?relation rdfs:label ?relationLabel . }}
    BIND("正向" AS ?direction)
    FILTER(
      CONTAINS(STR(?sourceLabel), "{person_a}") &&
      CONTAINS(STR(?targetLabel), "{person_b}")
    )
  }}
  UNION
  {{
    ?source rdf:type yrz:Person ;
            rdfs:label ?sourceLabel .
    ?target rdf:type yrz:Person ;
            rdfs:label ?targetLabel .
    ?relationFact rdf:type yrz:Relation ;
                  yrz:relationType ?relation ;
                  yrz:sourceEntity ?target ;
                  yrz:targetEntity ?source .
    OPTIONAL {{ ?relation rdfs:label ?relationLabel . }}
    BIND("反向" AS ?direction)
    FILTER(
      CONTAINS(STR(?sourceLabel), "{person_a}") &&
      CONTAINS(STR(?targetLabel), "{person_b}")
    )
  }}
}}
LIMIT 20
""".strip(),
                description="适合查询两个人物之间的直接关系。",
            ),
            FewShotExample(
                name="查询流派开创者",
                question="谁开创了吴门印派？",
                template="""
{prefixes}
SELECT ?founder ?founderLabel ?school ?schoolLabel
WHERE {{
  ?relation rdf:type yrz:Relation ;
            yrz:relationType yrz:foundsSchool ;
            yrz:sourceEntity ?founder ;
            yrz:targetEntity ?school .
  OPTIONAL {{ ?founder rdfs:label ?founderLabel . }}
  OPTIONAL {{ ?school rdfs:label ?schoolLabel . }}
  FILTER(
    CONTAINS(STR(?schoolLabel), "{school}") ||
    CONTAINS("{school}", STR(?schoolLabel))
  )
}}
LIMIT 20
""".strip(),
                description="适合查询某流派的开创者，并兼容简称与全称部分匹配。",
            ),
        ]

    def try_generate(self, question: str) -> FewShotDraft | None:
        normalized = question.strip().rstrip("？。")
        if not normalized:
            return None

        pair_match = re.match(r"^(.+?)[与和](.+?)是什么关系", normalized)
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
            "请严格基于 RDF/SPARQL 生成可执行查询，优先复用 yrz 命名空间和成员 C 的正式本体。\n"
            "注意 core.ttl 的关系不是人物和属性直接相连，而是通过 yrz:Relation + "
            "yrz:relationType / yrz:sourceEntity / yrz:targetEntity 表示。\n\n"
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
            note=f"{example.description} 当前 few-shot 已对齐成员 C 的真实 RDF 结构。",
        )

    def _escape_literal(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')
