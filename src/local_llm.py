from __future__ import annotations

from pathlib import Path


class LocalTransformersLangChainClient:
    def __init__(
        self,
        model_dir: Path,
        max_new_tokens: int = 768,
        temperature: float = 0.1,
        device: str = "auto",
        load_in_4bit: bool = False,
    ) -> None:
        self.model_dir = model_dir
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.device = device
        self.load_in_4bit = load_in_4bit
        self._chain = None

    def invoke(self, prompt: str) -> str:
        chain = self._get_chain()
        result = chain.invoke(prompt)
        if isinstance(result, str):
            return result
        if isinstance(result, list) and result:
            first = result[0]
            if isinstance(first, dict) and "generated_text" in first:
                return str(first["generated_text"])
        return str(result)

    def _get_chain(self):
        if self._chain is None:
            self._chain = self._build_chain()
        return self._chain

    def _build_chain(self):
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
        except ImportError as exc:
            raise RuntimeError(
                f"Failed to import transformers runtime: {exc}"
            ) from exc

        try:
            from langchain_huggingface import HuggingFacePipeline
        except ImportError as exc:
            raise RuntimeError(
                "Missing langchain_huggingface. Install it before running extraction."
            ) from exc

        torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

        tokenizer = AutoTokenizer.from_pretrained(self.model_dir, trust_remote_code=True)
        model_kwargs = {
            "torch_dtype": torch_dtype,
            "device_map": self.device,
            "trust_remote_code": True,
            "low_cpu_mem_usage": True,
        }
        if self.load_in_4bit:
            model_kwargs["load_in_4bit"] = True

        model = AutoModelForCausalLM.from_pretrained(
            self.model_dir,
            **model_kwargs,
        )

        generator = pipeline(
            task="text-generation",
            model=model,
            tokenizer=tokenizer,
            max_new_tokens=self.max_new_tokens,
            temperature=self.temperature,
            return_full_text=False,
        )
        return HuggingFacePipeline(pipeline=generator)
