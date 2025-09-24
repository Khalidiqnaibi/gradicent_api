from typing import List, Optional
import requests,os
from langchain.llms.base import LLM
from langchain.schema import LLMResult

# Llama-3 inference endpoint (user must host Llama 3 in a model server like vLLM/TGI/Ollama)
LLAMA3_API_URL = os.environ.get("LLAMA3_API_URL", "http://127.0.0.1:8080/generate") 

class RemoteLLM(LLM):
    """Thin LangChain LLM wrapper for an HTTP text-generation endpoint.
    The remote endpoint must accept JSON: {"input": "text", "max_new_tokens": 256, ...}
    and return JSON: {"output": "<generated text>"} or similar.
    Adjust parse logic to match your server's response shape.
    """

    max_output_tokens: int = 512
    temperature: float = 0.0
    api_url: str = LLAMA3_API_URL
    headers: dict = None

    def __init__(self, api_url: Optional[str] = None, temperature: float = 0.0, max_output_tokens: int = 512, headers: dict = None):
        if api_url:
            self.api_url = api_url
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.headers = headers or {"Content-Type": "application/json"}

    @property
    def _llm_type(self) -> str:
        return "remote-llama3"

    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        payload = {
            "input": prompt,
            "max_new_tokens": self.max_output_tokens,
            "temperature": self.temperature,
        }
        # If your server expects other keys (e.g., "prompt"), change payload accordingly.
        try:
            resp = requests.post(self.api_url, json=payload, headers=self.headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            # Try to pick the text from common shapes
            if isinstance(data, dict):
                if "output" in data:
                    return data["output"]
                if "text" in data:
                    return data["text"]
                if "generated_text" in data:
                    return data["generated_text"]
                # TGI style: {"results":[{"text":"..."}]}
                if "results" in data and isinstance(data["results"], list):
                    return data["results"][0].get("text", "")
            # Fallback to full text
            return str(data)
        except Exception as e:
            raise RuntimeError(f"LLM call failed: {e}")

    def _generate(self, prompts: List[str], stop: Optional[List[str]] = None) -> LLMResult:
        results = []
        for p in prompts:
            txt = self._call(p, stop=stop)
            results.append({"text": txt})
        # Build LLMResult
        llm_output = {"token_usage": {}}
        generations = [[{"text": r["text"]}] for r in results]
        return LLMResult(generations=generations, llm_output=llm_output)

