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


@dataclass
class ToolResult:
    name: str
    sparql: str
    rows: list[dict[str, str]]
    note: str = ""


class QueryTools:
    def __init__(self, graph_store: GraphStore):
        self.graph_store = graph_store

    def _run(self, name: str, sparql: str, note: str) -> ToolResult:
        rows = self.graph_store.query(sparql)
        return ToolResult(name=name, sparql=sparql.strip(), rows=rows, note=note)

    def _escape_literal(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def _person_filter(self, person_name: str) -> str:
        return (
            f'FILTER(?label = "{person_name}" || '
            f'CONTAINS(STR(?label), "{person_name}") || '
            f'CONTAINS("{person_name}", STR(?label)))'
        )

    def _school_filter(self, school_name: str) -> str:
        return (
            f'FILTER(?schoolLabel = "{school_name}" || '
            f'CONTAINS(STR(?schoolLabel), "{school_name}") || '
            f'CONTAINS("{school_name}", STR(?schoolLabel)))'
        )

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
            note="按成员 C 的正式本体查询人物候选实体。",
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

    def get_pair_relations(self, person_a: str, person_b: str) -> ToolResult:
        person_a = self._escape_literal(person_a)
        person_b = self._escape_literal(person_b)
        sparql = f"""
        {BASE_PREFIXES}
        SELECT DISTINCT ?sourceLabel ?targetLabel ?relation ?relationLabel ?direction
        WHERE {{
          {{
            SELECT DISTINCT ?source ?sourceLabel
            WHERE {{
              ?source rdf:type yrz:Person ;
                      rdfs:label ?sourceLabel .
              FILTER(?sourceLabel = "{person_a}" || CONTAINS(STR(?sourceLabel), "{person_a}"))
            }}
            LIMIT 20
          }}
          {{
            SELECT DISTINCT ?target ?targetLabel
            WHERE {{
              ?target rdf:type yrz:Person ;
                      rdfs:label ?targetLabel .
              FILTER(?targetLabel = "{person_b}" || CONTAINS(STR(?targetLabel), "{person_b}"))
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

    def run_raw_sparql(self, sparql: str) -> ToolResult:
        rows = self.graph_store.query(sparql)
        return ToolResult(
            name="run_raw_sparql",
            sparql=sparql.strip(),
            rows=rows,
            note="手动执行高级 SPARQL 查询。",
        )
