import pytest

from eis.agents import protocols as agent_protocols
from eis.config import (
    CompanyConfig,
    DivisionConfig,
    Environment,
    ProductConfig,
    ProjectConfig,
    Settings,
    get_settings,
)
from eis.core import (
    CompanyIdentity,
    CorrelationId,
    DivisionIdentity,
    EISContext,
    EISEvent,
    EISIdentity,
    EISRuntime,
    OrganizationHierarchy,
    ProductIdentity,
    ProjectIdentity,
    RepositoryIdentity,
    RequestIdentity,
    Result,
    RuntimeState,
    SessionIdentity,
    Status,
    TaskIdentity,
)
from eis.core.errors import ConfigurationError, EISError, LifecycleError
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
    assert settings.environment == Environment.DEVELOPMENT
    assert settings.max_tool_calls == 20
    assert settings.model_provider == "none"
    assert settings.runtime_name == "eis"


def test_environment_and_runtime_name_are_loaded_from_environment() -> None:
    settings = Settings(_env_file=None, environment="production", runtime_name="runtime-test")
    assert settings.environment is Environment.PRODUCTION
    assert settings.runtime_name == "runtime-test"


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
    assert issubclass(LifecycleError, EISError)


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


def test_identities_are_unique_and_named() -> None:
    first = CompanyIdentity.create("Example Company")
    second = CompanyIdentity.create("Example Company")
    assert first.name == "Example Company"
    assert first.id != second.id
    assert isinstance(EISIdentity.create("runtime"), EISIdentity)
    assert isinstance(ProductIdentity.create("product"), ProductIdentity)
    assert isinstance(DivisionIdentity.create("division"), DivisionIdentity)
    assert isinstance(ProjectIdentity.create("project"), ProjectIdentity)
    assert isinstance(RepositoryIdentity.create("repo"), RepositoryIdentity)
    assert isinstance(TaskIdentity.create("task"), TaskIdentity)
    assert isinstance(SessionIdentity.create("session"), SessionIdentity)
    assert isinstance(RequestIdentity.create(), RequestIdentity)
    assert str(CorrelationId.create())


def test_identity_rejects_blank_names() -> None:
    with pytest.raises(ValueError):
        CompanyIdentity.create("   ")


def test_hierarchy_preserves_scope_without_product_hardcoding() -> None:
    hierarchy = OrganizationHierarchy(
        company=CompanyIdentity.create("Example Company"),
        division=DivisionIdentity.create("Engineering"),
        product=ProductIdentity.create("Product X"),
        project=ProjectIdentity.create("Project Y"),
        repository=RepositoryIdentity.create("repo-z"),
        task=TaskIdentity.create("task-1"),
    )
    assert hierarchy.scope() == (
        "Example Company / Engineering / Product X / Project Y / repo-z / task-1"
    )
    assert len(hierarchy.ids()) == 6


def test_organization_configuration_is_generic() -> None:
    config = CompanyConfig(
        name="Configured Company",
        divisions=(
            DivisionConfig(
                name="Division A",
                products=(
                    ProductConfig(
                        name="Product A",
                        projects=(ProjectConfig(name="Project A"),),
                    ),
                ),
            ),
        ),
    )
    assert config.divisions[0].products[0].projects[0].name == "Project A"


def test_context_carries_request_session_correlation_and_metadata() -> None:
    hierarchy = OrganizationHierarchy(company=CompanyIdentity.create("Company"))
    session = SessionIdentity.create("session-1")
    request = RequestIdentity.create("request-1")
    context = EISContext(
        hierarchy=hierarchy,
        session=session,
        request=request,
        correlation_id=CorrelationId.create(),
        metadata={"source": "test"},
    )
    child = context.child(metadata={"step": "one"})
    assert child.correlation_id == context.correlation_id
    assert child.metadata == {"source": "test", "step": "one"}


def test_runtime_lifecycle_context_and_events() -> None:
    runtime = EISRuntime(Settings(runtime_name="test-runtime"))
    assert runtime.state is RuntimeState.CREATED
    runtime.start()
    assert runtime.state is RuntimeState.STARTED
    events: list[EISEvent] = []
    runtime.subscribe(events.append)
    event = EISEvent(event_type="runtime.started", correlation_id=CorrelationId.create())
    runtime.emit(event)
    assert events == [event]
    context = runtime.create_context(
        OrganizationHierarchy(company=CompanyIdentity.create("Company"))
    )
    assert context.hierarchy.company.name == "Company"
    runtime.stop()
    assert runtime.state is RuntimeState.STOPPED


def test_runtime_cannot_restart_after_stop() -> None:
    runtime = EISRuntime(Settings())
    runtime.start()
    runtime.stop()
    with pytest.raises(LifecycleError):
        runtime.start()


def test_runtime_from_environment() -> None:
    runtime = EISRuntime.from_environment()
    assert runtime.settings.environment is Environment.DEVELOPMENT


def test_structured_event_requires_valid_type_and_timezone() -> None:
    with pytest.raises(ValueError):
        EISEvent(event_type="   ", correlation_id=CorrelationId.create())


def test_result_status_and_success_failure() -> None:
    success = Result.success("done")
    failure = Result.failure("broken")
    cancelled = Result.failure("cancelled", status=Status.CANCELLED)
    assert success.ok and success.value == "done"
    assert not failure.ok and failure.error == "broken"
    assert cancelled.status is Status.CANCELLED
    with pytest.raises(ValueError):
        Result.failure("   ")
