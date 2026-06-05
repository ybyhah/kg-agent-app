from __future__ import annotations

from .config import AppConfig
from .graph_store import GraphStore
from .tools import QueryTools
from .workflow import QueryWorkflow


class AppService:
    def __init__(self, config: AppConfig):
        ttl_files = [config.schema_ttl, config.core_ttl, config.aligned_ttl]
        self.graph_store = GraphStore(ttl_files=ttl_files)
        self.tools = QueryTools(self.graph_store)
        self.workflow = QueryWorkflow(self.tools)

    def answer_question(self, question: str):
        return self.workflow.answer_question(question)

    def run_sparql(self, sparql: str):
        return self.tools.run_raw_sparql(sparql)
