from __future__ import annotations

import asyncio

import httpx
import pytest

from eis.adapters.models import CloudflareModel, CloudflareProvider
from eis.config.settings import Settings
from eis.models import (
    EmbeddingRequest,
    GenerationRequest,
    ModelConfigurationError,
    StructuredGenerationRequest,
)
from eis.models.errors import ModelRateLimitError, ModelUnavailableError, ModelValidationError
from eis.models.registry import default_registry


class FakeResponse:
    def __init__(
        self,
        payload: dict,
        *,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        lines: tuple[str, ...] = (),
    ) -> None:
        self.payload = payload
        self.status_code = status_code
        self.headers = headers or {}
        self._lines = lines

    def json(self) -> dict:
        return self.payload

    async def aiter_lines(self):
        for line in self._lines:
            yield line


class FakeStreamContext:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response

    async def __aenter__(self) -> FakeResponse:
        return self.response

    async def __aexit__(self, *args: object) -> None:
        return None


class FakeAsyncClient:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response

    async def __aenter__(self) -> FakeAsyncClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def post(self, *args: object, **kwargs: object) -> FakeResponse:
        return self.response

    def stream(self, *args: object, **kwargs: object) -> FakeStreamContext:
        return FakeStreamContext(self.response)


def test_cloudflare_provider_builds_configured_model() -> None:
    async def run() -> None:
        settings = Settings(
            model_provider="cloudflare",
            model_name="@cf/meta/llama-3.1-8b-instruct",
            model_api_key="test-key",
            cloudflare_account_id="account-123",
        )
        provider = CloudflareProvider(settings)
        model = await provider.get_model()
        assert model.metadata.provider == "cloudflare"
        assert model.metadata.model == "@cf/meta/llama-3.1-8b-instruct"

    asyncio.run(run())


def test_default_registry_wires_cloudflare_provider() -> None:
    async def run() -> None:
        settings = Settings(
            model_provider="cloudflare",
            model_name="@cf/meta/llama-3.1-8b-instruct",
            model_api_key="test-key",
            cloudflare_account_id="account-123",
        )
        registry = default_registry(settings)
        model = await registry.resolve(settings)
        assert model.metadata.provider == "cloudflare"
        assert model.metadata.model == "@cf/meta/llama-3.1-8b-instruct"

    asyncio.run(run())


def test_default_registry_rejects_incomplete_cloudflare_configuration() -> None:
    with pytest.raises(ModelConfigurationError, match="cloudflare_account_id is required"):
        default_registry(
            Settings(
                model_provider="cloudflare",
                model_name="@cf/meta/llama-3.1-8b-instruct",
                model_api_key="test-key",
            )
        )


def test_cloudflare_model_uses_account_scoped_endpoint_and_gateway(monkeypatch) -> None:
    response = FakeResponse(
        {
            "choices": [
                {"message": {"content": "Cloudflare response", "tool_calls": []}}
            ],
            "usage": {"prompt_tokens": 4, "completion_tokens": 2},
        }
    )
    calls: list[tuple[object, object]] = []

    class RecordingClient(FakeAsyncClient):
        async def post(self, *args: object, **kwargs: object) -> FakeResponse:
            calls.append((args, kwargs))
            return self.response

    monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: RecordingClient(response))
    model = CloudflareModel(
        account_id="account-123",
        api_key="secret",
        model="@cf/meta/llama-3.1-8b-instruct",
        gateway_id="default",
    )

    async def run() -> None:
        generated = await model.generate(GenerationRequest("hello"))
        assert generated.text == "Cloudflare response"
        assert generated.usage.total_tokens == 6
        assert calls
        url = calls[0][0][0]
        headers = calls[0][1]["headers"]
        assert url == (
            "https://api.cloudflare.com/client/v4/accounts/"
            "account-123/ai/v1/chat/completions"
        )
        assert headers["Authorization"] == "Bearer secret"
        assert headers["cf-aig-gateway-id"] == "default"

    asyncio.run(run())


def test_cloudflare_model_supports_structured_generation_and_embeddings(monkeypatch) -> None:
    responses = iter(
        [
            FakeResponse(
                {
                    "choices": [{"message": {"content": '{"answer": "ok"}'}}],
                    "usage": {"prompt_tokens": 3, "completion_tokens": 2},
                }
            ),
            FakeResponse(
                {"data": [{"embedding": [1, 2.5]}], "usage": {"prompt_tokens": 2}}
            ),
        ]
    )

    class SequentialClient(FakeAsyncClient):
        async def post(self, *args: object, **kwargs: object) -> FakeResponse:
            return next(responses)

    monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: SequentialClient(None))
    model = CloudflareModel(
        account_id="account-123",
        api_key="secret",
        model="@cf/baai/bge-large-en-v1.5",
    )

    async def run() -> None:
        structured = await model.generate_structured(
            StructuredGenerationRequest("hello", schema={"type": "object"})
        )
        embedded = await model.embed(EmbeddingRequest(("hello",)))
        assert structured.data["answer"] == "ok"
        assert embedded.vectors == ((1.0, 2.5),)

    asyncio.run(run())


def test_cloudflare_model_streams_sse(monkeypatch) -> None:
    response = FakeResponse(
        {},
        lines=(
            'data: {"choices":[{"delta":{"content":"Hello"}}]}',
            'data: {"choices":[{"delta":{"content":" Cloudflare"}}]}',
            "data: [DONE]",
        ),
    )
    monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: FakeAsyncClient(response))
    model = CloudflareModel(
        account_id="account-123",
        api_key="secret",
        model="@cf/meta/llama-3.1-8b-instruct",
    )

    async def run() -> None:
        chunks = [chunk async for chunk in model.stream(GenerationRequest("hello"))]
        assert chunks == ["Hello", " Cloudflare"]

    asyncio.run(run())


def test_cloudflare_model_maps_http_errors() -> None:
    model = CloudflareModel(
        account_id="account-123",
        api_key="secret",
        model="@cf/meta/llama-3.1-8b-instruct",
    )

    async def run() -> None:
        with pytest.raises(ModelRateLimitError):
            await model._raise_for_status(
                httpx.Response(429, headers={"retry-after": "2"})
            )
        with pytest.raises(ModelUnavailableError):
            await model._raise_for_status(httpx.Response(503))
        with pytest.raises(ModelValidationError):
            await model._raise_for_status(httpx.Response(400))

    asyncio.run(run())


def test_cloudflare_model_requires_configuration() -> None:
    with pytest.raises(ModelConfigurationError):
        CloudflareModel(
            account_id="",
            api_key="secret",
            model="@cf/meta/llama-3.1-8b-instruct",
        )
