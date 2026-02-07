from __future__ import annotations

from typing import Any, cast

from memu.llm.backends.base import EmbeddingBackend, LLMBackend


class GeminiLLMBackend(LLMBackend):
    """Backend for Google Gemini API."""

    name = "gemini"
    summary_endpoint = "" 

    def build_summary_payload(
        self, *, text: str, system_prompt: str | None, chat_model: str, max_tokens: int | None
    ) -> dict[str, Any]:
        parts = []
        if system_prompt:
             parts.append({"text": f"System Instruction: {system_prompt}\n\nUser Input: {text}"})
        else:
             parts.append({"text": text})

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": 0.2,
            }
        }
        if max_tokens:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens
            
        return payload

    def build_chat_payload(
        self, *, text: str, system_prompt: str | None, chat_model: str, max_tokens: int | None, temperature: float
    ) -> dict[str, Any]:
        parts = []
        if system_prompt:
             parts.append({"text": f"System Instruction: {system_prompt}\n\nUser Input: {text}"})
        else:
             parts.append({"text": text})

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": temperature,
            }
        }
        if max_tokens:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens
            
        return payload

    def parse_summary_response(self, data: dict[str, Any]) -> str:
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            if "error" in data:
                raise ValueError(f"Gemini API Error: {data['error']}")
            return ""

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
        
        text_part = {"text": prompt}
        if system_prompt:
             text_part["text"] = f"System Instruction: {system_prompt}\n\nUser Input: {prompt}"
             
        image_part = {
            "inline_data": {
                "mime_type": mime_type,
                "data": base64_image
            }
        }

        payload = {
            "contents": [{
                "parts": [text_part, image_part]
            }],
            "generationConfig": {
                "temperature": 0.2,
            }
        }
        if max_tokens:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens
            
        return payload


class GeminiEmbeddingBackend(EmbeddingBackend):
    name = "gemini"
    # This will be constructed in HTTPLLMClient usually, but here is default suffix
    # Actually for batch: :batchEmbedContents
    embedding_endpoint = ":batchEmbedContents" 

    def build_embedding_payload(self, *, inputs: list[str], embed_model: str) -> dict[str, Any]:
        requests = []
        model_name = f"models/{embed_model}" if not embed_model.startswith("models/") else embed_model
        for text in inputs:
            requests.append({
                "model": model_name,
                "content": {"parts": [{"text": text}]}
            })
        return {"requests": requests}

    def parse_embedding_response(self, data: dict[str, Any]) -> list[list[float]]:
        # Response: { "embeddings": [ { "values": [...] }, ... ] }
        if "embeddings" not in data:
             if "error" in data:
                 raise ValueError(f"Gemini Embedding Error: {data['error']}")
             return []
        return [item["values"] for item in data["embeddings"]]
