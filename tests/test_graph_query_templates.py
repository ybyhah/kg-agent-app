from __future__ import annotations

import unittest

from src.fewshot_sparql import FewShotSparqlGenerator
from src.tools import QueryTools
from src.workflow import QueryWorkflow


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

    def test_art_name_query_uses_relation_fact_model(self) -> None:
        self.tools.get_art_name("文彭")
        sparql = self.graph_store.last_sparql
        self.assertIn("yrz:relationType yrz:hasArtName", sparql)
        self.assertIn("yrz:targetEntity ?artNode", sparql)

    def test_birth_death_query_supports_literal_years(self) -> None:
        self.tools.get_birth_death("文彭")
        sparql = self.graph_store.last_sparql
        self.assertIn("?person yrz:bornIn ?birthLiteral", sparql)
        self.assertIn("?person yrz:diedIn ?deathLiteral", sparql)

    def test_pair_relation_query_uses_relation_fact_model(self) -> None:
        self.tools.get_pair_relations("文徵明", "文彭")
        sparql = self.graph_store.last_sparql
        self.assertIn("?relationFact rdf:type yrz:Relation", sparql)
        self.assertIn("yrz:sourceEntity ?source", sparql)
        self.assertIn("yrz:targetEntity ?target", sparql)

    def test_school_founder_query_supports_partial_name_match(self) -> None:
        self.tools.get_school_founder("吴门印派")
        sparql = self.graph_store.last_sparql
        self.assertIn("yrz:relationType yrz:foundsSchool", sparql)
        self.assertIn('CONTAINS(STR(?schoolLabel), "吴门印派")', sparql)
        self.assertIn("yrz:targetEntity ?school", sparql)

    def test_school_representatives_query_uses_membership_and_founder_relations(self) -> None:
        self.tools.get_school_representatives("吴门印派")
        sparql = self.graph_store.last_sparql
        self.assertIn("yrz:relationType yrz:belongsToSchool", sparql)
        self.assertIn("yrz:relationType yrz:foundsSchool", sparql)
        self.assertIn("?seedRelation rdf:type yrz:Relation", sparql)
        self.assertIn("yrz:targetEntity ?school", sparql)

    def test_fewshot_pair_relation_query_can_be_generated(self) -> None:
        generator = FewShotSparqlGenerator()
        draft = generator.try_generate("文徵明与文彭是什么关系？")
        self.assertIsNotNone(draft)
        assert draft is not None
        self.assertIn("?relationFact rdf:type yrz:Relation", draft.sparql)

    def test_workflow_normalizes_person_alias_before_generation(self) -> None:
        workflow = QueryWorkflow(self.tools)
        normalized = workflow._normalize_question_for_generation("征仲与文彭是什么关系？")
        self.assertIn("文徵明", normalized)

    def test_workflow_normalizes_school_alias_before_generation(self) -> None:
        workflow = QueryWorkflow(self.tools)
        normalized = workflow._normalize_question_for_generation("谁开创了吴门印派？")
        self.assertIn("吴门", normalized)


if __name__ == "__main__":
    unittest.main()
