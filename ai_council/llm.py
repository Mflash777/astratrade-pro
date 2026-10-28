"""Pluggable LLM interface.

Set LLM_PROVIDER to ``openai`` or ``anthropic`` and the matching API key to have
personas write their commentary with a hosted model. The default ``mock`` provider
returns ``None`` so personas fall back to their deterministic rule-based reasoning.
Numeric scoring is ALWAYS rule-based; the LLM only enriches the narrative.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod

import httpx


class LLMClient(ABC):
    @abstractmethod
    def complete(self, system: str, prompt: str, max_tokens: int = 300) -> str | None:
        """Return generated text, or None if unavailable."""


class MockLLM(LLMClient):
    def complete(self, system: str, prompt: str, max_tokens: int = 300) -> str | None:
        return None


class OpenAIClient(LLMClient):
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key, self.model = api_key, model

    def complete(self, system: str, prompt: str, max_tokens: int = 300) -> str | None:
        try:
            r = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "max_tokens": max_tokens,
                      "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]},
                timeout=30,
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
        except (httpx.HTTPError, KeyError, ValueError):
            return None


class AnthropicClient(LLMClient):
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key, self.model = api_key, model

    def complete(self, system: str, prompt: str, max_tokens: int = 300) -> str | None:
        try:
            r = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
                json={"model": self.model, "max_tokens": max_tokens, "system": system,
                      "messages": [{"role": "user", "content": prompt}]},
                timeout=30,
            )
            r.raise_for_status()
            return r.json()["content"][0]["text"].strip()
        except (httpx.HTTPError, KeyError, ValueError, IndexError):
            return None


def get_llm_client() -> LLMClient:
    provider = os.getenv("LLM_PROVIDER", "mock").lower()
    model = os.getenv("LLM_MODEL", "")
    if provider == "openai" and os.getenv("OPENAI_API_KEY"):
        return OpenAIClient(os.environ["OPENAI_API_KEY"], model or "gpt-4o-mini")
    if provider == "anthropic" and os.getenv("ANTHROPIC_API_KEY"):
        return AnthropicClient(os.environ["ANTHROPIC_API_KEY"], model or "claude-sonnet-4-5")
    return MockLLM()
