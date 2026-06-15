from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.utils.function_calling import convert_to_openai_tool
from openai import OpenAI


@dataclass(frozen=True)
class OpenAIChatResult:
    message: AIMessage
    raw_text: str


class OpenAIChatCompletionsClient:
    def __init__(self, api_key: str, model: str = "deepseek-v4-flash", base_url: str | None = None):
        client_kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        self.client = OpenAI(**client_kwargs)
        self.model = model
        self.base_url = base_url or ""

    def invoke(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )
        return (response.choices[0].message.content or "").strip()

    def bind_tools(self, tools: list[Any], prompt: str, system_prompt: str = "") -> OpenAIChatResult:
        openai_tools = [convert_to_openai_tool(tool) for tool in tools]
        messages: list[dict[str, str]] = []
        if system_prompt.strip():
            messages.append({"role": "system", "content": system_prompt.strip()})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=openai_tools,
            tool_choice="auto",
        )
        choice = response.choices[0].message
        tool_calls: list[dict[str, Any]] = []
        for call in choice.tool_calls or []:
            arguments = call.function.arguments or "{}"
            try:
                parsed_args = json.loads(arguments)
            except json.JSONDecodeError:
                parsed_args = {}
            tool_calls.append(
                {
                    "name": call.function.name,
                    "args": parsed_args,
                    "id": call.id,
                    "type": "tool_call",
                }
            )
        return OpenAIChatResult(
            message=AIMessage(content=choice.content or "", tool_calls=tool_calls),
            raw_text=choice.content or "",
        )


class OpenAIResponsesClient(OpenAIChatCompletionsClient):
    pass
