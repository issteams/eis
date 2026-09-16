from eis.agents import protocols as agent_protocols
from eis.config import Settings, get_settings
from eis.core.errors import ConfigurationError, EISError
from eis.core.protocols import Decision, Evidence, Model
from eis.evaluation import protocols as evaluation_protocols
from eis.execution import protocols as execution_protocols
from eis.integrity import protocols as integrity_protocols
from eis.knowledge import protocols as knowledge_protocols
from eis.memory import protocols as memory_protocols
from eis.observability import logging as observability_logging
from eis.observability import protocols as observability_protocols
from eis.orchestration import protocols as orchestration_protocols
from eis.reasoning import protocols as reasoning_protocols
from eis.sdk import EISClient
from eis.security import protocols as security_protocols
from eis.tools import protocols as tool_protocols


def test_settings_are_typed_and_have_safe_defaults() -> None:
    settings = Settings()
    assert settings.environment == "development"
    assert settings.max_tool_calls == 20
    assert settings.model_provider == "none"


def test_get_settings_is_cached(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("EIS_MODEL_PROVIDER", "test-provider")
    first = get_settings()
    second = get_settings()
    assert first is second
    assert first.model_provider == "test-provider"
    get_settings.cache_clear()


def test_evidence_and_decision_are_immutable_value_objects() -> None:
    evidence = Evidence(source="test", content="fact")
    decision = Decision(conclusion="unknown", rationale="no evidence", evidence=(evidence,))
    assert decision.evidence[0].source == "test"
    assert decision.uncertainty is None


def test_client_does_not_claim_unimplemented_capabilities() -> None:
    client = EISClient(Settings())
    assert all(value == "none" for value in client.capabilities().values())


def test_client_can_load_from_environment(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("EIS_REPOSITORY_PROVIDER", "github")
    client = EISClient.from_environment()
    assert client.settings.repository_provider == "github"
    get_settings.cache_clear()


def test_error_hierarchy_is_stable() -> None:
    assert issubclass(ConfigurationError, EISError)


def test_protocol_is_runtime_checkable() -> None:
    class FakeModel:
        async def generate(self, prompt: str, *, system: str | None = None) -> str:
            return prompt

    assert isinstance(FakeModel(), Model)


def test_domain_protocol_modules_are_importable() -> None:
    modules = (
        agent_protocols,
        evaluation_protocols,
        execution_protocols,
        integrity_protocols,
        knowledge_protocols,
        memory_protocols,
        observability_protocols,
        orchestration_protocols,
        reasoning_protocols,
        security_protocols,
        tool_protocols,
    )
    assert all(module is not None for module in modules)


def test_logging_configuration_and_logger() -> None:
    observability_logging.configure_logging("INFO")
    logger = observability_logging.get_logger("eis.test")
    assert logger is not None
