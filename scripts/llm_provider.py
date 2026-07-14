"""Provider abstraction for cached repository summaries."""
from __future__ import annotations

import json
import os
import urllib.request


def _post(url: str, payload: dict, headers: dict | None = None) -> dict:
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(request, timeout=150) as response:
        return json.load(response)


SUMMARY_PROMPT = (
    "Summarize this GitHub repository in 2-3 concise Korean sentences (한국어로 작성). "
    "State what it does, its key features, and its tech stack if mentioned; no marketing language. "
    "Reply only with the Korean summary, no English, no preamble.\\n\\n"
)


def call_ollama(readme: str, model: str) -> str:
    response = _post("http://127.0.0.1:11434/api/generate", {"model": model, "stream": False, "prompt": SUMMARY_PROMPT + readme})
    return response["response"].strip()


def call_anthropic(readme: str, model: str) -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is required when llm.provider is cloud")
    response = _post("https://api.anthropic.com/v1/messages", {"model": model, "max_tokens": 200, "messages": [{"role": "user", "content": SUMMARY_PROMPT + readme}]}, {"x-api-key": key, "anthropic-version": "2023-06-01"})
    return response["content"][0]["text"].strip()


def summarize(readme: str, settings: dict) -> str:
    provider = settings.get("provider", "local")
    if provider == "local":
        return call_ollama(readme, settings.get("model", "gemma4:e2b"))
    if provider == "cloud":
        return call_anthropic(readme, settings.get("model", "claude-3-5-haiku-latest"))
    raise ValueError(f"Unknown LLM provider: {provider}")
