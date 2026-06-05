from __future__ import annotations

from dataclasses import dataclass

from .graph_store import GraphStore


@dataclass
class ToolResult:
    name: str
    sparql: str
    rows: list[dict[str, str]]
    note: str = ""


class QueryTools:
    def __init__(self, graph_store: GraphStore):
        self.graph_store = graph_store

    def get_person_labels(self, person_name: str) -> ToolResult:
        sparql = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?person ?label
        WHERE {{
          ?person rdfs:label ?label .
          FILTER(CONTAINS(STR(?label), "{person_name}"))
        }}
        LIMIT 20
        """
        rows = self.graph_store.query(sparql)
        return ToolResult(
            name="get_person_labels",
            sparql=sparql.strip(),
            rows=rows,
            note="Basic label lookup. Replace with schema-aware person query after member C finalizes ontology.",
        )

    def run_raw_sparql(self, sparql: str) -> ToolResult:
        rows = self.graph_store.query(sparql)
        return ToolResult(name="run_raw_sparql", sparql=sparql.strip(), rows=rows)
