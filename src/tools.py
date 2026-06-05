from __future__ import annotations

from dataclasses import dataclass

from .graph_store import GraphStore


BASE_PREFIXES = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX ex: <http://example.org/kg/>
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

    def get_person_labels(self, person_name: str) -> ToolResult:
        sparql = f"""
        {BASE_PREFIXES}
        SELECT ?person ?label
        WHERE {{
          ?person rdfs:label ?label .
          FILTER(CONTAINS(STR(?label), "{person_name}"))
        }}
        LIMIT 20
        """
        return self._run(
            name="get_person_labels",
            sparql=sparql,
            note="当前是基础标签查询，后续可替换成更严格的人物实体定位工具。",
        )

    def get_courtesy_name(self, person_name: str) -> ToolResult:
        sparql = f"""
        {BASE_PREFIXES}
        SELECT ?person ?label ?courtesyName
        WHERE {{
          ?person rdfs:label ?label ;
                  ex:hasCourtesyName ?courtesyName .
          FILTER(CONTAINS(STR(?label), "{person_name}"))
        }}
        LIMIT 20
        """
        return self._run(
            name="get_courtesy_name",
            sparql=sparql,
            note="查询某人的字。当前使用占位属性 ex:hasCourtesyName，等成员 C 定稿后替换。",
        )

    def get_art_name(self, person_name: str) -> ToolResult:
        sparql = f"""
        {BASE_PREFIXES}
        SELECT ?person ?label ?artName
        WHERE {{
          ?person rdfs:label ?label ;
                  ex:hasArtName ?artName .
          FILTER(CONTAINS(STR(?label), "{person_name}"))
        }}
        LIMIT 20
        """
        return self._run(
            name="get_art_name",
            sparql=sparql,
            note="查询某人的号。当前使用占位属性 ex:hasArtName，等成员 C 定稿后替换。",
        )

    def get_birth_death(self, person_name: str) -> ToolResult:
        sparql = f"""
        {BASE_PREFIXES}
        SELECT ?person ?label ?birthYear ?deathYear
        WHERE {{
          ?person rdfs:label ?label .
          OPTIONAL {{ ?person ex:birthYear ?birthYear . }}
          OPTIONAL {{ ?person ex:deathYear ?deathYear . }}
          FILTER(CONTAINS(STR(?label), "{person_name}"))
        }}
        LIMIT 20
        """
        return self._run(
            name="get_birth_death",
            sparql=sparql,
            note="查询某人的生卒年。当前使用占位属性 ex:birthYear 和 ex:deathYear。",
        )

    def get_teacher_relations(self, person_name: str) -> ToolResult:
        sparql = f"""
        {BASE_PREFIXES}
        SELECT ?person ?label ?teacher ?teacherLabel
        WHERE {{
          ?person rdfs:label ?label ;
                  ex:hasTeacher ?teacher .
          ?teacher rdfs:label ?teacherLabel .
          FILTER(CONTAINS(STR(?label), "{person_name}"))
        }}
        LIMIT 30
        """
        return self._run(
            name="get_teacher_relations",
            sparql=sparql,
            note="查询某人的师承关系。当前使用占位属性 ex:hasTeacher。",
        )

    def get_family_relations(self, person_name: str) -> ToolResult:
        sparql = f"""
        {BASE_PREFIXES}
        SELECT ?person ?label ?relative ?relativeLabel ?relationType
        WHERE {{
          ?person rdfs:label ?label .
          ?person ex:hasRelative ?relative .
          ?relative rdfs:label ?relativeLabel .
          OPTIONAL {{ ?person ex:relativeRelationType ?relationType . }}
          FILTER(CONTAINS(STR(?label), "{person_name}"))
        }}
        LIMIT 30
        """
        return self._run(
            name="get_family_relations",
            sparql=sparql,
            note="查询某人的亲属关系。当前使用占位属性 ex:hasRelative 和 ex:relativeRelationType。",
        )

    def get_social_relations(self, person_name: str) -> ToolResult:
        sparql = f"""
        {BASE_PREFIXES}
        SELECT ?person ?label ?friend ?friendLabel
        WHERE {{
          ?person rdfs:label ?label ;
                  ex:hasFriend ?friend .
          ?friend rdfs:label ?friendLabel .
          FILTER(CONTAINS(STR(?label), "{person_name}"))
        }}
        LIMIT 30
        """
        return self._run(
            name="get_social_relations",
            sparql=sparql,
            note="查询某人的交游关系。当前使用占位属性 ex:hasFriend。",
        )

    def get_school_membership(self, person_name: str) -> ToolResult:
        sparql = f"""
        {BASE_PREFIXES}
        SELECT ?person ?label ?school ?schoolLabel
        WHERE {{
          ?person rdfs:label ?label ;
                  ex:belongsToSchool ?school .
          ?school rdfs:label ?schoolLabel .
          FILTER(CONTAINS(STR(?label), "{person_name}"))
        }}
        LIMIT 30
        """
        return self._run(
            name="get_school_membership",
            sparql=sparql,
            note="查询某人的流派归属。当前使用占位属性 ex:belongsToSchool。",
        )

    def get_school_founder(self, school_name: str) -> ToolResult:
        sparql = f"""
        {BASE_PREFIXES}
        SELECT ?founder ?founderLabel ?school ?schoolLabel
        WHERE {{
          ?founder ex:foundsSchool ?school ;
                   rdfs:label ?founderLabel .
          ?school rdfs:label ?schoolLabel .
          FILTER(CONTAINS(STR(?schoolLabel), "{school_name}"))
        }}
        LIMIT 20
        """
        return self._run(
            name="get_school_founder",
            sparql=sparql,
            note="查询某流派的开创者。当前使用占位属性 ex:foundsSchool。",
        )

    def get_related_people(self, person_name: str) -> ToolResult:
        sparql = f"""
        {BASE_PREFIXES}
        SELECT DISTINCT ?person ?label ?related ?relatedLabel
        WHERE {{
          ?person rdfs:label ?label .
          ?person ?relation ?related .
          ?related rdfs:label ?relatedLabel .
          FILTER(CONTAINS(STR(?label), "{person_name}"))
        }}
        LIMIT 50
        """
        return self._run(
            name="get_related_people",
            sparql=sparql,
            note="查询某人的关联人物，适合后续做人物关系网络或路径分析。",
        )

    def run_raw_sparql(self, sparql: str) -> ToolResult:
        rows = self.graph_store.query(sparql)
        return ToolResult(
            name="run_raw_sparql",
            sparql=sparql.strip(),
            rows=rows,
            note="手动执行高级 SPARQL 查询。",
        )
