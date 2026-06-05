from __future__ import annotations

from .models import QueryResult
from .tools import QueryTools


class QueryWorkflow:
    def __init__(self, tools: QueryTools):
        self.tools = tools

    def answer_question(self, question: str) -> QueryResult:
        question = question.strip()
        if not question:
            return QueryResult(mode="empty", answer="请输入问题。")

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
                "当前工作流骨架已经跑通，但这条问题还没有接入正式的意图分类与SPARQL生成。"
                " 你现在可以先补查询模板、few-shot示例和实体解析逻辑。"
            ),
            notes=[
                "Next step: add intent routing for 字、号、生卒年、师承、亲属、交游、流派 queries.",
                "Optional: replace this module with LangGraph after the final query tools are stable.",
            ],
        )

    def _extract_candidate_person_name(self, question: str) -> str | None:
        markers = ["谁是", "介绍", "是谁", "查", "看看"]
        for marker in markers:
            if marker in question:
                candidate = question.split(marker, 1)[-1].strip("？?，。 ")
                return candidate[:20] if candidate else None
        if len(question) <= 8:
            return question.strip("？?，。 ")
        return None

    def _format_tool_answer(self, person_name: str, rows: list[dict[str, str]]) -> str:
        if not rows:
            return f"图谱中暂时没有查到与“{person_name}”匹配的标签。"
        labels = [row.get("label", "") for row in rows if row.get("label")]
        if not labels:
            return f"查到了候选实体，但结果里没有可直接展示的标签。"
        shown = "，".join(labels[:10])
        return f"图谱里与“{person_name}”相关的候选标签有：{shown}"
