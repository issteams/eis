from __future__ import annotations

import asyncio

import pytest

from eis.adapters.models import OpenAICompatibleModel, OpenAICompatibleProvider
from eis.config.settings import Settings
from eis.models import (
    EmbeddingRequest,
    GenerationRequest,
    GenerationResponse,
    ModelConfigurationError,
    RetryPolicy,
    StructuredGenerationRequest,
    ToolDefinition,
    Usage,
)
from eis.models.errors import ModelTimeoutError
from eis.models.fakes import FakeModel, FakeModelProvider
from eis.models.registry import ModelRegistry
from eis.models.runtime import ReliableModel


def test_fake_model_supports_generation_structured_embeddings_and_streaming() -> None:
    async def run() -> None:
        model = FakeModel()
        response = await model.generate(GenerationRequest("hello", trace_id="trace-1"))
        assert response.text == "fake response"
        structured = await model.generate_structured(
            StructuredGenerationRequest("hello", schema={"type": "object"})
        )
        assert structured.data["response"] == "fake response"
        embeddings = await model.embed(EmbeddingRequest(("a", "b")))
        assert len(embeddings.vectors) == 2
        chunks = [chunk async for chunk in model.stream(GenerationRequest("hello"))]
        assert chunks == ["fake", "response"]

    asyncio.run(run())


def test_reliable_model_retries_transient_failures_and_tracks_usage() -> None:
    async def run() -> None:
        model = FakeModel()
        model.failures = 2
        reliable = ReliableModel(model, retry_policy=RetryPolicy(max_attempts=3, initial_delay=0))
        response = await reliable.generate(GenerationRequest("hello", timeout=1))
        assert response.text == "fake response"
        assert reliable.usage.requests == 1
        assert reliable.usage.input_tokens == 3
        assert reliable.usage.output_tokens == 2
        assert reliable.traces[0].attempts == 3

    asyncio.run(run())


def test_reliable_model_timeout_becomes_structured_error() -> None:
    class SlowModel(FakeModel):
        async def generate(self, request: GenerationRequest) -> GenerationResponse:
            await asyncio.sleep(0.02)
            return await super().generate(request)

    async def run() -> None:
        reliable = ReliableModel(SlowModel(), retry_policy=RetryPolicy(max_attempts=1))
        with pytest.raises(ModelTimeoutError):
            await reliable.generate(GenerationRequest("hello", timeout=0.001))

    asyncio.run(run())


def test_registry_selects_configured_provider() -> None:
    async def run() -> None:
        fake = FakeModelProvider()
        registry = ModelRegistry({"fake": fake})
        settings = Settings(model_provider="fake", model_name="test")
        model = await registry.resolve(settings)
        assert model.metadata.provider == "fake"
        assert model.metadata.model == "fake-model"

    asyncio.run(run())


def test_registry_rejects_missing_provider() -> None:
    async def run() -> None:
        registry = ModelRegistry({})
        with pytest.raises(ModelConfigurationError):
            await registry.resolve(Settings(model_provider="none"))

    asyncio.run(run())


def test_registry_rejects_unknown_provider() -> None:
    async def run() -> None:
        registry = ModelRegistry({})
        with pytest.raises(ModelConfigurationError):
            await registry.resolve(Settings(model_provider="unknown"))

    asyncio.run(run())


def test_openai_compatible_provider_builds_configured_model() -> None:
    async def run() -> None:
        settings = Settings(
            model_provider="openrouter",
            model_name="example-model",
            model_base_url="https://example.test/v1",
            model_api_key="secret",
        )
        provider = OpenAICompatibleProvider(settings)
        model = await provider.get_model()
        assert model.metadata.provider == "openrouter"
        assert model.metadata.model == "example-model"

    asyncio.run(run())


def test_usage_and_retry_policy_validate_inputs() -> None:
    with pytest.raises(ValueError):
        Usage(input_tokens=-1)
    with pytest.raises(ValueError):
        RetryPolicy(max_attempts=0)
    with pytest.raises(ValueError):
        RetryPolicy(initial_delay=2, max_delay=1)


def test_openai_compatible_adapter_translates_tool_definition() -> None:
    adapter = OpenAICompatibleModel(
        provider="openrouter",
        base_url="https://example.test/v1",
        api_key="secret",
        model="example-model",
    )
    payload = adapter._chat_payload(
        GenerationRequest(
            "hello",
            tools=(ToolDefinition("search", "Search", {"type": "object"}),),
        )
    )
    assert payload["model"] == "example-model"
    assert payload["tools"][0]["function"]["name"] == "search"
