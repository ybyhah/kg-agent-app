from __future__ import annotations

import re
from dataclasses import dataclass

from .fewshot_sparql import FewShotDraft, FewShotSparqlGenerator
from .langgraph_workflow import LangGraphWorkflowSkeleton
from .models import QueryResult
from .tools import QueryTools, ToolResult


@dataclass
class RoutedQuery:
    intent: str
    slots: list[str]


@dataclass
class QuestionPlan:
    route_type: str
    routed_query: RoutedQuery | None = None
    fewshot_draft: FewShotDraft | None = None


class QueryWorkflow:
    def __init__(self, tools: QueryTools):
        self.tools = tools
        self.fewshot_generator = FewShotSparqlGenerator()
        self.langgraph = LangGraphWorkflowSkeleton(
            plan_question=self._plan_question,
            execute_tool_plan=self._execute_tool_plan,
            execute_generated_plan=self._execute_generated_plan,
            build_fallback_result=self._build_fallback_result,
        )

    def answer_question(self, question: str) -> QueryResult:
        question = question.strip()
        if not question:
            return QueryResult(mode="empty", answer="请输入问题。")

        if self.langgraph.available:
            graph_result = self.langgraph.run(question)
            if graph_result is not None:
                return graph_result

        return self._answer_question_without_graph(question)

    def _answer_question_without_graph(self, question: str) -> QueryResult:
        plan = self._plan_question(question)
        if plan.route_type == "tool":
            return self._execute_tool_plan(plan)
        if plan.route_type == "generated_sparql":
            return self._execute_generated_plan(plan)
        return self._build_fallback_result(question)

    def _plan_question(self, question: str) -> QuestionPlan:
        routed = self._route_question(question)
        if routed is not None:
            return QuestionPlan(route_type="tool", routed_query=routed)

        draft = self.fewshot_generator.try_generate(question)
        if draft is not None:
            return QuestionPlan(route_type="generated_sparql", fewshot_draft=draft)

        return QuestionPlan(route_type="fallback")

    def _route_question(self, question: str) -> RoutedQuery | None:
        normalized = question.strip().rstrip("？?。")
        if not normalized:
            return None

        pair_relation = re.match(r"^(.+?)[与和](.+?)是什么关系$", normalized)
        if pair_relation:
            person_a = pair_relation.group(1).strip()
            person_b = pair_relation.group(2).strip()
            if person_a and person_b:
                return RoutedQuery(intent="pair_relations", slots=[person_a, person_b])

        intent_rules = [
            ("courtesy_name", ["的字是什么", "字是什么", "字"]),
            ("art_name", ["的号是什么", "号是什么", "号"]),
            ("birth_death", ["的生卒年是什么", "生卒年", "出生", "去世", "卒于"]),
            ("teacher_relations", ["的师承是", "师承", "老师是谁", "师从"]),
            ("family_relations", ["的父亲是谁", "的儿子是谁", "亲属", "家族", "父子", "兄弟"]),
            ("social_relations", ["交游", "朋友", "往来", "交往"]),
            ("school_membership", ["属于什么流派", "属于哪个流派", "所属流派", "流派"]),
            ("school_founder", ["谁开创了", "谁创立了", "开创了", "创立了"]),
            ("person_labels", ["是谁", "介绍", "查一下", "看看"]),
        ]

        for intent, markers in intent_rules:
            for marker in markers:
                if marker in normalized:
                    slots = self._extract_slots(normalized, marker, intent)
                    if slots:
                        return RoutedQuery(intent=intent, slots=slots)

        if len(normalized) <= 8:
            return RoutedQuery(intent="person_labels", slots=[normalized])

        return None

    def _extract_slots(self, question: str, marker: str, intent: str) -> list[str]:
        if intent == "school_founder":
            if marker.startswith("谁"):
                slot = question.split(marker, 1)[-1]
            else:
                slot = question.split(marker, 1)[0]
            cleaned = self._clean_slot(slot)
            return [cleaned] if cleaned else []

        if marker in {"是谁", "的字是什么", "的号是什么", "的生卒年是什么", "的师承是", "的父亲是谁", "的儿子是谁", "亲属", "家族", "父子", "兄弟", "交游", "朋友", "往来", "交往", "属于什么流派", "属于哪个流派", "所属流派", "流派"}:
            slot = question.split(marker, 1)[0]
        else:
            slot = question.split(marker, 1)[-1]

        cleaned = self._clean_slot(slot)
        return [cleaned] if cleaned else []

    def _clean_slot(self, value: str) -> str:
        return value.strip().strip("，,：:；;。？?、 ")

    def _execute_tool_plan(self, plan: QuestionPlan) -> QueryResult:
        routed = plan.routed_query
        if routed is None:
            return self._build_fallback_result("")

        try:
            tool_result = self._call_tool(routed)
        except Exception as exc:
            return QueryResult(
                mode="tool_error",
                answer="工具查询已命中，但当前图谱数据或 SPARQL 执行还不可用。",
                notes=[
                    f"错误信息：{exc}",
                    "如果这是联调阶段，优先检查 data/kg/ 下是否已经放入 schema.ttl、core.ttl、aligned.ttl。",
                    self._workflow_status_note(),
                ],
            )

        answer = self._format_tool_answer(routed, tool_result)
        return QueryResult(
            mode="tool",
            answer=answer,
            sparql=tool_result.sparql,
            rows=tool_result.rows,
            notes=[tool_result.note, self._workflow_status_note()],
        )

    def _execute_generated_plan(self, plan: QuestionPlan) -> QueryResult:
        draft = plan.fewshot_draft
        if draft is None:
            return self._build_fallback_result("")

        try:
            tool_result = self.tools.run_raw_sparql(draft.sparql)
            answer = self._format_generated_answer(draft, tool_result)
            notes = [
                "当前回答来自 few-shot SPARQL 生成骨架。",
                f"匹配示例：{draft.example_name}",
                draft.note,
                self._workflow_status_note(),
            ]
            return QueryResult(
                mode="generated_sparql",
                answer=answer,
                sparql=tool_result.sparql,
                rows=tool_result.rows,
                notes=notes,
            )
        except Exception as exc:
            notes = [
                "few-shot SPARQL 已生成，但执行失败。",
                f"错误信息：{exc}",
                "常见原因是本体属性名尚未和成员 C 的 Turtle 定稿对齐，或图谱文件尚未接入。",
                draft.note,
                self._workflow_status_note(),
            ]
            return QueryResult(
                mode="generated_sparql",
                answer="系统已经根据 few-shot 示例生成了候选 SPARQL，但当前还不能稳定执行。",
                sparql=draft.sparql,
                rows=[],
                notes=notes,
            )

    def _build_fallback_result(self, question: str) -> QueryResult:
        notes = [
            "当前固定工作流已支持：查字、查号、生卒年、师承、亲属、交游、流派、开创者、两人关系。",
            "下一步可继续补充：复杂路径查询、子查询、统计类问题、多跳关系问题。",
            "问答系统工作流已经预留 LangGraph 骨架和 few-shot SPARQL 生成骨架。",
            "few-shot 提示词模板已写入 src/fewshot_sparql.py，可在接入大模型时直接复用。",
            self._workflow_status_note(),
        ]
        return QueryResult(
            mode="fallback",
            answer="这条问题目前还没有命中固定工具规则，也没有匹配到可直接复用的 few-shot SPARQL 模板。",
            notes=notes,
        )

    def _call_tool(self, routed: RoutedQuery) -> ToolResult:
        intent = routed.intent
        slots = routed.slots

        if intent == "courtesy_name":
            return self.tools.get_courtesy_name(slots[0])
        if intent == "art_name":
            return self.tools.get_art_name(slots[0])
        if intent == "birth_death":
            return self.tools.get_birth_death(slots[0])
        if intent == "teacher_relations":
            return self.tools.get_teacher_relations(slots[0])
        if intent == "family_relations":
            return self.tools.get_family_relations(slots[0])
        if intent == "social_relations":
            return self.tools.get_social_relations(slots[0])
        if intent == "school_membership":
            return self.tools.get_school_membership(slots[0])
        if intent == "school_founder":
            return self.tools.get_school_founder(slots[0])
        if intent == "pair_relations":
            return self.tools.get_pair_relations(slots[0], slots[1])
        return self.tools.get_person_labels(slots[0])

    def _format_tool_answer(self, routed: RoutedQuery, tool_result: ToolResult) -> str:
        rows = tool_result.rows
        slot_text = "、".join(routed.slots)
        if not rows:
            return f"图谱中暂时没有查到与“{slot_text}”相关的结果。"

        if routed.intent == "courtesy_name":
            return self._format_named_answer(slot_text, "字", self._collect_values(rows, "courtesyName"))
        if routed.intent == "art_name":
            return self._format_named_answer(slot_text, "号", self._collect_values(rows, "artName"))
        if routed.intent == "birth_death":
            values: list[str] = []
            for row in rows:
                birth = row.get("birthYear", "").strip()
                death = row.get("deathYear", "").strip()
                if birth or death:
                    values.append(f"{birth} - {death}".strip(" -"))
            return self._format_named_answer(slot_text, "生卒年", values)
        if routed.intent == "teacher_relations":
            return self._format_named_answer(slot_text, "师承对象", self._collect_values(rows, "teacherLabel"))
        if routed.intent == "family_relations":
            values = []
            for row in rows:
                relative = row.get("relativeLabel", "").strip()
                relation_type = row.get("relationType", "").strip()
                if relative and relation_type:
                    values.append(f"{relation_type}：{relative}")
                elif relative:
                    values.append(relative)
            return self._format_named_answer(slot_text, "亲属关系对象", values)
        if routed.intent == "social_relations":
            return self._format_named_answer(slot_text, "交游对象", self._collect_values(rows, "friendLabel"))
        if routed.intent == "school_membership":
            return self._format_named_answer(slot_text, "所属流派", self._collect_values(rows, "schoolLabel"))
        if routed.intent == "school_founder":
            return self._format_named_answer(slot_text, "开创者", self._collect_values(rows, "founderLabel"))
        if routed.intent == "pair_relations":
            values = []
            for row in rows:
                relation_label = row.get("relationLabel", "").strip()
                relation_uri = row.get("relation", "").strip()
                direction = row.get("direction", "").strip()
                shown = relation_label or relation_uri
                if shown:
                    values.append(f"{direction}：{shown}")
            return self._format_named_answer(slot_text, "人物关系", values)

        labels = self._collect_values(rows, "label")
        shown = "、".join(labels[:10]) if labels else "暂无候选标签"
        return f"图谱里与“{slot_text}”相关的候选标签有：{shown}"

    def _format_generated_answer(self, draft: FewShotDraft, tool_result: ToolResult) -> str:
        if not tool_result.rows:
            return "系统已经生成并执行了候选 SPARQL，但当前结果集为空。"
        preview = self._summarize_rows(tool_result.rows)
        return f"系统已根据 few-shot 示例生成并执行 SPARQL，当前返回结果包括：{preview}"

    def _summarize_rows(self, rows: list[dict[str, str]]) -> str:
        chunks: list[str] = []
        for row in rows[:5]:
            parts = [f"{key}={value}" for key, value in row.items() if value]
            if parts:
                chunks.append("，".join(parts))
        return "；".join(chunks) if chunks else "结果为空"

    def _collect_values(self, rows: list[dict[str, str]], key: str) -> list[str]:
        values: list[str] = []
        for row in rows:
            value = row.get(key, "").strip()
            if value and value not in values:
                values.append(value)
        return values

    def _format_named_answer(self, slot: str, field_name: str, values: list[str]) -> str:
        if not values:
            return f"图谱里查到了“{slot}”的候选实体，但还没有可展示的{field_name}信息。"
        shown = "、".join(values[:10])
        return f"“{slot}”的{field_name}信息包括：{shown}"

    def _workflow_status_note(self) -> str:
        if self.langgraph.available:
            return "LangGraph 工作流骨架已启用，可用于答辩时展示节点式路由。"
        return "LangGraph 工作流骨架已预留；当前环境未安装 langgraph 时自动退回到本地规则工作流。"
