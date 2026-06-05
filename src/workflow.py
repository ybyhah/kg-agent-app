from __future__ import annotations

from .models import QueryResult
from .tools import QueryTools


class QueryWorkflow:
    def __init__(self, tools: QueryTools):
        self.tools = tools

    def answer_question(self, question: str) -> QueryResult:
        question = question.strip()
        if not question:
            return QueryResult(mode="empty", answer="\u8bf7\u8f93\u5165\u95ee\u9898\u3002")

        person_name = self._extract_candidate_person_name(question)
        if person_name:
            tool_result = self.tools.get_person_labels(person_name)
            answer = self._format_tool_answer(person_name, tool_result.rows)
            return QueryResult(
                mode="tool",
                answer=answer,
                sparql=tool_result.sparql,
                rows=tool_result.rows,
                notes=[tool_result.note],
            )

        return QueryResult(
            mode="fallback",
            answer=(
                "\u5f53\u524d\u5de5\u4f5c\u6d41\u9aa8\u67b6\u5df2\u7ecf\u8dd1\u901a\uff0c"
                "\u4f46\u8fd9\u6761\u95ee\u9898\u8fd8\u6ca1\u6709\u63a5\u5165\u6b63\u5f0f\u7684\u610f\u56fe\u5206\u7c7b\u4e0e SPARQL \u751f\u6210\u3002"
                " \u4f60\u73b0\u5728\u53ef\u4ee5\u7ee7\u7eed\u8865\u67e5\u8be2\u6a21\u677f\u3001few-shot \u793a\u4f8b\u548c\u5b9e\u4f53\u89e3\u6790\u903b\u8f91\u3002"
            ),
            notes=[
                "\u4e0b\u4e00\u6b65\uff1a\u8865\u201c\u5b57\u3001\u53f7\u3001\u751f\u5352\u5e74\u3001\u5e08\u627f\u3001\u4eb2\u5c5e\u3001\u4ea4\u6e38\u3001\u6d41\u6d3e\u201d\u7b49\u95ee\u9898\u7684\u610f\u56fe\u8def\u7531\u3002",
                "\u5982\u679c\u540e\u7eed\u6d41\u7a0b\u7a33\u5b9a\uff0c\u53ef\u4ee5\u518d\u66ff\u6362\u6210 LangGraph \u5de5\u4f5c\u6d41\u3002",
            ],
        )

    def _extract_candidate_person_name(self, question: str) -> str | None:
        markers = ["\u8c01\u662f", "\u4ecb\u7ecd", "\u662f\u8c01", "\u67e5", "\u770b\u770b"]
        for marker in markers:
            if marker in question:
                candidate = question.split(marker, 1)[-1].strip("\uff1f?\uff0c\u3002 ")
                return candidate[:20] if candidate else None
        if len(question) <= 8:
            return question.strip("\uff1f?\uff0c\u3002 ")
        return None

    def _format_tool_answer(self, person_name: str, rows: list[dict[str, str]]) -> str:
        if not rows:
            return f"\u56fe\u8c31\u4e2d\u6682\u65f6\u6ca1\u6709\u67e5\u5230\u4e0e\u201c{person_name}\u201d\u5339\u914d\u7684\u6807\u7b7e\u3002"
        labels = [row.get("label", "") for row in rows if row.get("label")]
        if not labels:
            return "\u67e5\u5230\u4e86\u5019\u9009\u5b9e\u4f53\uff0c\u4f46\u7ed3\u679c\u91cc\u6ca1\u6709\u53ef\u76f4\u63a5\u5c55\u793a\u7684\u6807\u7b7e\u3002"
        shown = "\uff0c".join(labels[:10])
        return f"\u56fe\u8c31\u91cc\u4e0e\u201c{person_name}\u201d\u76f8\u5173\u7684\u5019\u9009\u6807\u7b7e\u6709\uff1a{shown}"
