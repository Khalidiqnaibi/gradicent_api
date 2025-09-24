"""
# Mistral LLM adapter using public hosted APIs for quick testing.

Supports:
 - Hugging Face Inference API ("mistralai/Mistral-7B-Instruct-v0.3") – requires HF API token
 - OpenRouter public API ("mistral/mistral-7b-instruct" or other available models) – requires OpenRouter API key

Defaults to OpenRouter (mistralai/mistral-nemo) for convenience in your setup.
"""

import os
import requests
from dotenv import load_dotenv
from typing import Optional, List
from langchain.llms.base import LLM
from langchain.schema import LLMResult

##############
#! Immortal !#
##############

# Load environment variables from .env file without overriding
load_dotenv( override=False)

# Default models & endpoints
DEFAULT_HF_MODEL = os.environ.get(
    "MISTRAL_HF_MODEL",
    "mistralai/Mistral-7B-Instruct-v0.3"
)
DEFAULT_HF_URL = "https://api-inference.huggingface.co/models"

# Default OpenRouter chat completions endpoint
DEFAULT_OPENROUTER_MODEL = os.environ.get(
    "MISTRAL_OPENROUTER_MODEL",
    "mistralai/mistral-nemo"   
)
DEFAULT_OPENROUTER_URL = os.environ.get(
    "OPENROUTER_URL",
    "https://openrouter.ai/api/v1/chat/completions"
)

# Tokens
HF_TOKEN = os.environ.get("HUGGINGFACE_API_TOKEN")
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY")


class MistralLLM(LLM):
    class Config:
        extra = "allow"

    def __init__(
        self,
        mode: str = "openrouter",  # "hf" or "openrouter"
        temperature: float = 0.0,
        max_tokens: int = 512,
        hf_model: Optional[str] = None,
        openrouter_model: Optional[str] = None,
        timeout: int = 60,
        **kwargs
    ):
        super().__init__(**kwargs)

        self.mode = mode
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.hf_model = hf_model or DEFAULT_HF_MODEL
        self.openrouter_model = openrouter_model or DEFAULT_OPENROUTER_MODEL
        self.timeout = timeout

        if self.mode == "hf" and not HF_TOKEN:
            raise RuntimeError("HUGGINGFACE_API_TOKEN not found for mode='hf'")
        if self.mode == "openrouter" and not OPENROUTER_KEY:
            raise RuntimeError("OPENROUTER_API_KEY not found for mode='openrouter'")

    @property
    def _llm_type(self) -> str:
        return "mistral"

    def _call_hf(self, prompt: str) -> str:
        url = f"{DEFAULT_HF_URL}/{self.hf_model}"
        headers = {"Authorization": f"Bearer {HF_TOKEN}"}
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": self.max_tokens,
                "temperature": float(self.temperature)
            }
        }
        r = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
        try:
            r.raise_for_status()
        except Exception as e:
            # include body for debug
            raise RuntimeError(f"HuggingFace API error {r.status_code}: {r.text}") from e
        data = r.json()
        if isinstance(data, list) and data and "generated_text" in data[0]:
            return data[0]["generated_text"]
        # fallback: try to parse 'generated_text' or return raw body
        return str(data)

    def _call_openrouter(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "Content-Type": "application/json"
        }
        # Build messages (system + user) for chat-style models.
        messages = [
            {"role": "user", "content": prompt},
        ]
        payload = {
            "model": self.openrouter_model,
            "messages": messages,
            # openrouter uses "max_tokens" in their chat completions (OpenAI-like)
            "max_tokens": int(self.max_tokens),
            "temperature": float(self.temperature)
        }

        r = requests.post(DEFAULT_OPENROUTER_URL, headers=headers, json=payload, timeout=self.timeout)
        # if request fails, raise with body to help debugging 400s
        if r.status_code >= 400:
            # include the server response to help identify why the request was bad
            body = r.text
            raise RuntimeError(f"OpenRouter API error {r.status_code}: {body}")
        data = r.json()
        # defensive access
        try:
            return data["choices"][0]["message"]["content"]
        except Exception:
            # return whole json if unexpected shape
            return str(data)

    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        if self.mode == "hf":
            return self._call_hf(prompt)
        elif self.mode == "openrouter":
            return self._call_openrouter(prompt)
        else:
            raise ValueError(f"Unknown mode: {self.mode}")

    def _generate(self, prompts: List[str], stop: Optional[List[str]] = None) -> LLMResult:
        generations = [[{"text": self._call(p, stop)}] for p in prompts]
        return LLMResult(generations=generations, llm_output={"token_usage": {}})