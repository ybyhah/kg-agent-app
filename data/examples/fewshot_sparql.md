# few-shot SPARQL 示例

这个文件用于成员 D 后续接入大模型时，作为问句到 SPARQL 的少样本示例集。

当前版本已经按成员 C 的真实 RDF 结构修正：

- 命名空间使用 `yrz: <http://www.yinrenzhuan.org/ontology#>`
- `core.ttl` 中的大多数关系不是“人物直接连属性”，而是：
  - `?relation rdf:type yrz:Relation`
  - `?relation yrz:relationType ...`
  - `?relation yrz:sourceEntity ...`
  - `?relation yrz:targetEntity ...`
- `aligned.ttl` 中部分生卒年是直接补充的字面量，所以生卒年查询要兼容两种写法

## 示例 1：查询字

问题：`文彭的字是什么？`

```sparql
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX yrz: <http://www.yinrenzhuan.org/ontology#>

SELECT ?person ?label ?courtesyNode ?courtesyLabel
WHERE {
  ?person rdf:type yrz:Person ;
          rdfs:label ?label .
  ?relation rdf:type yrz:Relation ;
            yrz:relationType yrz:hasCourtesyName ;
            yrz:sourceEntity ?person ;
            yrz:targetEntity ?courtesyNode .
  OPTIONAL { ?courtesyNode rdfs:label ?courtesyLabel . }
  FILTER(CONTAINS(STR(?label), "文彭"))
}
LIMIT 20
```

## 示例 2：查询号

问题：`文彭的号是什么？`

```sparql
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX yrz: <http://www.yinrenzhuan.org/ontology#>

SELECT ?person ?label ?artNode ?artLabel
WHERE {
  ?person rdf:type yrz:Person ;
          rdfs:label ?label .
  ?relation rdf:type yrz:Relation ;
            yrz:relationType yrz:hasArtName ;
            yrz:sourceEntity ?person ;
            yrz:targetEntity ?artNode .
  OPTIONAL { ?artNode rdfs:label ?artLabel . }
  FILTER(CONTAINS(STR(?label), "文彭"))
}
LIMIT 20
```

## 示例 3：查询生卒年

问题：`文彭的生卒年是什么？`

```sparql
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX yrz: <http://www.yinrenzhuan.org/ontology#>

SELECT ?person ?label
       (GROUP_CONCAT(DISTINCT ?birthText; separator=" / ") AS ?birthYear)
       (GROUP_CONCAT(DISTINCT ?deathText; separator=" / ") AS ?deathYear)
WHERE {
  ?person rdf:type yrz:Person ;
          rdfs:label ?label .

  OPTIONAL {
    {
      ?birthRelation rdf:type yrz:Relation ;
                     yrz:relationType yrz:bornIn ;
                     yrz:sourceEntity ?person ;
                     yrz:targetEntity ?birthNode .
      OPTIONAL { ?birthNode rdfs:label ?birthNodeLabel . }
      BIND(COALESCE(?birthNodeLabel, STR(?birthNode)) AS ?birthText)
    }
    UNION
    {
      ?person yrz:bornIn ?birthLiteral .
      FILTER(isLiteral(?birthLiteral))
      BIND(STR(?birthLiteral) AS ?birthText)
    }
  }

  OPTIONAL {
    {
      ?deathRelation rdf:type yrz:Relation ;
                     yrz:relationType yrz:diedIn ;
                     yrz:sourceEntity ?person ;
                     yrz:targetEntity ?deathNode .
      OPTIONAL { ?deathNode rdfs:label ?deathNodeLabel . }
      BIND(COALESCE(?deathNodeLabel, STR(?deathNode)) AS ?deathText)
    }
    UNION
    {
      ?person yrz:diedIn ?deathLiteral .
      FILTER(isLiteral(?deathLiteral))
      BIND(STR(?deathLiteral) AS ?deathText)
    }
  }

  FILTER(CONTAINS(STR(?label), "文彭"))
}
GROUP BY ?person ?label
LIMIT 20
```

## 示例 4：查询两人关系

问题：`文徵明与文彭是什么关系？`

```sparql
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX yrz: <http://www.yinrenzhuan.org/ontology#>

SELECT ?sourceLabel ?targetLabel ?relation ?relationLabel ?direction
WHERE {
  {
    ?source rdf:type yrz:Person ;
            rdfs:label ?sourceLabel .
    ?target rdf:type yrz:Person ;
            rdfs:label ?targetLabel .
    ?relationFact rdf:type yrz:Relation ;
                  yrz:relationType ?relation ;
                  yrz:sourceEntity ?source ;
                  yrz:targetEntity ?target .
    OPTIONAL { ?relation rdfs:label ?relationLabel . }
    BIND("正向" AS ?direction)
    FILTER(
      CONTAINS(STR(?sourceLabel), "文徵明") &&
      CONTAINS(STR(?targetLabel), "文彭")
    )
  }
  UNION
  {
    ?source rdf:type yrz:Person ;
            rdfs:label ?sourceLabel .
    ?target rdf:type yrz:Person ;
            rdfs:label ?targetLabel .
    ?relationFact rdf:type yrz:Relation ;
                  yrz:relationType ?relation ;
                  yrz:sourceEntity ?target ;
                  yrz:targetEntity ?source .
    OPTIONAL { ?relation rdfs:label ?relationLabel . }
    BIND("反向" AS ?direction)
    FILTER(
      CONTAINS(STR(?sourceLabel), "文徵明") &&
      CONTAINS(STR(?targetLabel), "文彭")
    )
  }
}
LIMIT 20
```

## 示例 5：查询流派开创者

问题：`谁开创了吴门印派？`

```sparql
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX yrz: <http://www.yinrenzhuan.org/ontology#>

SELECT ?founder ?founderLabel ?school ?schoolLabel
WHERE {
  ?relation rdf:type yrz:Relation ;
            yrz:relationType yrz:foundsSchool ;
            yrz:sourceEntity ?founder ;
            yrz:targetEntity ?school .
  OPTIONAL { ?founder rdfs:label ?founderLabel . }
  OPTIONAL { ?school rdfs:label ?schoolLabel . }
  FILTER(
    CONTAINS(STR(?schoolLabel), "吴门印派") ||
    CONTAINS("吴门印派", STR(?schoolLabel))
  )
}
LIMIT 20
```

## 说明

- 这些示例可以直接放进大模型提示词，也可以作为 LangGraph 中 “SPARQL 生成节点” 的 few-shot 参考。
- 如果后续成员 C 又调整了 `schema.ttl` 的关系命名，只需要同步改这里和 `src/fewshot_sparql.py`。
- 目前最适合展示的 few-shot 问题仍然是：
  - 字 / 号
  - 生卒年
  - 两人关系
  - 流派开创者
