from __future__ import annotations

from dataclasses import dataclass

from .fewshot_sparql import FewShotSparqlGenerator
from .llm_workflow_support import WorkflowLlmSupport
from .models import QueryResult
from .openai_llm import OpenAIChatCompletionsClient
from .tool_calling_workflow import ToolCallingWorkflow
from .tools import QueryTools


PERSON_CANONICAL_MAP: dict[str, str] = {
    "\u6587\u5f81\u660e": "\u6587\u5fb5\u660e",
    "\u6587\u955c\u660e": "\u6587\u5fb5\u660e",
    "\u5f81\u4ef2": "\u6587\u5fb5\u660e",
}

SCHOOL_CANONICAL_MAP: dict[str, str] = {
    "\u5434\u95e8\u5370\u6d3e": "\u5434\u95e8",
    "\u5434\u95e8\u6d3e": "\u5434\u95e8",
}


@dataclass
class QuestionPlan:
    question: str
    generated_sparql: str | None = None
    generation_source: str = ""
    generation_note: str = ""


@dataclass
class GeneratedQueryExecution:
    sparql: str
    rows: list[dict[str, str]]
    note: str
    error: str = ""


class QueryWorkflow:
    def __init__(self, tools: QueryTools, llm_support: WorkflowLlmSupport | None = None):
        self.tools = tools
        self.fewshot_generator = FewShotSparqlGenerator()
        self.llm_support = llm_support or WorkflowLlmSupport()
        self.openai_tool_client = self._build_openai_tool_client()
        self.tool_calling_workflow = ToolCallingWorkflow(
            query_tools=self.tools,
            llm_client=self.openai_tool_client,
            answer_from_result=self._answer_from_result,
            prepare_generated_execution=self._prepare_generated_execution,
            finalize_generated_execution=self._finalize_generated_execution,
            build_fallback_result=self._build_fallback_result,
            build_generated_plan=self._build_generated_plan_from_question,
        )

    def answer_question(self, question: str) -> QueryResult:
        question = question.strip()
        if not question:
            return QueryResult(
                mode="empty",
                answer="请输入问题。",
                route_label="等待查询",
                route_stage="尚未进入问答工作流",
            )

        openai_failure_note = ""
        if self.tool_calling_workflow.available:
            try:
                tool_calling_result = self.tool_calling_workflow.run(question)
            except Exception as exc:
                tool_calling_result = None
                openai_failure_note = f"OpenAI 工具调用链暂时不可用，已自动降级到本地图谱链路：{exc}"
            if tool_calling_result is not None:
                return tool_calling_result

        deterministic_tool_result = self._run_local_tool_fallback(question)
        if deterministic_tool_result is not None:
            if openai_failure_note:
                deterministic_tool_result.notes.insert(0, openai_failure_note)
            return deterministic_tool_result

        plan = self._build_generated_plan_from_question(question)
        if plan is None:
            result = self._build_fallback_result(question)
            if openai_failure_note:
                result.notes.insert(0, openai_failure_note)
            return result

        execution = self._prepare_generated_execution(plan)
        result = self._finalize_generated_execution(plan, execution)
        if openai_failure_note:
            result.notes.insert(0, openai_failure_note)
        return result

    def _build_generated_plan_from_question(self, question: str) -> QuestionPlan | None:
        normalized_question = self._normalize_question_for_generation(question)
        llm_draft = self.llm_support.try_generate_sparql(normalized_question, self.fewshot_generator)
        if llm_draft is not None:
            return QuestionPlan(
                question=question,
                generated_sparql=llm_draft.sparql,
                generation_source=llm_draft.source,
                generation_note=llm_draft.note,
            )

        template_draft = self.fewshot_generator.try_generate(normalized_question)
        if template_draft is not None:
            return QuestionPlan(
                question=question,
                generated_sparql=template_draft.sparql,
                generation_source="fewshot_template",
                generation_note=template_draft.note,
            )
        return None

    def _prepare_generated_execution(self, plan: QuestionPlan) -> GeneratedQueryExecution:
        if not plan.generated_sparql:
            return GeneratedQueryExecution(
                sparql="",
                rows=[],
                note="当前没有可执行的 SPARQL 草稿。",
                error="missing_sparql",
            )
        try:
            tool_result = self.tools.run_raw_sparql(plan.generated_sparql)
            return GeneratedQueryExecution(
                sparql=tool_result.sparql,
                rows=tool_result.rows,
                note=tool_result.note,
            )
        except Exception as exc:
            return GeneratedQueryExecution(
                sparql=plan.generated_sparql,
                rows=[],
                note="SPARQL 已生成，但执行失败。",
                error=str(exc),
            )

    def _finalize_generated_execution(
        self,
        plan: QuestionPlan,
        execution: GeneratedQueryExecution,
    ) -> QueryResult:
        if not execution.sparql:
            return self._build_fallback_result(plan.question)

        if execution.error:
            failure_reason = (
                f"候选 SPARQL 已生成，但执行失败：{execution.error}。"
                " 常见原因是本体属性名尚未与最终 Turtle 定义完全对齐，或图谱文件尚未接入。"
            )
            direct_answer = self._build_fallback_result(
                plan.question,
                failure_reason=failure_reason,
                generated_sparql=execution.sparql,
            )
            direct_answer.notes = [
                f"当前生成来源：{plan.generation_source or 'unknown'}",
                plan.generation_note,
                self._workflow_status_note(),
                *[note for note in direct_answer.notes if note],
            ]
            direct_answer.sparql = execution.sparql
            return direct_answer

        route_stage = "LLM / few-shot 生成 SPARQL -> 执行查询 -> LLM 基于结果回答"
        notes = [
            f"当前生成来源：{plan.generation_source or 'unknown'}",
            plan.generation_note or "当前回答来自生成式 SPARQL 查询链路。",
            execution.note,
            route_stage,
            self._workflow_status_note(),
        ]
        answer = self._answer_from_result(
            question=plan.question,
            deterministic_answer=self._format_generated_answer(execution.rows),
            sparql=execution.sparql,
            rows=execution.rows,
            notes=notes,
        )
        return QueryResult(
            mode="generated_sparql",
            answer=answer,
            sparql=execution.sparql,
            rows=execution.rows,
            notes=notes,
            route_label="生成式 SPARQL",
            route_stage=route_stage,
        )

    def _build_fallback_result(
        self,
        question: str,
        failure_reason: str | None = None,
        generated_sparql: str | None = None,
    ) -> QueryResult:
        route_stage = "工具链与 SPARQL 链均未稳定命中 -> fallback 谨慎说明"
        notes = [
            "当前主链路为：优先走 LLM function calling 固定工具，不足时转为 LLM / few-shot 生成 SPARQL，再执行查询。",
            "只有当工具链和 SPARQL 链都没有稳定返回结果时，系统才进入 fallback。",
            route_stage,
            self._workflow_status_note(),
        ]
        if failure_reason:
            notes.insert(0, failure_reason)
        if generated_sparql:
            notes.insert(1 if failure_reason else 0, "当前问题已经生成过候选 SPARQL，但查询没有稳定完成。")

        answer = "图谱结论：当前本地图谱未返回足够结果，暂时无法确认。"
        llm_answer = self.llm_support.direct_answer(
            question=question,
            failure_reason=failure_reason or answer,
            workflow_summary="系统支持 function calling 固定工具、生成式 SPARQL、SPARQL 执行，以及失败后的谨慎 fallback。",
            allow_reference_knowledge=self._reference_mode_enabled(),
        )
        if llm_answer:
            answer = llm_answer
            notes.insert(0, f"当前回答来自大模型 fallback 节点（{self.llm_support.provider_name}）。")

        return QueryResult(
            mode="fallback",
            answer=answer,
            sparql=generated_sparql,
            notes=notes,
            route_label="fallback",
            route_stage=route_stage,
        )

    def _answer_from_result(
        self,
        *,
        question: str,
        deterministic_answer: str,
        sparql: str | None,
        rows: list[dict[str, str]],
        notes: list[str],
    ) -> str:
        llm_answer = self.llm_support.answer_from_query_result(
            question=question,
            deterministic_answer=deterministic_answer,
            sparql=sparql,
            rows=rows,
            notes=notes,
        )
        return llm_answer or deterministic_answer

    def _format_generated_answer(self, rows: list[dict[str, str]]) -> str:
        if not rows:
            return "系统已经生成并执行了候选 SPARQL，但当前结果集为空。"
        preview = self._summarize_rows(rows)
        return f"系统已根据示例生成并执行 SPARQL，当前返回结果包括：{preview}"

    def _summarize_rows(self, rows: list[dict[str, str]]) -> str:
        chunks: list[str] = []
        for row in rows[:5]:
            parts = [f"{key}={value}" for key, value in row.items() if value]
            if parts:
                chunks.append("；".join(parts))
        return "；".join(chunks) if chunks else "结果为空"

    def _normalize_question_for_generation(self, question: str) -> str:
        normalized = self._replace_aliases_with_canonical(question, SCHOOL_CANONICAL_MAP)
        normalized = self._replace_aliases_with_canonical(normalized, PERSON_CANONICAL_MAP)
        return normalized

    def _replace_aliases_with_canonical(self, text: str, canonical_map: dict[str, str]) -> str:
        normalized = text
        for alias in sorted(canonical_map, key=len, reverse=True):
            normalized = normalized.replace(alias, canonical_map[alias])
        return normalized

    def _workflow_status_note(self) -> str:
        if self.tool_calling_workflow.available:
            return "当前已启用真实的 LLM -> ToolNode -> ToolMessage -> LLM 回答链路。"
        return "当前未启用 OpenAI 工具调用链，系统将直接尝试生成式 SPARQL。"

    def _reference_mode_enabled(self) -> bool:
        return getattr(self.llm_support, "reference_mode", False)

    def _build_openai_tool_client(self) -> OpenAIChatCompletionsClient | None:
        provider_name = getattr(self.llm_support, "provider_name", "")
        if not provider_name.startswith("openai:"):
            return None
        client = getattr(self.llm_support, "client", None)
        if client is None or not hasattr(client, "client"):
            return None
        try:
            raw_api_key = client.client.api_key
        except Exception:
            return None
        model_name = provider_name.split("openai:", 1)[-1] or "gpt-5.5"
        if not raw_api_key:
            return None
        return OpenAIChatCompletionsClient(api_key=raw_api_key, model=model_name)

    def _run_local_tool_fallback(self, question: str) -> QueryResult | None:
        normalized = self._normalize_question_for_generation(question.strip()).rstrip("\uFF1F?")
        if not normalized:
            return None

        if normalized.endswith("\u662F\u8C01") or normalized.endswith("\u662F\u8C01\u554A"):
            person = normalized[:-2].strip()
            rows = self.tools.get_person_labels(person).rows
            if rows:
                answer = f"{person}在当前图谱中存在对应人物实体，共找到 {len(rows)} 条候选记录。"
                return QueryResult(
                    mode="tool",
                    answer=answer,
                    rows=rows,
                    notes=["当前结果来自本地图谱固定工具降级链路。"],
                    route_label="固定工具降级",
                    route_stage="OpenAI 不可用 -> 本地图谱固定工具",
                )

        if "\u7684\u5B57\u548C\u53F7" in normalized:
            person = normalized.split("\u7684\u5B57\u548C\u53F7", 1)[0].strip()
            courtesy = self.tools.get_courtesy_name(person)
            art = self.tools.get_art_name(person)
            courtesy_names = sorted(
                {
                    (row.get("courtesyName") or row.get("courtesyLabel") or "").strip()
                    for row in courtesy.rows
                    if (row.get("courtesyName") or row.get("courtesyLabel") or "").strip()
                }
            )
            art_names = sorted(
                {
                    (row.get("artName") or row.get("artLabel") or "").strip()
                    for row in art.rows
                    if (row.get("artName") or row.get("artLabel") or "").strip()
                }
            )
            if courtesy_names or art_names:
                answer = f"{person}的字为：{'、'.join(courtesy_names) or '暂无'}；号为：{'、'.join(art_names) or '暂无'}。"
                return QueryResult(
                    mode="tool",
                    answer=answer,
                    sparql=courtesy.sparql,
                    rows=courtesy.rows + art.rows,
                    notes=[courtesy.note, art.note, "当前结果来自本地图谱固定工具降级链路。"],
                    route_label="固定工具降级",
                    route_stage="OpenAI 不可用 -> 本地图谱固定工具",
                )

        if "\u7684\u5B57" in normalized:
            person = normalized.split("\u7684\u5B57", 1)[0].strip()
            result = self.tools.get_courtesy_name(person)
            if result.rows:
                names = sorted(
                    {
                        (row.get("courtesyName") or row.get("courtesyLabel") or "").strip()
                        for row in result.rows
                        if (row.get("courtesyName") or row.get("courtesyLabel") or "").strip()
                    }
                )
                answer = f"{person}的字为：{'、'.join(names)}。"
                return QueryResult(
                    mode="tool",
                    answer=answer,
                    sparql=result.sparql,
                    rows=result.rows,
                    notes=[result.note, "当前结果来自本地图谱固定工具降级链路。"],
                    route_label="固定工具降级",
                    route_stage="OpenAI 不可用 -> 本地图谱固定工具",
                )

        if "\u7684\u53F7" in normalized:
            person = normalized.split("\u7684\u53F7", 1)[0].strip()
            result = self.tools.get_art_name(person)
            if result.rows:
                names = sorted(
                    {
                        (row.get("artName") or row.get("artLabel") or "").strip()
                        for row in result.rows
                        if (row.get("artName") or row.get("artLabel") or "").strip()
                    }
                )
                answer = f"{person}的号为：{'、'.join(names)}。"
                return QueryResult(
                    mode="tool",
                    answer=answer,
                    sparql=result.sparql,
                    rows=result.rows,
                    notes=[result.note, "当前结果来自本地图谱固定工具降级链路。"],
                    route_label="固定工具降级",
                    route_stage="OpenAI 不可用 -> 本地图谱固定工具",
                )

        if "\u4E0E" in normalized and "\u4EC0\u4E48\u5173\u7CFB" in normalized:
            left, right = normalized.split("\u4E0E", 1)
            person_a = left.strip()
            person_b = right.replace("\u662F\u4EC0\u4E48\u5173\u7CFB", "").replace("\u4EC0\u4E48\u5173\u7CFB", "").strip()
            result = self.tools.get_pair_relations(person_a, person_b)
            if result.rows:
                rels = sorted(
                    {
                        (row.get("relationLabel") or row.get("relation") or "").strip()
                        for row in result.rows
                        if (row.get("relationLabel") or row.get("relation") or "").strip()
                    }
                )
                answer = f"{person_a}与{person_b}的关系包括：{'、'.join(rels)}。"
                return QueryResult(
                    mode="tool",
                    answer=answer,
                    sparql=result.sparql,
                    rows=result.rows,
                    notes=[result.note, "当前结果来自本地图谱固定工具降级链路。"],
                    route_label="固定工具降级",
                    route_stage="OpenAI 不可用 -> 本地图谱固定工具",
                )

        if "\u8C01\u5F00\u521B\u4E86" in normalized:
            school = normalized.split("\u8C01\u5F00\u521B\u4E86", 1)[-1].strip()
            result = self.tools.get_school_founder(school)
            if result.rows:
                founders = sorted(
                    {
                        (row.get("founderLabel") or "").strip()
                        for row in result.rows
                        if (row.get("founderLabel") or "").strip()
                    }
                )
                answer = f"{school}的开创者包括：{'、'.join(founders)}。"
                return QueryResult(
                    mode="tool",
                    answer=answer,
                    sparql=result.sparql,
                    rows=result.rows,
                    notes=[result.note, "当前结果来自本地图谱固定工具降级链路。"],
                    route_label="固定工具降级",
                    route_stage="OpenAI 不可用 -> 本地图谱固定工具",
                )

        if "\u7684\u5E08\u627F\u5173\u7CFB" in normalized:
            person = normalized.split("\u7684\u5E08\u627F\u5173\u7CFB", 1)[0].strip()
            result = self.tools.get_teacher_relations(person)
            if result.rows:
                teachers = sorted(
                    {
                        (row.get("teacherLabel") or "").strip()
                        for row in result.rows
                        if (row.get("teacherLabel") or "").strip()
                    }
                )
                answer = f"{person}的师承对象包括：{'、'.join(teachers)}。"
                return QueryResult(
                    mode="tool",
                    answer=answer,
                    sparql=result.sparql,
                    rows=result.rows,
                    notes=[result.note, "当前结果来自本地图谱固定工具降级链路。"],
                    route_label="固定工具降级",
                    route_stage="OpenAI 不可用 -> 本地图谱固定工具",
                )

        return None
