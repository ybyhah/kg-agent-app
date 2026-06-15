from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .tools import QueryTools, ToolResult


@dataclass(frozen=True)
class CourseReference:
    pdf: str
    page: int
    topic: str


@dataclass(frozen=True)
class ToolParameter:
    name: str
    type: str
    description: str
    required: bool = True
    example: str = ""


@dataclass(frozen=True)
class ToolReturnField:
    name: str
    type: str
    description: str


@dataclass(frozen=True)
class AgentToolDefinition:
    name: str
    display_name: str
    description: str
    workflow_role: str
    parameters: list[ToolParameter]
    return_fields: list[ToolReturnField]
    sample_kwargs: dict[str, str]
    course_references: list[CourseReference]

    def input_schema(self) -> dict[str, Any]:
        properties: dict[str, Any] = {}
        required: list[str] = []
        for parameter in self.parameters:
            properties[parameter.name] = {
                "type": parameter.type,
                "description": parameter.description,
            }
            if parameter.example:
                properties[parameter.name]["example"] = parameter.example
            if parameter.required:
                required.append(parameter.name)
        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }


COURSE_OVERVIEW: list[CourseReference] = [
    CourseReference("2026新1.pdf", 17, "课程总览中明确包含 Knowledge Extraction、Langchain、User Query Parsing"),
    CourseReference("2026新1.pdf", 18, "课程总览中明确包含 RDF、Turtle、RDFS"),
    CourseReference("2026新1.pdf", 19, "课程总览中明确包含 SPARQL、Knowledge Graph Programming、KG Agent"),
    CourseReference("2026新1.pdf", 22, "项目展示模块包含 Entity Linking、Langgraph、Web Interface and Visualization"),
    CourseReference("2026新2.pdf", 57, "LangChain 中模型可发起 tool calls"),
    CourseReference("2026新2.pdf", 58, "Tool Message 用于把工具执行结果返回给模型"),
    CourseReference("2026新2.pdf", 60, "Structured Output 使用 Pydantic schema 约束输出"),
    CourseReference("2026新2.pdf", 65, "User Query Parsing 是 KBQA 的核心挑战"),
    CourseReference("2026新2.pdf", 68, "Semantic parser 将自然语言转为可执行 SPARQL"),
    CourseReference("2026新2.pdf", 80, "课程练习要求用 LangChain 解析用户问句并抽取命名实体"),
    CourseReference("2026新3.pdf", 2, "RDF / Turtle / RDFS 是图谱存储与建模基础"),
    CourseReference("2026新4.pdf", 2, "Lecture 4 主题是 Querying RDFS with SPARQL"),
    CourseReference("2026新4.pdf", 155, "工具需要有清晰的输入输出并可被模型调用"),
    CourseReference("2026新4.pdf", 157, "@tool 的 docstring 和 type hints 决定工具说明与输入 schema"),
    CourseReference("2026新4.pdf", 158, "工具需要绑定给模型后才能被工作流使用"),
    CourseReference("2026新4.pdf", 159, "ToolNode 负责在 LangGraph 工作流中执行工具"),
    CourseReference("2026新4.pdf", 160, "KG-agent 组件包括 State、Nodes、Edges、Tools、Workflow"),
    CourseReference("2026新4.pdf", 161, "大项目要求用 LLM agent 解析问句并借助工具与 SPARQL 搜索答案"),
]


TOOL_DEFINITIONS: list[AgentToolDefinition] = [
    AgentToolDefinition(
        name="get_person_labels",
        display_name="查询人物候选",
        description="根据人物名称或别名查找图谱中的候选人物实体，适合作为问句解析后的第一步实体确认工具。",
        workflow_role="用户问句解析后先确认人物实体，供后续工具或 SPARQL 查询继续使用。",
        parameters=[
            ToolParameter("person_name", "string", "待查询的人物名称、字号或别名。", example="文徵明"),
        ],
        return_fields=[
            ToolReturnField("person", "string", "人物实体 URI。"),
            ToolReturnField("label", "string", "人物实体标签。"),
        ],
        sample_kwargs={"person_name": "文彭"},
        course_references=[
            CourseReference("2026新2.pdf", 80, "问句解析阶段需要先抽取用户问句中的实体"),
            CourseReference("2026新4.pdf", 155, "工具应提供明确输入输出，供模型决定是否调用"),
            CourseReference("2026新4.pdf", 157, "工具说明和参数类型需要显式写清"),
        ],
    ),
    AgentToolDefinition(
        name="get_courtesy_name",
        display_name="查询人物字",
        description="查询某位印人的字，对应人物属性类高频问题。",
        workflow_role="当用户询问某人的字时直接调用，提高比自由生成更稳定的准确率。",
        parameters=[
            ToolParameter("person_name", "string", "待查询的人物姓名。", example="文彭"),
        ],
        return_fields=[
            ToolReturnField("person", "string", "人物实体 URI。"),
            ToolReturnField("label", "string", "人物标签。"),
            ToolReturnField("courtesyName", "string", "人物的字。"),
        ],
        sample_kwargs={"person_name": "文彭"},
        course_references=[
            CourseReference("2026新2.pdf", 57, "模型可通过 tool call 调用结构化查询工具"),
            CourseReference("2026新2.pdf", 60, "工具输出应可映射为结构化字段"),
            CourseReference("2026新4.pdf", 155, "工具需要明确的输入输出定义"),
            CourseReference("2026新4.pdf", 160, "KG-agent 组件中 Tools 是核心部分"),
        ],
    ),
    AgentToolDefinition(
        name="get_art_name",
        display_name="查询人物号",
        description="查询某位印人的号，对应人物属性类高频问题。",
        workflow_role="当用户询问某人的号时直接调用。",
        parameters=[
            ToolParameter("person_name", "string", "待查询的人物姓名。", example="文彭"),
        ],
        return_fields=[
            ToolReturnField("person", "string", "人物实体 URI。"),
            ToolReturnField("label", "string", "人物标签。"),
            ToolReturnField("artName", "string", "人物的号。"),
        ],
        sample_kwargs={"person_name": "文彭"},
        course_references=[
            CourseReference("2026新2.pdf", 57, "工具调用用于回答结构清晰的问题"),
            CourseReference("2026新2.pdf", 60, "输出需符合 schema 以便后续解析"),
            CourseReference("2026新4.pdf", 155, "工具输入输出要清晰"),
        ],
    ),
    AgentToolDefinition(
        name="get_birth_death",
        display_name="查询生卒年",
        description="查询人物生卒年，兼容本地图谱与对齐后补充的外部年份信息。",
        workflow_role="用于回答人物基本信息问题，也是实体消歧的重要辅助工具。",
        parameters=[
            ToolParameter("person_name", "string", "待查询的人物姓名。", example="文彭"),
        ],
        return_fields=[
            ToolReturnField("person", "string", "人物实体 URI。"),
            ToolReturnField("label", "string", "人物标签。"),
            ToolReturnField("birthYear", "string", "出生年份或出生时间信息。"),
            ToolReturnField("deathYear", "string", "去世年份或去世时间信息。"),
        ],
        sample_kwargs={"person_name": "文彭"},
        course_references=[
            CourseReference("2026新2.pdf", 23, "实体消歧可借助时间上下文"),
            CourseReference("2026新2.pdf", 60, "结构化输出适合后续流程复用"),
            CourseReference("2026新4.pdf", 155, "工具可查询外部数据库或本地图谱中的结构化事实"),
        ],
    ),
    AgentToolDefinition(
        name="get_teacher_relations",
        display_name="查询师承关系",
        description="查询某位印人的师承对象。",
        workflow_role="用于关系问答和关系网络构图。",
        parameters=[
            ToolParameter("person_name", "string", "待查询的人物姓名。", example="文彭"),
        ],
        return_fields=[
            ToolReturnField("person", "string", "人物实体 URI。"),
            ToolReturnField("label", "string", "人物标签。"),
            ToolReturnField("teacher", "string", "师承对象 URI。"),
            ToolReturnField("teacherLabel", "string", "师承对象标签。"),
        ],
        sample_kwargs={"person_name": "文彭"},
        course_references=[
            CourseReference("2026新2.pdf", 25, "Relation Extraction 对应固定关系类型抽取"),
            CourseReference("2026新4.pdf", 155, "工具封装可以把复杂查询能力暴露给模型"),
            CourseReference("2026新4.pdf", 161, "最终项目要用工具搜索答案"),
        ],
    ),
    AgentToolDefinition(
        name="get_family_relations",
        display_name="查询亲属关系",
        description="查询人物的父亲或子女等亲属关系。",
        workflow_role="用于人物关系问答与人物网络展示。",
        parameters=[
            ToolParameter("person_name", "string", "待查询的人物姓名。", example="文彭"),
        ],
        return_fields=[
            ToolReturnField("person", "string", "人物实体 URI。"),
            ToolReturnField("label", "string", "人物标签。"),
            ToolReturnField("relative", "string", "亲属实体 URI。"),
            ToolReturnField("relativeLabel", "string", "亲属标签。"),
            ToolReturnField("relationType", "string", "关系方向，如父亲或子女。"),
        ],
        sample_kwargs={"person_name": "文彭"},
        course_references=[
            CourseReference("2026新2.pdf", 25, "Relation Extraction 对应固定 schema 的关系分类"),
            CourseReference("2026新2.pdf", 68, "问句解析后可转为执行查询"),
            CourseReference("2026新4.pdf", 155, "工具具备明确定义输入输出"),
        ],
    ),
    AgentToolDefinition(
        name="get_social_relations",
        display_name="查询交游关系",
        description="查询人物的交游圈和朋友关系。",
        workflow_role="用于交游问题和关系网络可视化。",
        parameters=[
            ToolParameter("person_name", "string", "待查询的人物姓名。", example="文彭"),
        ],
        return_fields=[
            ToolReturnField("person", "string", "人物实体 URI。"),
            ToolReturnField("label", "string", "人物标签。"),
            ToolReturnField("friend", "string", "交游对象 URI。"),
            ToolReturnField("friendLabel", "string", "交游对象标签。"),
        ],
        sample_kwargs={"person_name": "文彭"},
        course_references=[
            CourseReference("2026新2.pdf", 25, "关系抽取结果可按预定义关系类型组织"),
            CourseReference("2026新4.pdf", 160, "KG-agent 中工具层负责调用图谱能力"),
            CourseReference("2026新4.pdf", 161, "项目要求结合工具和图谱搜索答案"),
        ],
    ),
    AgentToolDefinition(
        name="get_school_membership",
        display_name="查询所属流派",
        description="查询人物所属流派或印风流派。",
        workflow_role="用于人物所属流派问答，以及布尔型流派判断的基础工具。",
        parameters=[
            ToolParameter("person_name", "string", "待查询的人物姓名。", example="文彭"),
        ],
        return_fields=[
            ToolReturnField("person", "string", "人物实体 URI。"),
            ToolReturnField("label", "string", "人物标签。"),
            ToolReturnField("school", "string", "流派实体 URI。"),
            ToolReturnField("schoolLabel", "string", "流派标签。"),
        ],
        sample_kwargs={"person_name": "文彭"},
        course_references=[
            CourseReference("2026新2.pdf", 65, "问句解析需要理解复杂问题中的关系槽位"),
            CourseReference("2026新4.pdf", 155, "工具可以查询外部数据库或图数据库"),
            CourseReference("2026新4.pdf", 160, "Tools 是 KG-agent 组件之一"),
        ],
    ),
    AgentToolDefinition(
        name="get_school_founder",
        display_name="查询流派开创者",
        description="查询某个流派的开创者，并支持部分匹配与别名匹配。",
        workflow_role="用于流派问题、演示固定工具与复杂问句解析。",
        parameters=[
            ToolParameter("school_name", "string", "待查询的流派名称。", example="吴门印派"),
        ],
        return_fields=[
            ToolReturnField("founder", "string", "开创者实体 URI。"),
            ToolReturnField("founderLabel", "string", "开创者标签。"),
            ToolReturnField("school", "string", "流派实体 URI。"),
            ToolReturnField("schoolLabel", "string", "流派标签。"),
        ],
        sample_kwargs={"school_name": "吴门印派"},
        course_references=[
            CourseReference("2026新2.pdf", 68, "自然语言问句可被转换为可执行查询"),
            CourseReference("2026新4.pdf", 155, "工具调用适合明确查询目标的场景"),
            CourseReference("2026新4.pdf", 161, "项目要求工具与 SPARQL 协同搜索答案"),
        ],
    ),
    AgentToolDefinition(
        name="get_pair_relations",
        display_name="查询两人关系",
        description="查询两个人物之间的直接关系，适合回答父子、师承、交游等直接关系问题。",
        workflow_role="用于复杂关系问句的固定工具兜底。",
        parameters=[
            ToolParameter("person_a", "string", "第一个人物名称。", example="文徵明"),
            ToolParameter("person_b", "string", "第二个人物名称。", example="文彭"),
        ],
        return_fields=[
            ToolReturnField("sourceLabel", "string", "源人物标签。"),
            ToolReturnField("targetLabel", "string", "目标人物标签。"),
            ToolReturnField("relation", "string", "关系 URI。"),
            ToolReturnField("relationLabel", "string", "关系标签。"),
            ToolReturnField("direction", "string", "关系方向。"),
        ],
        sample_kwargs={"person_a": "文徵明", "person_b": "文彭"},
        course_references=[
            CourseReference("2026新2.pdf", 25, "关系抽取后的知识可进入固定关系查询"),
            CourseReference("2026新2.pdf", 68, "Semantic parser 最终要落到可执行查询"),
            CourseReference("2026新4.pdf", 155, "工具通过明确参数支持模型调用"),
        ],
    ),
    AgentToolDefinition(
        name="get_related_people",
        display_name="查询关联人物网络",
        description="抓取某位人物的直接关联人物，供前端关系网络面板使用。",
        workflow_role="服务于人物关系网络可视化与答辩展示。",
        parameters=[
            ToolParameter("person_name", "string", "待查询的人物姓名。", example="文彭"),
        ],
        return_fields=[
            ToolReturnField("person", "string", "中心人物 URI。"),
            ToolReturnField("label", "string", "中心人物标签。"),
            ToolReturnField("related", "string", "关联人物 URI。"),
            ToolReturnField("relatedLabel", "string", "关联人物标签。"),
            ToolReturnField("relation", "string", "关系 URI。"),
            ToolReturnField("relationLabel", "string", "关系标签。"),
            ToolReturnField("direction", "string", "关联方向。"),
        ],
        sample_kwargs={"person_name": "文彭"},
        course_references=[
            CourseReference("2026新1.pdf", 22, "项目展示包含 Web Interface and Visualization"),
            CourseReference("2026新4.pdf", 160, "KG-agent 组件包括 Tools 和 Workflow"),
            CourseReference("2026新4.pdf", 161, "项目要求漂亮展示结果"),
        ],
    ),
    AgentToolDefinition(
        name="run_raw_sparql",
        display_name="执行高级 SPARQL",
        description="直接执行自定义 SPARQL 语句，适合高级查询面板和 few-shot SPARQL 生成结果落地执行。",
        workflow_role="当固定工具不足时，由模型或用户提供 SPARQL 并执行。",
        parameters=[
            ToolParameter("sparql", "string", "完整的 SPARQL 查询语句。", example="SELECT ?person ?label WHERE { ?person rdfs:label ?label . } LIMIT 10"),
        ],
        return_fields=[
            ToolReturnField("rows", "array", "SPARQL 查询返回的结果行列表。"),
        ],
        sample_kwargs={"sparql": "SELECT ?person ?label WHERE { ?person rdfs:label ?label . } LIMIT 10"},
        course_references=[
            CourseReference("2026新2.pdf", 68, "自然语言最终可以转为可执行 SPARQL"),
            CourseReference("2026新3.pdf", 2, "RDF/Turtle 是 SPARQL 查询的底层数据格式"),
            CourseReference("2026新4.pdf", 2, "Lecture 4 核心即 SPARQL 查询"),
            CourseReference("2026新4.pdf", 159, "ToolNode 适合执行工具并把结果回传给工作流"),
        ],
    ),
]


class _CatalogGraphStore:
    def query(self, sparql: str) -> list[dict[str, str]]:
        return []


class AgentToolbox:
    def __init__(self, query_tools: QueryTools):
        self.query_tools = query_tools
        self._definitions = {definition.name: definition for definition in TOOL_DEFINITIONS}
        self._invokers = {
            "get_person_labels": self.get_person_labels,
            "get_courtesy_name": self.get_courtesy_name,
            "get_art_name": self.get_art_name,
            "get_birth_death": self.get_birth_death,
            "get_teacher_relations": self.get_teacher_relations,
            "get_family_relations": self.get_family_relations,
            "get_social_relations": self.get_social_relations,
            "get_school_membership": self.get_school_membership,
            "get_school_founder": self.get_school_founder,
            "get_pair_relations": self.get_pair_relations,
            "get_related_people": self.get_related_people,
            "run_raw_sparql": self.run_raw_sparql,
        }

    def list_tools(self) -> list[dict[str, Any]]:
        return build_tool_catalog()

    def invoke(self, tool_name: str, **kwargs: str) -> ToolResult:
        if tool_name not in self._invokers:
            raise KeyError(f"未注册的工具：{tool_name}")
        return self._invokers[tool_name](**kwargs)

    def get_person_labels(self, person_name: str) -> ToolResult:
        """查询人物候选实体。"""
        return self.query_tools.get_person_labels(person_name)

    def get_courtesy_name(self, person_name: str) -> ToolResult:
        """查询人物的字。"""
        return self.query_tools.get_courtesy_name(person_name)

    def get_art_name(self, person_name: str) -> ToolResult:
        """查询人物的号。"""
        return self.query_tools.get_art_name(person_name)

    def get_birth_death(self, person_name: str) -> ToolResult:
        """查询人物生卒年。"""
        return self.query_tools.get_birth_death(person_name)

    def get_teacher_relations(self, person_name: str) -> ToolResult:
        """查询人物师承关系。"""
        return self.query_tools.get_teacher_relations(person_name)

    def get_family_relations(self, person_name: str) -> ToolResult:
        """查询人物亲属关系。"""
        return self.query_tools.get_family_relations(person_name)

    def get_social_relations(self, person_name: str) -> ToolResult:
        """查询人物交游关系。"""
        return self.query_tools.get_social_relations(person_name)

    def get_school_membership(self, person_name: str) -> ToolResult:
        """查询人物所属流派。"""
        return self.query_tools.get_school_membership(person_name)

    def get_school_founder(self, school_name: str) -> ToolResult:
        """查询流派开创者。"""
        return self.query_tools.get_school_founder(school_name)

    def get_pair_relations(self, person_a: str, person_b: str) -> ToolResult:
        """查询两个人物之间的直接关系。"""
        return self.query_tools.get_pair_relations(person_a, person_b)

    def get_related_people(self, person_name: str) -> ToolResult:
        """查询人物关联人物网络。"""
        return self.query_tools.get_related_people(person_name)

    def run_raw_sparql(self, sparql: str) -> ToolResult:
        """执行高级 SPARQL 查询。"""
        return self.query_tools.run_raw_sparql(sparql)


def build_tool_catalog() -> list[dict[str, Any]]:
    query_tools = QueryTools(_CatalogGraphStore())
    toolbox = AgentToolbox(query_tools)
    catalog: list[dict[str, Any]] = []

    for definition in TOOL_DEFINITIONS:
        sample_result = toolbox.invoke(definition.name, **definition.sample_kwargs)
        catalog.append(
            {
                "name": definition.name,
                "display_name": definition.display_name,
                "description": definition.description,
                "workflow_role": definition.workflow_role,
                "parameters": [asdict(parameter) for parameter in definition.parameters],
                "input_schema": definition.input_schema(),
                "return_fields": [asdict(field) for field in definition.return_fields],
                "sample_kwargs": definition.sample_kwargs,
                "sparql_template": sample_result.sparql,
                "course_references": [asdict(reference) for reference in definition.course_references],
            }
        )
    return catalog


def build_course_overview() -> list[dict[str, Any]]:
    return [asdict(reference) for reference in COURSE_OVERVIEW]
