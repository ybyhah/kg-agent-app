from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .fewshot_sparql import FewShotSparqlGenerator
from .local_llm import LocalTransformersLangChainClient
from .openai_llm import OpenAIResponsesClient


class PromptClient(Protocol):
    def invoke(self, prompt: str) -> str:
        ...


@dataclass(frozen=True)
class LlmSparqlDraft:
    sparql: str
    source: str
    note: str


class WorkflowLlmSupport:
    _fence_pattern = re.compile(r"```(?:sparql|sql)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)
    _sparql_start_pattern = re.compile(
        r"((?:PREFIX\s+[^\n]+\n)*\s*(?:SELECT|ASK|CONSTRUCT|DESCRIBE)\b.*)",
        re.DOTALL | re.IGNORECASE,
    )

    def __init__(
        self,
        client: PromptClient | None = None,
        provider_name: str = "disabled",
        reference_mode: bool = False,
    ):
        self.client = client
        self.provider_name = provider_name
        self.reference_mode = reference_mode

    @property
    def available(self) -> bool:
        return self.client is not None

    @classmethod
    def from_config(cls, config) -> "WorkflowLlmSupport":
        if config.llm_mode == "openai":
            if not config.openai_api_key:
                return cls()
            model_name = config.llm_model_name or "deepseek-v4-flash"
            base_url = config.openai_base_url or ""
            client = OpenAIResponsesClient(
                api_key=config.openai_api_key,
                model=model_name,
                base_url=base_url or None,
            )
            provider_prefix = cls._provider_prefix(model_name=model_name, base_url=base_url)
            return cls(
                client=client,
                provider_name=f"{provider_prefix}:{model_name}",
                reference_mode=config.llm_reference_mode,
            )

        if config.llm_mode == "local_transformers":
            if config.llm_model_dir is None:
                return cls()
            if not Path(config.llm_model_dir).exists():
                return cls()

            client = LocalTransformersLangChainClient(
                model_dir=config.llm_model_dir,
                max_new_tokens=config.llm_max_new_tokens,
                temperature=config.llm_temperature,
                device=config.llm_device,
                load_in_4bit=config.llm_load_in_4bit,
            )
            return cls(
                client=client,
                provider_name="local_transformers",
                reference_mode=config.llm_reference_mode,
            )

        return cls()

    @staticmethod
    def _provider_prefix(model_name: str, base_url: str) -> str:
        lowered_model = (model_name or "").lower()
        lowered_url = (base_url or "").lower()
        if lowered_model.startswith("deepseek") or "deepseek" in lowered_url:
            return "deepseek"
        if base_url:
            return "openai-compatible"
        return "openai"

    def try_generate_sparql(
        self,
        question: str,
        fewshot_generator: FewShotSparqlGenerator,
    ) -> LlmSparqlDraft | None:
        if not self.available:
            return None

        prompt = (
            fewshot_generator.build_prompt(question)
            + "\n\n输出要求：\n"
            + "1. 只输出一段可执行 SPARQL，不要解释。\n"
            + "2. 保留 PREFIX。\n"
            + "3. 如有必要，可使用子查询、UNION、GROUP_CONCAT。\n"
            + "4. 如果无法生成，请输出“无法生成SPARQL”。"
        )
        raw_text = self._safe_invoke(prompt)
        if raw_text is None:
            return None

        sparql = self._extract_sparql(raw_text)
        if not sparql:
            return None

        return LlmSparqlDraft(
            sparql=sparql,
            source="llm_fewshot",
            note="当前 SPARQL 由大模型基于 few-shot 示例生成。",
        )

    def answer_from_query_result(
        self,
        *,
        question: str,
        deterministic_answer: str,
        sparql: str | None,
        rows: list[dict[str, object]],
        notes: list[str] | None = None,
    ) -> str | None:
        if not self.available:
            return None

        preview_rows = rows[:10]
        notes_text = "\n".join(notes or [])
        prompt = (
            "你是《印人传》知识图谱问答系统的回答节点。\n"
            "请严格根据给定查询结果回答，不要编造图谱中没有的事实。\n"
            "如果结果为空或证据不足，请明确说明“当前图谱未返回足够结果”。\n"
            "回答用中文，1到3句，简洁明确。\n\n"
            f"用户问题：{question}\n"
            f"规则回答草稿：{deterministic_answer}\n"
            f"SPARQL：\n{sparql or '无'}\n"
            f"结果表 JSON：\n{json.dumps(preview_rows, ensure_ascii=False, indent=2)}\n"
            f"补充说明：\n{notes_text or '无'}\n"
        )
        return self._safe_invoke(prompt)

    def direct_answer(
        self,
        *,
        question: str,
        failure_reason: str,
        workflow_summary: str,
        allow_reference_knowledge: bool = False,
    ) -> str | None:
        if not self.available:
            return None

        reference_rule = (
            "不要使用模型内部知识补充任何人物或流派事实，只输出谨慎说明型回答。"
            if not allow_reference_knowledge
            else (
                "你可以在谨慎说明后，额外输出一段“模型参考说明”。"
                " 这段内容来自模型内部知识，仅供参考，不作为本地图谱查询结论。"
                " 如果输出这段内容，必须尽量简短。"
            )
        )
        prompt = (
            "你是《印人传》知识图谱问答系统的兜底回答节点。\n"
            "当前工具或 SPARQL 链路没有稳定返回结果。\n"
            "请先输出一行：图谱结论：当前本地图谱未返回足够结果，暂时无法确认。\n"
            "然后可补一句建议，例如可尝试改写问句或使用高级查询。\n"
            f"{reference_rule}\n"
            "回答用中文，最多4句。\n\n"
            f"用户问题：{question}\n"
            f"失败原因：{failure_reason}\n"
            f"系统能力摘要：{workflow_summary}\n"
        )
        return self._safe_invoke(prompt)

    def reference_answer(
        self,
        *,
        question: str,
        failure_reason: str,
    ) -> str | None:
        if not self.available:
            return None

        prompt = (
            "你是《印人传》知识图谱问答系统的参考说明节点。\n"
            "当前本地图谱未稳定返回结果，但系统已开启参考模式。\n"
            "请只输出一段以“模型参考说明：”开头的简短补充，内容可以基于模型内部知识进行概括。\n"
            "必须明确声明这段内容仅供参考，不作为本地图谱查询结论。\n"
            "回答用中文，最多3句，不要重复“图谱结论”。\n\n"
            f"用户问题：{question}\n"
            f"失败原因：{failure_reason}\n"
        )
        return self._safe_invoke(prompt)

    def _safe_invoke(self, prompt: str) -> str | None:
        if self.client is None:
            return None
        try:
            raw_text = self.client.invoke(prompt).strip()
        except Exception as e:
            # 记录错误信息以便调试
            import sys
            print(f"[LLM调用错误] {type(e).__name__}: {str(e)}", file=sys.stderr)
            # 如果是认证错误，抛出以便用户看到
            if "401" in str(e) or "Incorrect API key" in str(e) or "authentication" in str(e).lower():
                raise
            return None
        return raw_text or None

    def _extract_sparql(self, raw_text: str) -> str | None:
        text = raw_text.strip()
        fence_match = self._fence_pattern.search(text)
        if fence_match:
            text = fence_match.group(1).strip()

        if "无法生成SPARQL" in text:
            return None

        start_match = self._sparql_start_pattern.search(text)
        if start_match:
            text = start_match.group(1).strip()

        if not re.search(r"\b(SELECT|ASK|CONSTRUCT|DESCRIBE)\b", text, re.IGNORECASE):
            return None
        return text
