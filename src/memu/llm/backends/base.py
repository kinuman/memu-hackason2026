from __future__ import annotations

from typing import Any


class LLMBackend:
    """Defines how to talk to a specific HTTP LLM provider."""

    name: str = "base"
    summary_endpoint: str = "/chat/completions"

    def build_summary_payload(
        self, *, text: str, system_prompt: str | None, chat_model: str, max_tokens: int | None
    ) -> dict[str, Any]:
        raise NotImplementedError

    def build_chat_payload(
        self, *, text: str, system_prompt: str | None, chat_model: str, max_tokens: int | None, temperature: float
    ) -> dict[str, Any]:
        """Build payload for generic chat completion."""
        # Default implementation can be same as summary if summary is generic enough,
        # but better to have separate.
        # For backward compatibility, we can just call build_summary_payload but ignoring temperature
        return self.build_summary_payload(text=text, system_prompt=system_prompt, chat_model=chat_model, max_tokens=max_tokens)

    def parse_summary_response(self, data: dict[str, Any]) -> str:
        raise NotImplementedError

    def build_vision_payload(
        self,
        *,
        prompt: str,
        base64_image: str,
        mime_type: str,
        system_prompt: str | None,
        chat_model: str,
        max_tokens: int | None,
    ) -> dict[str, Any]:
        raise NotImplementedError


class EmbeddingBackend:
    """Defines how to talk to a specific Embedding provider."""

    name: str
    embedding_endpoint: str

    def build_embedding_payload(self, *, inputs: list[str], embed_model: str) -> dict[str, Any]:
        raise NotImplementedError

    def parse_embedding_response(self, data: dict[str, Any]) -> list[list[float]]:
        raise NotImplementedError
