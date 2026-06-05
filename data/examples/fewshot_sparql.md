# few-shot SPARQL 示例

这个文件用于成员 D 后续接入大模型时，作为问句到 SPARQL 的少样本示例集。

## 示例 1：查询字

问题：
`文彭的字是什么？`

SPARQL：

```sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX ex: <http://example.org/kg/>

SELECT ?person ?label ?courtesyName
WHERE {
  ?person rdfs:label ?label ;
          ex:hasCourtesyName ?courtesyName .
  FILTER(CONTAINS(STR(?label), "文彭"))
}
LIMIT 20
```

## 示例 2：查询号

问题：
`文彭的号是什么？`

SPARQL：

```sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX ex: <http://example.org/kg/>

SELECT ?person ?label ?artName
WHERE {
  ?person rdfs:label ?label ;
          ex:hasArtName ?artName .
  FILTER(CONTAINS(STR(?label), "文彭"))
}
LIMIT 20
```

## 示例 3：查询生卒年

问题：
`文彭的生卒年是什么？`

SPARQL：

```sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX ex: <http://example.org/kg/>

SELECT ?person ?label ?birthYear ?deathYear
WHERE {
  ?person rdfs:label ?label .
  OPTIONAL { ?person ex:birthYear ?birthYear . }
  OPTIONAL { ?person ex:deathYear ?deathYear . }
  FILTER(CONTAINS(STR(?label), "文彭"))
}
LIMIT 20
```

## 示例 4：查询两人关系

问题：
`文徵明与文彭是什么关系？`

SPARQL：

```sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?sourceLabel ?targetLabel ?relation ?relationLabel
WHERE {
  ?source rdfs:label ?sourceLabel .
  ?target rdfs:label ?targetLabel .
  ?source ?relation ?target .
  OPTIONAL { ?relation rdfs:label ?relationLabel . }
  FILTER(CONTAINS(STR(?sourceLabel), "文徵明") && CONTAINS(STR(?targetLabel), "文彭"))
}
LIMIT 20
```

## 示例 5：查询流派开创者

问题：
`谁开创了吴门印派？`

SPARQL：

```sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX ex: <http://example.org/kg/>

SELECT ?founder ?founderLabel ?school ?schoolLabel
WHERE {
  ?founder ex:foundsSchool ?school ;
           rdfs:label ?founderLabel .
  ?school rdfs:label ?schoolLabel .
  FILTER(CONTAINS(STR(?schoolLabel), "吴门印派"))
}
LIMIT 20
```

## 说明

- 这里的 `ex:` 命名空间和属性名目前是成员 D 联调阶段使用的占位写法。
- 等成员 C 完成本体和 Turtle 定稿后，需要统一替换为最终类名、属性名和命名空间。
- 这些示例既可以直接放进提示词，也可以作为 LangGraph 中“SPARQL 生成节点”的参考样例。
