"""Cloudflare Workers AI model adapter.

Uses Cloudflare's OpenAI-compatible Workers AI endpoint while keeping
Cloudflare-specific configuration isolated from EIS.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from eis.models.errors import (
    ModelConfigurationError,
    ModelRateLimitError,
    ModelUnavailableError,
    ModelValidationError,
)
from eis.models.interfaces import (
    EmbeddingRequest,
    EmbeddingResponse,
    GenerationRequest,
    GenerationResponse,
    ModelMetadata,
    StructuredGenerationRequest,
    StructuredGenerationResponse,
    ToolCall,
    Usage,
)


class CloudflareModel:
    """HTTP adapter for Cloudflare Workers AI."""

    def __init__(
        self,
        *,
        account_id: str,
        api_key: str,
        model: str,
        timeout: float = 60.0,
        gateway_id: str | None = None,
    ) -> None:
        if not account_id or not api_key or not model:
            raise ModelConfigurationError(
                "account_id, api_key, and model are required",
                provider="cloudflare",
            )
        self.account_id = account_id
        self.api_key = api_key
        self.gateway_id = gateway_id
        self.base_url = (
            f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1"
        )
        self._timeout = timeout
        self._metadata = ModelMetadata(
            provider="cloudflare",
            model=model,
            supports_structured_output=True,
            supports_tools=True,
            supports_streaming=True,
            supports_embeddings=True,
        )

    @property
    def metadata(self) -> ModelMetadata:
        return self._metadata

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        payload = self._chat_payload(request)
        data = await self._post("/chat/completions", payload, request.timeout)
        choice = data["choices"][0]
        message = choice["message"]
        calls = tuple(
            ToolCall(
                call["id"],
                call["function"]["name"],
                json.loads(call["function"]["arguments"]),
            )
            for call in message.get("tool_calls", [])
        )
        return GenerationResponse(
            text=message.get("content") or "",
            model=self._metadata,
            usage=self._usage(data.get("usage")),
            tool_calls=calls,
            raw=data,
            trace_id=request.trace_id,
        )

    async def generate_structured(
        self, request: StructuredGenerationRequest
    ) -> StructuredGenerationResponse:
        payload = self._chat_payload(request)
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "eis_response",
                "schema": dict(request.schema),
            },
        }
        data = await self._post("/chat/completions", payload, request.timeout)
        content = data["choices"][0]["message"].get("content") or "{}"
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ModelValidationError(
                "provider returned invalid structured JSON",
                provider="cloudflare",
            ) from exc
        if not isinstance(parsed, dict):
            raise ModelValidationError(
                "structured response must be a JSON object",
                provider="cloudflare",
            )
        return StructuredGenerationResponse(
            parsed,
            self._metadata,
            self._usage(data.get("usage")),
            data,
            request.trace_id,
        )

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        payload = {
            "model": request.model or self.metadata.model,
            "input": list(request.texts),
        }
        data = await self._post("/embeddings", payload, request.timeout)
        vectors = tuple(
            tuple(float(value) for value in item["embedding"])
            for item in data["data"]
        )
        return EmbeddingResponse(
            vectors,
            self._metadata,
            self._usage(data.get("usage")),
            request.trace_id,
        )

    async def stream(self, request: GenerationRequest) -> AsyncIterator[str]:
        payload = self._chat_payload(request)
        payload["stream"] = True
        headers = self._headers()
        try:
            async with (
                httpx.AsyncClient(timeout=request.timeout or self._timeout) as client,
                client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                ) as response,
            ):
                await self._raise_for_status(response)
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    value = line[5:].strip()
                    if value == "[DONE]":
                        return
                    chunk = json.loads(value)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    if delta.get("content"):
                        yield delta["content"]
        except httpx.TimeoutException as exc:
            raise ModelUnavailableError(
                "Cloudflare request timed out",
                provider="cloudflare",
            ) from exc
        except httpx.HTTPError as exc:
            raise ModelUnavailableError(
                "Cloudflare request failed",
                provider="cloudflare",
            ) from exc

    def _chat_payload(self, request: GenerationRequest) -> dict[str, Any]:
        messages: list[dict[str, Any]] = []
        if request.system:
            messages.append({"role": "system", "content": request.system})
        messages.append({"role": "user", "content": request.prompt})
        payload: dict[str, Any] = {
            "model": request.model or self.metadata.model,
            "messages": messages,
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": dict(tool.parameters),
                    },
                }
                for tool in request.tools
            ]
        return payload

    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.gateway_id:
            headers["cf-aig-gateway-id"] = self.gateway_id
        return headers

    async def _post(
        self,
        path: str,
        payload: dict[str, Any],
        timeout: float | None,
    ) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=timeout or self._timeout) as client:
                response = await client.post(
                    f"{self.base_url}{path}",
                    json=payload,
                    headers=self._headers(),
                )
                await self._raise_for_status(response)
                data = response.json()
                if not isinstance(data, dict):
                    raise ModelValidationError(
                        "Cloudflare returned an invalid response body",
                        provider="cloudflare",
                    )
                return data
        except httpx.TimeoutException as exc:
            raise ModelUnavailableError(
                "Cloudflare request timed out",
                provider="cloudflare",
            ) from exc
        except httpx.HTTPError as exc:
            raise ModelUnavailableError(
                "Cloudflare request failed",
                provider="cloudflare",
            ) from exc

    async def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code == 429:
            retry_after = response.headers.get("retry-after")
            raise ModelRateLimitError(
                "Cloudflare rate limit exceeded",
                retry_after=float(retry_after) if retry_after else None,
                provider="cloudflare",
            )
        if response.status_code >= 500:
            raise ModelUnavailableError(
                f"Cloudflare returned HTTP {response.status_code}",
                provider="cloudflare",
            )
        if response.status_code >= 400:
            raise ModelValidationError(
                f"Cloudflare returned HTTP {response.status_code}",
                provider="cloudflare",
            )

    @staticmethod
    def _usage(value: Any) -> Usage:
        if not isinstance(value, dict):
            return Usage()
        input_tokens = int(value.get("prompt_tokens") or value.get("input_tokens") or 0)
        output_tokens = int(
            value.get("completion_tokens") or value.get("output_tokens") or 0
        )
        return Usage(input_tokens, output_tokens, input_tokens + output_tokens)
