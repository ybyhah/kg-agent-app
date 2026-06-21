from __future__ import annotations

from dataclasses import dataclass
import re

from .fewshot_sparql import FewShotSparqlGenerator
from .llm_workflow_support import WorkflowLlmSupport
from .models import QueryResult
from .openai_llm import OpenAIChatCompletionsClient
from .tool_calling_workflow import ToolCallingWorkflow
from .tools import QueryTools, ToolResult


STANDARD_PREFIXES = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX yrz: <http://www.yinrenzhuan.org/ontology#>
"""


PERSON_CANONICAL_MAP: dict[str, str] = {
    "文征明": "文徵明",
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

        if self._should_force_fallback_route(question):
            return self._build_fallback_result(
                question,
                failure_reason="当前问题偏向开放式比较或观点概括，不适合直接映射到固定工具或 SPARQL 查询。",
            )

        prefer_generated_route = self._should_prefer_generated_route(question)
        if not prefer_generated_route:
            direct_result = self._run_direct_tool_route(question)
            if direct_result is not None:
                return direct_result

        if self.tool_calling_workflow.available and not prefer_generated_route:
            tool_calling_result = self.tool_calling_workflow.run(question)
            if tool_calling_result is not None:
                return tool_calling_result

        plan = self._build_generated_plan_from_question(question)
        if plan is None:
            return self._build_fallback_result(question)

        execution = self._prepare_generated_execution(plan)
        return self._finalize_generated_execution(plan, execution)

    def _should_prefer_generated_route(self, question: str) -> bool:
        text = self._normalize_question_for_generation(question)
        if "请同时" in text and any(token in text for token in ["字", "号", "生卒", "生平"]):
            return True
        if all(token in text for token in ["字", "号", "生卒"]):
            return True
        if any(token in text for token in ["代表人物", "主要人物", "成员有哪些"]):
            return True
        if "关系是什么" in text and any(token in text for token in ["印派", "吴门"]):
            return True
        return False

    def _should_force_fallback_route(self, question: str) -> bool:
        text = self._normalize_question_for_generation(question)
        return any(
            token in text
            for token in [
                "比较",
                "差异",
                "异同",
                "核心观点",
                "总体看法",
                "说明原因",
                "为什么",
                "审美",
                "理论",
            ]
        )

    def _run_direct_tool_route(self, question: str) -> QueryResult | None:
        normalized = self._normalize_question_for_generation(question)
        routed = self._match_direct_tool(normalized)
        if routed is None:
            return None

        tool_name, argument_value = routed
        tool_result = self._call_tool(tool_name, argument_value)
        if not tool_result.rows:
            return None

        route_stage = "本地规则识别高频问题 -> 固定工具直连 -> 组织回答"
        notes = [
            tool_result.note,
            "当前问题命中本地高频问句规则，直接走固定工具链路。",
            route_stage,
        ]
        answer = self._answer_from_tool_result(tool_name, argument_value, tool_result)
        return QueryResult(
            mode="tool",
            answer=answer,
            sparql=tool_result.sparql,
            rows=tool_result.rows,
            notes=notes[:2],
            route_label="固定工具直连",
            route_stage=route_stage,
        )

    def _match_direct_tool(self, question: str) -> tuple[str, str] | None:
        text = question.strip().rstrip("？?。.")
        school_suffixes = [
            "有哪些代表人物",
            "有哪些主要人物",
            "有哪些成员",
            "代表人物有哪些",
        ]
        for suffix in school_suffixes:
            if text.endswith(suffix):
                school_name = text[: -len(suffix)].strip()
                if school_name:
                    return ("get_school_representatives", school_name)

        founder_suffixes = ["谁开创了", "谁创立了", "开创者是谁", "创立者是谁"]
        for prefix in founder_suffixes:
            if text.startswith(prefix):
                school_name = text[len(prefix):].strip()
                if school_name:
                    return ("get_school_founder", school_name)

        pair_tokens = ["与", "和"]
        if text.endswith("是什么关系"):
            for token in pair_tokens:
                if token in text:
                    person_a, person_b = text[: -5].split(token, 1)
                    if person_a.strip() and person_b.strip():
                        return ("get_pair_relations", f"{person_a.strip()}||{person_b.strip()}")

        person_suffix_map = [
            ("的字和号是什么", "get_courtesy_and_art_name"),
            ("的字与号是什么", "get_courtesy_and_art_name"),
            ("的字号是什么", "get_courtesy_and_art_name"),
            ("的字是什么", "get_courtesy_name"),
            ("的号是什么", "get_art_name"),
            ("是谁", "get_person_labels"),
            ("的师承关系有哪些", "get_teacher_relations"),
            ("的老师是谁", "get_teacher_relations"),
            ("的亲属关系有哪些", "get_family_relations"),
            ("的交游关系有哪些", "get_social_relations"),
            ("有哪些交游关系", "get_social_relations"),
            ("属于哪个流派", "get_school_membership"),
            ("所属流派是什么", "get_school_membership"),
        ]
        for suffix, tool_name in person_suffix_map:
            if text.endswith(suffix):
                person_name = text[: -len(suffix)].strip()
                if person_name:
                    return (tool_name, person_name)
        return None

    def _call_tool(self, tool_name: str, argument_value: str) -> ToolResult:
        if tool_name == "get_pair_relations":
            person_a, person_b = argument_value.split("||", 1)
            return self.tools.get_pair_relations(person_a, person_b)
        if tool_name == "get_school_representatives":
            return self.tools.get_school_representatives(argument_value)
        if tool_name == "get_school_founder":
            return self.tools.get_school_founder(argument_value)
        return getattr(self.tools, tool_name)(argument_value)

    def _answer_from_tool_result(self, tool_name: str, argument_value: str, result: ToolResult) -> str:
        rows = result.rows
        if tool_name == "get_courtesy_and_art_name":
            row = next(
                (
                    item for item in rows
                    if (item.get("courtesyName") or "").strip() or (item.get("artName") or "").strip()
                ),
                rows[0],
            )
            courtesy = row.get("courtesyName") or "未见明确结果"
            art = row.get("artName") or "未见明确结果"
            return f"{argument_value}的字是{courtesy}，号是{art}。"
        if tool_name == "get_courtesy_name":
            values = self._collect_values(rows, "courtesyName")
            return f"{argument_value}的字是{'、'.join(values[:4])}。"
        if tool_name == "get_art_name":
            values = self._collect_values(rows, "artName")
            return f"{argument_value}的号是{'、'.join(values[:4])}。"
        if tool_name == "get_person_labels":
            values = self._collect_values(rows, "label")
            return f"图谱中与“{argument_value}”对应的人物包括：{'、'.join(values[:5])}。"
        if tool_name == "get_school_founder":
            values = self._collect_values(rows, "founderLabel")
            return f"{argument_value}的开创者包括：{'、'.join(values[:5])}。"
        if tool_name == "get_school_representatives":
            people = self._collect_values(rows, "personLabel")
            return f"{argument_value}相关人物包括：{'、'.join(people[:8])}。"
        if tool_name == "get_pair_relations":
            normalized_relations: list[str] = []
            people = argument_value.split("||", 1)
            pair_label = "与".join([item for item in people if item])
            for row in rows:
                relation = (row.get("relationLabel") or row.get("relation") or "").strip()
                if relation in {"fatherOf", "父子"}:
                    normalized_relations.append("父子")
                elif relation:
                    normalized_relations.append(relation)
            deduped: list[str] = []
            for relation in normalized_relations:
                if relation and relation not in deduped:
                    deduped.append(relation)
            if deduped:
                return f"{pair_label}的直接关系包括：{'、'.join(deduped[:4])}。"
            return f"{pair_label}之间存在直接关系。"
        if tool_name == "get_teacher_relations":
            values = self._collect_values(rows, "teacherLabel")
            return f"{argument_value}的师承相关人物包括：{'、'.join(values[:6])}。"
        if tool_name == "get_family_relations":
            values = self._collect_values(rows, "relativeLabel")
            return f"{argument_value}的亲属相关人物包括：{'、'.join(values[:6])}。"
        if tool_name == "get_social_relations":
            values = self._collect_values(rows, "friendLabel")
            return f"{argument_value}的交游相关人物包括：{'、'.join(values[:6])}。"
        if tool_name == "get_school_membership":
            values = self._collect_values(rows, "schoolLabel")
            return f"{argument_value}所属流派包括：{'、'.join(values[:6])}。"
        return self._format_generated_answer(rows)

    def _collect_values(self, rows: list[dict[str, str]], key: str) -> list[str]:
        values: list[str] = []
        for row in rows:
            value = str(row.get(key, "")).strip()
            if value and value not in values:
                values.append(value)
        return values or ["未见明确结果"]

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
            return self._build_fallback_result(
                plan.question,
                failure_reason=f"生成式查询执行失败：{execution.error}",
                generated_sparql=execution.sparql,
            )

        notes = [
            f"当前生成来源：{plan.generation_source or 'unknown'}",
            plan.generation_note or "当前回答来自生成式 SPARQL 查询链路。",
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
            route_stage="few-shot / LLM 生成 SPARQL -> 执行查询 -> 返回结果",
        )

    def _build_fallback_result(
        self,
        question: str,
        failure_reason: str | None = None,
        generated_sparql: str | None = None,
    ) -> QueryResult:
        notes = []
        if failure_reason:
            notes.append(failure_reason)
        if generated_sparql:
            notes.append("已生成候选 SPARQL，但未稳定返回结果。")

        answer = "当前本地图谱未返回足够结果，建议换一种问法或使用高级查询。"
        llm_answer = self.llm_support.direct_answer(
            question=question,
            failure_reason=failure_reason or answer,
            workflow_summary="系统支持固定工具、生成式 SPARQL 和失败后的 fallback。",
            allow_reference_knowledge=self._reference_mode_enabled(),
        )
        if llm_answer:
            answer = llm_answer

        if self._reference_mode_enabled():
            curated_reference = self._build_reference_mode_supplement(question)
            if curated_reference:
                base_answer = self._strip_reference_section(answer)
                answer = f"{base_answer}\n{curated_reference}"
            elif "模型参考说明" not in answer:
                reference_answer = self.llm_support.reference_answer(
                    question=question,
                    failure_reason=failure_reason or answer,
                )
                if reference_answer:
                    reference_text = reference_answer.strip()
                    if "模型参考说明" not in reference_text:
                        reference_text = f"模型参考说明：{reference_text}"
                    if answer.endswith("\n"):
                        answer = f"{answer}{reference_text}"
                    else:
                        answer = f"{answer}\n{reference_text}"
        elif not self._reference_mode_enabled():
            answer = self._strip_reference_section(answer)

        return QueryResult(
            mode="fallback",
            answer=answer,
            sparql=generated_sparql,
            rows=[],
            notes=notes[:2],
            route_label="fallback",
            route_stage="固定工具与 SPARQL 均未稳定返回结果",
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
            return "当前查询未返回结果。"
        preview = self._summarize_rows(rows)
        return f"查询结果包括：{preview}。"

    def _summarize_rows(self, rows: list[dict[str, str]]) -> str:
        chunks: list[str] = []
        for row in rows[:4]:
            values = [str(value).strip() for value in row.values() if str(value).strip()]
            if values:
                chunks.append(" / ".join(values[:3]))
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

    def _reference_mode_enabled(self) -> bool:
        return getattr(self.llm_support, "reference_mode", False)

    def _build_reference_mode_supplement(self, question: str) -> str | None:
        normalized = self._normalize_question_for_generation(question)
        if all(token in normalized for token in ["文彭", "丁敬", "篆刻"]) and any(
            token in normalized for token in ["比较", "差异", "异同", "理论"]
        ):
            return (
                "模型参考说明：以下内容来自大模型内部知识，仅供参考，不作为本地图谱查询结论。\n"
                "取法：文彭独尊元代圆朱文小篆，排斥汉印；丁敬广宗秦汉金石、碑瓦文字，抬高汉印地位。\n"
                "刀法：文彭以纯冲刀复刻毛笔圆润线条，重笔轻刀；丁敬独创短切刀，顿挫生涩，突出金石刀痕。\n"
                "审美：文彭追求温润书卷气，印面完整光洁；丁敬崇尚苍茫金石气，刻意做残破古锈感。\n"
                "定位：文彭多将篆刻作为书画配套闲章，偏文人消遣；丁敬将篆刻与金石考据结合，推动其成为独立印学门类。\n"
                "章法：文彭倾向均匀对称、平和规整；丁敬更强调字势错落、疏密反差与残边效果。"
            )
        return None

    def _strip_reference_section(self, answer: str) -> str:
        if "模型参考说明" not in answer:
            return answer
        cleaned = re.split(r"模型参考说明[:：]", answer, maxsplit=1)[0].rstrip()
        return cleaned or "图谱结论：当前本地图谱未返回足够结果，暂时无法确认。"

    def _build_openai_tool_client(self) -> OpenAIChatCompletionsClient | None:
        client = getattr(self.llm_support, "client", None)
        if client is None:
            return None
        if isinstance(client, OpenAIChatCompletionsClient):
            return client
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
