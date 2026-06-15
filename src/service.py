from __future__ import annotations

from .agent_tools import AgentToolbox, build_course_overview
from .config import AppConfig
from .graph_analysis import GraphAnalysisService
from .graph_store import GraphStore
from .llm_workflow_support import WorkflowLlmSupport
from .tools import QueryTools
from .workflow import QueryWorkflow


class AppService:
    def __init__(self, config: AppConfig):
        ttl_files = [config.schema_ttl, config.core_ttl, config.aligned_ttl]
        self.graph_store = GraphStore(ttl_files=ttl_files)
        self.tools = QueryTools(self.graph_store)
        self.graph_analysis = GraphAnalysisService(self.graph_store)
        self.agent_toolbox = AgentToolbox(self.tools)
        self.llm_support = WorkflowLlmSupport.from_config(config)
        self.workflow = QueryWorkflow(self.tools, llm_support=self.llm_support)

    def answer_question(self, question: str):
        return self.workflow.answer_question(question)

    def run_sparql(self, sparql: str):
        return self.tools.run_raw_sparql(sparql)

    def list_tools(self):
        return self.agent_toolbox.list_tools()

    def get_course_overview(self):
        return build_course_overview()

    def get_graph_analysis(self):
        return self.graph_analysis.build_overview()

    def get_graph_exploration(self, center: str = "", hop: int = 1, relation_types: list[str] | None = None):
        return self.graph_analysis.get_exploration_graph(
            center=center,
            hop=hop,
            relation_types=relation_types,
        )

    def get_person_detail(self, person_name: str):
        return self.graph_analysis.get_person_detail(person_name)

    def find_person_path(self, source_name: str, target_name: str):
        return self.graph_analysis.find_shortest_path(source_name, target_name)

    def get_runtime_status(self):
        llm_available = self.llm_support.available
        provider_name = self.llm_support.provider_name
        if not llm_available and provider_name == "disabled":
            provider_display = "未启用（请将 KG_AGENT_LLM_MODE 改为 openai）"
        else:
            provider_display = provider_name
        return {
            "llm_available": llm_available,
            "provider_name": provider_display,
            "reference_mode": bool(self.llm_support.reference_mode),
            "tool_calling_available": bool(self.workflow.tool_calling_workflow.available),
        }

    def set_reference_mode(self, enabled: bool):
        self.llm_support.reference_mode = bool(enabled)
        return self.get_runtime_status()
