from __future__ import annotations

import unittest

from kg_agent_app.src.fewshot_sparql import FewShotSparqlGenerator
from kg_agent_app.src.tools import QueryTools


class DummyGraphStore:
    def __init__(self):
        self.last_sparql = ""

    def query(self, sparql: str):
        self.last_sparql = sparql
        return []


class GraphQueryTemplateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.graph_store = DummyGraphStore()
        self.tools = QueryTools(self.graph_store)

    def test_courtesy_name_query_uses_relation_fact_model(self) -> None:
        self.tools.get_courtesy_name("文彭")
        sparql = self.graph_store.last_sparql
        self.assertIn("rdf:type yrz:Relation", sparql)
        self.assertIn("yrz:relationType yrz:hasCourtesyName", sparql)
        self.assertIn("yrz:sourceEntity ?person", sparql)
        self.assertIn("yrz:targetEntity ?courtesyNode", sparql)

    def test_art_name_query_uses_relation_fact_model(self) -> None:
        self.tools.get_art_name("文彭")
        sparql = self.graph_store.last_sparql
        self.assertIn("yrz:relationType yrz:hasArtName", sparql)
        self.assertIn("yrz:targetEntity ?artNode", sparql)

    def test_birth_death_query_supports_core_and_aligned_data(self) -> None:
        self.tools.get_birth_death("文彭")
        sparql = self.graph_store.last_sparql
        self.assertIn("yrz:relationType yrz:bornIn", sparql)
        self.assertIn("?person yrz:bornIn ?birthLiteral", sparql)
        self.assertIn("yrz:relationType yrz:diedIn", sparql)
        self.assertIn("?person yrz:diedIn ?deathLiteral", sparql)

    def test_pair_relation_query_uses_relation_fact_model(self) -> None:
        self.tools.get_pair_relations("文徵明", "文彭")
        sparql = self.graph_store.last_sparql
        self.assertIn("?relationFact rdf:type yrz:Relation", sparql)
        self.assertIn("yrz:relationType ?relation", sparql)
        self.assertIn("yrz:sourceEntity ?source", sparql)
        self.assertIn("yrz:targetEntity ?target", sparql)

    def test_school_founder_query_supports_partial_name_match(self) -> None:
        self.tools.get_school_founder("吴门印派")
        sparql = self.graph_store.last_sparql
        self.assertIn("yrz:relationType yrz:foundsSchool", sparql)
        self.assertIn('CONTAINS(STR(?schoolLabel), "吴门印派")', sparql)
        self.assertIn('CONTAINS("吴门印派", STR(?schoolLabel))', sparql)

    def test_fewshot_pair_relation_uses_relation_fact_model(self) -> None:
        generator = FewShotSparqlGenerator()
        draft = generator.try_generate("文徵明与文彭是什么关系？")
        self.assertIsNotNone(draft)
        sparql = draft.sparql
        self.assertIn("?relationFact rdf:type yrz:Relation", sparql)
        self.assertIn("yrz:relationType ?relation", sparql)

    def test_fewshot_birth_death_supports_literal_years(self) -> None:
        generator = FewShotSparqlGenerator()
        draft = generator.try_generate("文彭的生卒年是什么？")
        self.assertIsNotNone(draft)
        sparql = draft.sparql
        self.assertIn("?person yrz:bornIn ?birthLiteral", sparql)
        self.assertIn("?person yrz:diedIn ?deathLiteral", sparql)


if __name__ == "__main__":
    unittest.main()
