from __future__ import annotations

from dataclasses import dataclass

from .fewshot_sparql import FewShotSparqlGenerator
from .llm_workflow_support import WorkflowLlmSupport
from .models import QueryResult
from .openai_llm import OpenAIChatCompletionsClient
from .tool_calling_workflow import ToolCallingWorkflow
from .tools import QueryTools


STANDARD_PREFIXES = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX yrz: <http://www.yinrenzhuan.org/ontology#>
"""


PERSON_CANONICAL_MAP: dict[str, str] = {
    "文征明": "文徵明",
    "文镜明": "文徵明",
    "征仲": "文徵明",
}

SCHOOL_CANONICAL_MAP: dict[str, str] = {
    "吴门印派": "吴门",
    "吴门派": "吴门",
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

        if self.tool_calling_workflow.available:
            tool_calling_result = self.tool_calling_workflow.run(question)
            if tool_calling_result is not None:
                return tool_calling_result

        plan = self._build_generated_plan_from_question(question)
        if plan is None:
            return self._build_fallback_result(question)

        execution = self._prepare_generated_execution(plan)
        return self._finalize_generated_execution(plan, execution)

    def _build_generated_plan_from_question(self, question: str) -> QuestionPlan | None:
        normalized_question = self._normalize_question_for_generation(question)
        llm_draft = self.llm_support.try_generate_sparql(normalized_question, self.fewshot_generator)
        if llm_draft is not None:
            return QuestionPlan(
                question=question,
                generated_sparql=self._sanitize_generated_sparql(llm_draft.sparql),
                generation_source=llm_draft.source,
                generation_note=llm_draft.note,
            )

        template_draft = self.fewshot_generator.try_generate(normalized_question)
        if template_draft is not None:
            return QuestionPlan(
                question=question,
                generated_sparql=self._sanitize_generated_sparql(template_draft.sparql),
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
                " 常见原因是本体属性名尚未与最终 Turtle 定义完全对齐，或图谱文件尚未稳定接入。"
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

    def _sanitize_generated_sparql(self, sparql: str) -> str:
        text = sparql.strip()
        text = text.replace("http://example.com/yrz/", "http://www.yinrenzhuan.org/ontology#")
        text = text.replace("http://example.org/yrz/", "http://www.yinrenzhuan.org/ontology#")
        text = text.replace("http://www.yunshuiyuan.org/ontology/", "http://www.yinrenzhuan.org/ontology#")
        if "PREFIX yrz:" not in text:
            text = f"{STANDARD_PREFIXES}\n{text}"
        else:
            lines = []
            for line in text.splitlines():
                if line.startswith("PREFIX yrz:"):
                    lines.append("PREFIX yrz: <http://www.yinrenzhuan.org/ontology#>")
                else:
                    lines.append(line)
            text = "\n".join(lines)
        return text

    def _workflow_status_note(self) -> str:
        if self.tool_calling_workflow.available:
            return "当前已启用真实的 LLM -> ToolNode -> ToolMessage -> LLM 回答链路。"
        return "当前未启用 LLM 工具调用链，系统将直接尝试生成式 SPARQL。"

    def _reference_mode_enabled(self) -> bool:
        return getattr(self.llm_support, "reference_mode", False)

    def _build_openai_tool_client(self) -> OpenAIChatCompletionsClient | None:
        client = getattr(self.llm_support, "client", None)
        if client is None:
            return None
        # 如果 client 本身就是 OpenAIChatCompletionsClient，直接返回
        if isinstance(client, OpenAIChatCompletionsClient):
            return client
        # 兼容其他情况
        try:
            if hasattr(client, "client") and hasattr(client.client, "api_key"):
                raw_api_key = client.client.api_key
            else:
                raw_api_key = getattr(client, "api_key", None)
            if not raw_api_key:
                return None
            model_name = getattr(client, "model", "") or "deepseek-v4-flash"
            base_url = getattr(client, "base_url", "") or ""
            return OpenAIChatCompletionsClient(api_key=raw_api_key, model=model_name, base_url=base_url)
        except Exception:
            return None