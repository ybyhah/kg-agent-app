from __future__ import annotations

from dataclasses import dataclass

from .models import QueryResult
from .tools import QueryTools, ToolResult


@dataclass
class RoutedQuery:
    intent: str
    slot: str


class QueryWorkflow:
    def __init__(self, tools: QueryTools):
        self.tools = tools

    def answer_question(self, question: str) -> QueryResult:
        question = question.strip()
        if not question:
            return QueryResult(mode="empty", answer="请输入问题。")

        routed = self._route_question(question)
        if routed is None:
            return QueryResult(
                mode="fallback",
                answer=(
                    "当前工作流已经支持部分固定问题，但这条问题还没有接入正式的意图分类。"
                    " 你可以继续补 few-shot 示例、SPARQL 模板和 LangGraph 工作流。"
                ),
                notes=[
                    "当前已支持：查字、查号、生卒年、师承、亲属、交游、流派、开创、候选人物标签。",
                    "下一步可补：自然语言生成 SPARQL、复杂路径查询、多跳关系问题。",
                ],
            )

        tool_result = self._call_tool(routed)
        answer = self._format_tool_answer(routed.intent, routed.slot, tool_result)
        return QueryResult(
            mode="tool",
            answer=answer,
            sparql=tool_result.sparql,
            rows=tool_result.rows,
            notes=[tool_result.note],
        )

    def _route_question(self, question: str) -> RoutedQuery | None:
        normalized = question.strip("？?。 ")
        if not normalized:
            return None

        intent_rules = [
            ("courtesy_name", ["字是什么", "字是", "的字"]),
            ("art_name", ["号是什么", "号是", "的号"]),
            ("birth_death", ["生卒年", "出生", "去世", "卒于", "活了多久"]),
            ("teacher_relations", ["师承", "老师是谁", "师从", "师承关系"]),
            ("family_relations", ["父亲", "儿子", "家族", "亲属", "父子", "兄弟"]),
            ("social_relations", ["交游", "朋友", "往来", "交往"]),
            ("school_membership", ["流派", "属于什么派", "属于哪个派", "所属流派"]),
            ("school_founder", ["谁开创", "谁创立", "开创了", "创立了"]),
            ("person_labels", ["是谁", "谁是", "介绍一下", "介绍", "查一下", "查", "看看"]),
        ]

        for intent, markers in intent_rules:
            for marker in markers:
                if marker in normalized:
                    slot = self._extract_slot(normalized, marker, intent)
                    if slot:
                        return RoutedQuery(intent=intent, slot=slot)

        if len(normalized) <= 8:
            return RoutedQuery(intent="person_labels", slot=normalized)

        return None

    def _extract_slot(self, question: str, marker: str, intent: str) -> str | None:
        if intent == "school_founder":
            if marker in ["谁开创", "谁创立"]:
                slot = question.split(marker, 1)[-1]
            else:
                slot = question.split(marker, 1)[0]
        elif marker in ["是谁", "的字", "的号", "生卒年", "出生", "去世", "师承", "父亲", "儿子", "家族", "亲属", "父子", "兄弟", "交游", "朋友", "往来", "交往", "流派", "属于什么派", "属于哪个派", "所属流派"]:
            slot = question.split(marker, 1)[0]
        else:
            slot = question.split(marker, 1)[-1]

        cleaned = slot.strip("：:，,？?。 ")
        return cleaned[:30] if cleaned else None

    def _call_tool(self, routed: RoutedQuery) -> ToolResult:
        intent = routed.intent
        slot = routed.slot

        if intent == "courtesy_name":
            return self.tools.get_courtesy_name(slot)
        if intent == "art_name":
            return self.tools.get_art_name(slot)
        if intent == "birth_death":
            return self.tools.get_birth_death(slot)
        if intent == "teacher_relations":
            return self.tools.get_teacher_relations(slot)
        if intent == "family_relations":
            return self.tools.get_family_relations(slot)
        if intent == "social_relations":
            return self.tools.get_social_relations(slot)
        if intent == "school_membership":
            return self.tools.get_school_membership(slot)
        if intent == "school_founder":
            return self.tools.get_school_founder(slot)
        return self.tools.get_person_labels(slot)

    def _format_tool_answer(self, intent: str, slot: str, tool_result: ToolResult) -> str:
        rows = tool_result.rows
        if not rows:
            return f"图谱中暂时没有查到与“{slot}”相关的结果。"

        if intent == "courtesy_name":
            values = self._collect_values(rows, "courtesyName")
            return self._format_named_answer(slot, "字", values)

        if intent == "art_name":
            values = self._collect_values(rows, "artName")
            return self._format_named_answer(slot, "号", values)

        if intent == "birth_death":
            values = []
            for row in rows:
                birth = row.get("birthYear", "")
                death = row.get("deathYear", "")
                if birth or death:
                    values.append(f"{birth} - {death}".strip(" -"))
            return self._format_named_answer(slot, "生卒年", values)

        if intent == "teacher_relations":
            values = self._collect_values(rows, "teacherLabel")
            return self._format_named_answer(slot, "师承对象", values)

        if intent == "family_relations":
            values = self._collect_values(rows, "relativeLabel")
            return self._format_named_answer(slot, "亲属关系对象", values)

        if intent == "social_relations":
            values = self._collect_values(rows, "friendLabel")
            return self._format_named_answer(slot, "交游对象", values)

        if intent == "school_membership":
            values = self._collect_values(rows, "schoolLabel")
            return self._format_named_answer(slot, "所属流派", values)

        if intent == "school_founder":
            values = self._collect_values(rows, "founderLabel")
            return self._format_named_answer(slot, "开创者", values)

        labels = self._collect_values(rows, "label")
        shown = "，".join(labels[:10]) if labels else "暂无标签"
        return f"图谱里与“{slot}”相关的候选标签有：{shown}"

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
        shown = "，".join(values[:10])
        return f"“{slot}”的{field_name}信息包括：{shown}"
