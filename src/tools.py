from __future__ import annotations

from dataclasses import dataclass

from .graph_store import GraphStore


BASE_PREFIXES = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX yrz: <http://www.yinrenzhuan.org/ontology#>
"""

PERSON_ALIAS_MAP: dict[str, list[str]] = {
    "文征明": ["文征明", "文徵明", "征仲", "文氏"],
    "文徵明": ["文征明", "文徵明", "征仲", "文氏"],
    "征仲": ["文征明", "文徵明", "征仲"],
    "文氏": ["文征明", "文徵明", "征仲", "文氏"],
}

SCHOOL_ALIAS_MAP: dict[str, list[str]] = {
    "吴门": ["吴门", "吴门印派", "吴门派"],
    "吴门印派": ["吴门", "吴门印派", "吴门派"],
    "吴门派": ["吴门", "吴门印派", "吴门派"],
}


@dataclass
class ToolResult:
    name: str
    sparql: str
    rows: list[dict[str, str]]
    note: str = ""


class QueryTools:
    def __init__(self, graph_store: GraphStore):
        self.graph_store = graph_store

    def _normalize_terms(self, value: str, alias_map: dict[str, list[str]]) -> list[str]:
        base = value.strip()
        terms = [base]
        for alias in alias_map.get(base, []):
            if alias not in terms:
                terms.append(alias)
        return [term for term in terms if term]

    def _label_match_clause(self, label_var: str, terms: list[str]) -> str:
        comparisons: list[str] = []
        for term in terms:
            escaped = self._escape_literal(term)
            comparisons.append(
                f'CONTAINS(STR({label_var}), "{escaped}") || '
                f'CONTAINS("{escaped}", STR({label_var})) || '
                f'STR({label_var}) = "{escaped}"'
            )
        return " || ".join(f"({item})" for item in comparisons) if comparisons else "false"

    def _run(self, name: str, sparql: str, note: str) -> ToolResult:
        rows = self.graph_store.query(sparql)
        return ToolResult(name=name, sparql=sparql.strip(), rows=rows, note=note)

    def _escape_literal(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def _person_filter(self, person_name: str) -> str:
        terms = self._normalize_terms(person_name, PERSON_ALIAS_MAP)
        return f"FILTER({self._label_match_clause('?label', terms)})"

    def _school_filter(self, school_name: str) -> str:
        terms = self._normalize_terms(school_name, SCHOOL_ALIAS_MAP)
        return f"FILTER({self._label_match_clause('?schoolLabel', terms)})"

    def _candidate_people_block(self, person_name: str) -> str:
        return f"""
          {{
            SELECT DISTINCT ?person ?label
            WHERE {{
              ?person rdf:type yrz:Person ;
                      rdfs:label ?label .
              {self._person_filter(person_name)}
            }}
            LIMIT 30
          }}
        """

    def _candidate_person_subjects_block(self, person_name: str) -> str:
        return f"""
          {{
            SELECT DISTINCT ?person
            WHERE {{
              ?person rdf:type yrz:Person ;
                      rdfs:label ?label .
              {self._person_filter(person_name)}
            }}
            LIMIT 30
          }}
        """

    def _person_relation_query(
        self,
        relation_name: str,
        relation_type: str,
        value_var: str,
        label_var: str,
        alias_var: str,
    ) -> str:
        return f"""
        {BASE_PREFIXES}
        SELECT DISTINCT ?person ?label ?{value_var} ?{label_var} ?{alias_var}
        WHERE {{
          {self._candidate_people_block(relation_name)}
          ?relation rdf:type yrz:Relation ;
                    yrz:relationType yrz:{relation_type} ;
                    yrz:sourceEntity ?person ;
                    yrz:targetEntity ?{value_var} .
          OPTIONAL {{ ?{value_var} rdfs:label ?{label_var} . }}
          BIND(COALESCE(?{label_var}, STR(?{value_var})) AS ?{alias_var})
        }}
        LIMIT 30
        """

    def get_person_labels(self, person_name: str) -> ToolResult:
        person_name = self._escape_literal(person_name)
        sparql = f"""
        {BASE_PREFIXES}
        SELECT DISTINCT ?person ?label
        WHERE {{
          ?person rdf:type yrz:Person ;
                  rdfs:label ?label .
          FILTER(CONTAINS(STR(?label), "{person_name}"))
        }}
        LIMIT 20
        """
        return self._run(
            name="get_person_labels",
            sparql=sparql,
            note="根据当前本体结构查询人物候选实体。",
        )

    def get_courtesy_name(self, person_name: str) -> ToolResult:
        person_name = self._escape_literal(person_name)
        sparql = self._person_relation_query(
            relation_name=person_name,
            relation_type="hasCourtesyName",
            value_var="courtesyNode",
            label_var="courtesyLabel",
            alias_var="courtesyName",
        )
        return self._run(
            name="get_courtesy_name",
            sparql=sparql,
            note="当前按 core.ttl 的关系实例模型查询人物的字。",
        )

    def get_art_name(self, person_name: str) -> ToolResult:
        person_name = self._escape_literal(person_name)
        sparql = self._person_relation_query(
            relation_name=person_name,
            relation_type="hasArtName",
            value_var="artNode",
            label_var="artLabel",
            alias_var="artName",
        )
        return self._run(
            name="get_art_name",
            sparql=sparql,
            note="当前按 core.ttl 的关系实例模型查询人物的号。",
        )

    def get_birth_death(self, person_name: str) -> ToolResult:
        person_name = self._escape_literal(person_name)
        sparql = f"""
        {BASE_PREFIXES}
        SELECT ?person ?label ?birthYear ?deathYear
        WHERE {{
          {self._candidate_people_block(person_name)}

          OPTIONAL {{
            SELECT ?person (GROUP_CONCAT(DISTINCT ?birthItem; separator=" / ") AS ?birthYear)
            WHERE {{
              {self._candidate_person_subjects_block(person_name)}
              {{
                ?birthRelation rdf:type yrz:Relation ;
                               yrz:relationType yrz:bornIn ;
                               yrz:sourceEntity ?person ;
                               yrz:targetEntity ?birthNode .
                OPTIONAL {{ ?birthNode rdfs:label ?birthNodeLabel . }}
                BIND(COALESCE(?birthNodeLabel, STR(?birthNode)) AS ?birthItem)
              }}
              UNION
              {{
                ?person yrz:bornIn ?birthLiteral .
                FILTER(isLiteral(?birthLiteral))
                BIND(STR(?birthLiteral) AS ?birthItem)
              }}
            }}
            GROUP BY ?person
          }}

          OPTIONAL {{
            SELECT ?person (GROUP_CONCAT(DISTINCT ?deathItem; separator=" / ") AS ?deathYear)
            WHERE {{
              {self._candidate_person_subjects_block(person_name)}
              {{
                ?deathRelation rdf:type yrz:Relation ;
                               yrz:relationType yrz:diedIn ;
                               yrz:sourceEntity ?person ;
                               yrz:targetEntity ?deathNode .
                OPTIONAL {{ ?deathNode rdfs:label ?deathNodeLabel . }}
                BIND(COALESCE(?deathNodeLabel, STR(?deathNode)) AS ?deathItem)
              }}
              UNION
              {{
                ?person yrz:diedIn ?deathLiteral .
                FILTER(isLiteral(?deathLiteral))
                BIND(STR(?deathLiteral) AS ?deathItem)
              }}
            }}
            GROUP BY ?person
          }}
        }}
        LIMIT 20
        """
        return self._run(
            name="get_birth_death",
            sparql=sparql,
            note="生卒年查询同时兼容 core.ttl 的关系实例和 aligned.ttl 的外部补充年份字面量。",
        )

    def get_teacher_relations(self, person_name: str) -> ToolResult:
        person_name = self._escape_literal(person_name)
        sparql = f"""
        {BASE_PREFIXES}
        SELECT DISTINCT ?person ?label ?teacher ?teacherLabel
        WHERE {{
          {self._candidate_people_block(person_name)}
          ?relation rdf:type yrz:Relation ;
                    yrz:relationType yrz:hasTeacher ;
                    yrz:sourceEntity ?person ;
                    yrz:targetEntity ?teacher .
          OPTIONAL {{ ?teacher rdfs:label ?teacherLabelRaw . }}
          BIND(COALESCE(?teacherLabelRaw, STR(?teacher)) AS ?teacherLabel)
        }}
        LIMIT 30
        """
        return self._run(
            name="get_teacher_relations",
            sparql=sparql,
            note="当前按关系实例模型查询人物师承关系。",
        )

    def get_family_relations(self, person_name: str) -> ToolResult:
        person_name = self._escape_literal(person_name)
        sparql = f"""
        {BASE_PREFIXES}
        SELECT DISTINCT ?person ?label ?relative ?relativeLabel ?relationType
        WHERE {{
          {self._candidate_people_block(person_name)}
          {{
            ?relation rdf:type yrz:Relation ;
                      yrz:relationType yrz:fatherOf ;
                      yrz:sourceEntity ?person ;
                      yrz:targetEntity ?relative .
            BIND("子女" AS ?relationType)
          }}
          UNION
          {{
            ?relation rdf:type yrz:Relation ;
                      yrz:relationType yrz:fatherOf ;
                      yrz:sourceEntity ?relative ;
                      yrz:targetEntity ?person .
            BIND("父亲" AS ?relationType)
          }}
          OPTIONAL {{ ?relative rdfs:label ?relativeLabelRaw . }}
          BIND(COALESCE(?relativeLabelRaw, STR(?relative)) AS ?relativeLabel)
        }}
        LIMIT 40
        """
        return self._run(
            name="get_family_relations",
            sparql=sparql,
            note="当前亲属查询基于 yrz:fatherOf 的关系实例，覆盖父亲和子女两个方向。",
        )

    def get_social_relations(self, person_name: str) -> ToolResult:
        person_name = self._escape_literal(person_name)
        sparql = f"""
        {BASE_PREFIXES}
        SELECT DISTINCT ?person ?label ?friend ?friendLabel
        WHERE {{
          {self._candidate_people_block(person_name)}
          {{
            ?relation rdf:type yrz:Relation ;
                      yrz:relationType yrz:hasFriend ;
                      yrz:sourceEntity ?person ;
                      yrz:targetEntity ?friend .
          }}
          UNION
          {{
            ?relation rdf:type yrz:Relation ;
                      yrz:relationType yrz:hasFriend ;
                      yrz:sourceEntity ?friend ;
                      yrz:targetEntity ?person .
          }}
          OPTIONAL {{ ?friend rdfs:label ?friendLabelRaw . }}
          BIND(COALESCE(?friendLabelRaw, STR(?friend)) AS ?friendLabel)
        }}
        LIMIT 30
        """
        return self._run(
            name="get_social_relations",
            sparql=sparql,
            note="当前按关系实例模型查询人物交游关系。",
        )

    def get_school_membership(self, person_name: str) -> ToolResult:
        person_name = self._escape_literal(person_name)
        sparql = f"""
        {BASE_PREFIXES}
        SELECT DISTINCT ?person ?label ?school ?schoolLabel
        WHERE {{
          {self._candidate_people_block(person_name)}
          ?relation rdf:type yrz:Relation ;
                    yrz:relationType yrz:belongsToSchool ;
                    yrz:sourceEntity ?person ;
                    yrz:targetEntity ?school .
          OPTIONAL {{ ?school rdfs:label ?schoolLabelRaw . }}
          BIND(COALESCE(?schoolLabelRaw, STR(?school)) AS ?schoolLabel)
        }}
        LIMIT 30
        """
        return self._run(
            name="get_school_membership",
            sparql=sparql,
            note="当前按关系实例模型查询人物所属流派。",
        )

    def get_school_founder(self, school_name: str) -> ToolResult:
        school_name = self._escape_literal(school_name)
        sparql = f"""
        {BASE_PREFIXES}
        SELECT DISTINCT ?founder ?founderLabel ?school ?schoolLabel
        WHERE {{
          {{
            SELECT DISTINCT ?school ?schoolLabel
            WHERE {{
              ?relation rdf:type yrz:Relation ;
                        yrz:relationType yrz:foundsSchool ;
                        yrz:targetEntity ?school .
              ?school rdfs:label ?schoolLabel .
              {self._school_filter(school_name)}
            }}
            LIMIT 30
          }}
          ?relation rdf:type yrz:Relation ;
                    yrz:relationType yrz:foundsSchool ;
                    yrz:sourceEntity ?founder ;
                    yrz:targetEntity ?school .
          OPTIONAL {{ ?founder rdfs:label ?founderLabelRaw . }}
          BIND(COALESCE(?founderLabelRaw, STR(?founder)) AS ?founderLabel)
        }}
        LIMIT 20
        """
        return self._run(
            name="get_school_founder",
            sparql=sparql,
            note="当前按关系实例模型查询流派开创者，并兼容“吴门”与“吴门印派”这类部分匹配。",
        )

    def get_school_representatives(self, school_name: str) -> ToolResult:
        school_name = self._escape_literal(school_name)
        sparql = f"""
        {BASE_PREFIXES}
        SELECT DISTINCT ?person ?personLabel ?school ?schoolLabel ?role
        WHERE {{
          {{
            SELECT DISTINCT ?school ?schoolLabel
            WHERE {{
              {{
                ?seedRelation rdf:type yrz:Relation ;
                              yrz:relationType yrz:belongsToSchool ;
                              yrz:targetEntity ?school .
              }}
              UNION
              {{
                ?seedRelation rdf:type yrz:Relation ;
                              yrz:relationType yrz:foundsSchool ;
                              yrz:targetEntity ?school .
              }}
              ?school rdfs:label ?schoolLabel .
              {self._school_filter(school_name)}
            }}
            LIMIT 30
          }}
          {{
            ?relation rdf:type yrz:Relation ;
                      yrz:relationType yrz:belongsToSchool ;
                      yrz:sourceEntity ?person ;
                      yrz:targetEntity ?school .
            BIND("成员" AS ?role)
          }}
          UNION
          {{
            ?relation rdf:type yrz:Relation ;
                      yrz:relationType yrz:foundsSchool ;
                      yrz:sourceEntity ?person ;
                      yrz:targetEntity ?school .
            BIND("开创者" AS ?role)
          }}
          OPTIONAL {{ ?person rdfs:label ?personLabelRaw . }}
          BIND(COALESCE(?personLabelRaw, STR(?person)) AS ?personLabel)
        }}
        LIMIT 60
        """
        return self._run(
            name="get_school_representatives",
            sparql=sparql,
            note="当前按关系实例模型查询流派成员与开创者，用于回答流派代表人物、主要成员等问题。",
        )

    def get_pair_relations(self, person_a: str, person_b: str) -> ToolResult:
        person_a = self._escape_literal(person_a)
        person_b = self._escape_literal(person_b)
        source_clause = self._label_match_clause("?sourceLabel", self._normalize_terms(person_a, PERSON_ALIAS_MAP))
        target_clause = self._label_match_clause("?targetLabel", self._normalize_terms(person_b, PERSON_ALIAS_MAP))
        sparql = f"""
        {BASE_PREFIXES}
        SELECT DISTINCT ?sourceLabel ?targetLabel ?relation ?relationLabel ?direction
        WHERE {{
          {{
            SELECT DISTINCT ?source ?sourceLabel
            WHERE {{
              ?source rdf:type yrz:Person ;
                      rdfs:label ?sourceLabel .
              FILTER({source_clause})
            }}
            LIMIT 20
          }}
          {{
            SELECT DISTINCT ?target ?targetLabel
            WHERE {{
              ?target rdf:type yrz:Person ;
                      rdfs:label ?targetLabel .
              FILTER({target_clause})
            }}
            LIMIT 20
          }}
          {{
            ?relationFact rdf:type yrz:Relation ;
                          yrz:relationType ?relation ;
                          yrz:sourceEntity ?source ;
                          yrz:targetEntity ?target .
            OPTIONAL {{ ?relation rdfs:label ?relationLabel . }}
            BIND("正向" AS ?direction)
          }}
          UNION
          {{
            ?relationFact rdf:type yrz:Relation ;
                          yrz:relationType ?relation ;
                          yrz:sourceEntity ?target ;
                          yrz:targetEntity ?source .
            OPTIONAL {{ ?relation rdfs:label ?relationLabel . }}
            BIND("反向" AS ?direction)
          }}
        }}
        LIMIT 30
        """
        return self._run(
            name="get_pair_relations",
            sparql=sparql,
            note="当前通过关系实例查询两个人物之间的直接关系。",
        )

    def get_related_people(self, person_name: str) -> ToolResult:
        person_name = self._escape_literal(person_name)
        sparql = f"""
        {BASE_PREFIXES}
        SELECT DISTINCT ?person ?label ?related ?relatedLabel ?relation ?relationLabel ?direction
        WHERE {{
          {self._candidate_people_block(person_name)}
          {{
            ?related rdf:type yrz:Person ;
                     rdfs:label ?relatedLabelRaw .
            ?relationFact rdf:type yrz:Relation ;
                          yrz:relationType ?relation ;
                          yrz:sourceEntity ?person ;
                          yrz:targetEntity ?related .
            OPTIONAL {{ ?relation rdfs:label ?relationLabel . }}
            BIND("outgoing" AS ?direction)
          }}
          UNION
          {{
            ?related rdf:type yrz:Person ;
                     rdfs:label ?relatedLabelRaw .
            ?relationFact rdf:type yrz:Relation ;
                          yrz:relationType ?relation ;
                          yrz:sourceEntity ?related ;
                          yrz:targetEntity ?person .
            OPTIONAL {{ ?relation rdfs:label ?relationLabel . }}
            BIND("incoming" AS ?direction)
          }}
          BIND(COALESCE(?relatedLabelRaw, STR(?related)) AS ?relatedLabel)
        }}
        LIMIT 50
        """
        return self._run(
            name="get_related_people",
            sparql=sparql,
            note="当前按关系实例抓取人物关联人物，供前端关系网络面板直接消费。",
        )

    def get_courtesy_and_art_name(self, person_name: str) -> ToolResult:
        """同时查询人物的字和号"""
        person_name_escaped = self._escape_literal(person_name)

        sparql = f"""
        {BASE_PREFIXES}
        SELECT DISTINCT ?person ?label ?courtesyName ?artName
        WHERE {{
          {self._candidate_people_block(person_name_escaped)}

          OPTIONAL {{
            {{
              ?courtesyRelation rdf:type yrz:Relation ;
                                yrz:relationType yrz:hasCourtesyName ;
                                yrz:sourceEntity ?person ;
                                yrz:targetEntity ?courtesyNode .
              OPTIONAL {{ ?courtesyNode rdfs:label ?courtesyLabel . }}
              BIND(COALESCE(?courtesyLabel, STR(?courtesyNode)) AS ?courtesyName)
            }}
            UNION
            {{
              ?person yrz:courtesyName ?courtesyLiteral .
              BIND(STR(?courtesyLiteral) AS ?courtesyName)
            }}
          }}

          OPTIONAL {{
            {{
              ?artRelation rdf:type yrz:Relation ;
                           yrz:relationType yrz:hasArtName ;
                           yrz:sourceEntity ?person ;
                           yrz:targetEntity ?artNode .
              OPTIONAL {{ ?artNode rdfs:label ?artLabel . }}
              BIND(COALESCE(?artLabel, STR(?artNode)) AS ?artName)
            }}
            UNION
            {{
              ?person yrz:artName ?artLiteral .
              BIND(STR(?artLiteral) AS ?artName)
            }}
          }}
        }}
        LIMIT 20
        """
        return self._run(
            name="get_courtesy_and_art_name",
            sparql=sparql,
            note="当前同时兼容关系实例与直接属性两种写法查询人物的字和号。",
        )

    def get_classmates(self, person_name: str) -> ToolResult:
        """查询人物的师兄弟（同门）"""
        person_name = self._escape_literal(person_name)
        sparql = f"""
        {BASE_PREFIXES}
        SELECT DISTINCT ?person ?label ?classmate ?classmateLabel
        WHERE {{
          {self._candidate_people_block(person_name)}

          # 找到此人的老师
          ?relation1 rdf:type yrz:Relation ;
                     yrz:relationType yrz:hasTeacher ;
                     yrz:sourceEntity ?person ;
                     yrz:targetEntity ?teacher .

          # 找到同一个老师的其他学生（师兄弟）
          ?relation2 rdf:type yrz:Relation ;
                     yrz:relationType yrz:hasTeacher ;
                     yrz:sourceEntity ?classmate ;
                     yrz:targetEntity ?teacher .

          # 排除自己
          FILTER(?person != ?classmate)

          OPTIONAL {{ ?classmate rdfs:label ?classmateLabelRaw . }}
          BIND(COALESCE(?classmateLabelRaw, STR(?classmate)) AS ?classmateLabel)
        }}
        LIMIT 50
        """
        return self._run(
            name="get_classmates",
            sparql=sparql,
            note="当前按关系实例模型查询同门师兄弟：找到共同的老师，再找该老师的其他学生。",
        )

    def run_raw_sparql(self, sparql: str) -> ToolResult:
        rows = self.graph_store.query(sparql)
        return ToolResult(
            name="run_raw_sparql",
            sparql=sparql.strip(),
            rows=rows,
            note="手动执行高级 SPARQL 查询。",
        )
