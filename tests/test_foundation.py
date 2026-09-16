from eis.config import Settings
from eis.core.errors import ConfigurationError, EISError
from eis.core.protocols import Decision, Evidence, Model
from eis.sdk import EISClient


def test_settings_are_typed_and_have_safe_defaults() -> None:
    settings = Settings()
    assert settings.environment == "development"
    assert settings.max_tool_calls == 20
    assert settings.model_provider == "none"


def test_evidence_and_decision_are_immutable_value_objects() -> None:
    evidence = Evidence(source="test", content="fact")
    decision = Decision(conclusion="unknown", rationale="no evidence", evidence=(evidence,))
    assert decision.evidence[0].source == "test"
    assert decision.uncertainty is None


def test_client_does_not_claim_unimplemented_capabilities() -> None:
    client = EISClient(Settings())
    assert all(value == "none" for value in client.capabilities().values())


def test_error_hierarchy_is_stable() -> None:
    assert issubclass(ConfigurationError, EISError)


def test_protocol_is_runtime_checkable() -> None:
    class FakeModel:
        async def generate(self, prompt: str, *, system: str | None = None) -> str:
            return prompt

    assert isinstance(FakeModel(), Model)
