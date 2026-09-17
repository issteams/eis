from __future__ import annotations

from eis.sdk import EIS
from eis.sdk.models import EvaluationResult, TaskStatus


async def test_public_sdk_lifecycle() -> None:
    eis = EIS()
    product = eis.register_product("CraftIQ", "AI marketing platform")
    knowledge = eis.add_knowledge(
        "CraftIQ is an Echowavs product.",
        source="product-profile",
    )
    task = eis.create_task("Explain CraftIQ")

    assert product.name == "CraftIQ"
    assert eis.products() == (product,)
    assert eis.search_knowledge("CraftIQ") == (knowledge,)
    assert eis.task_result(task.id) is not None
    assert eis.task_result(task.id).status is TaskStatus.QUEUED


async def test_agent_execution_updates_task_and_audit() -> None:
    eis = EIS()
    eis.register_agent("writer", lambda task: f"done: {task.objective}")
    task = eis.create_task("write a summary")

    result = await eis.run_agent("writer", task)

    assert result.completed is True
    assert result.output == "done: write a summary"
    assert eis.task_result(task.id).status is TaskStatus.COMPLETED
    assert any(entry.action == "agent.run" and entry.result == "success" for entry in eis.audit_history())


async def test_evaluation_requires_stable_result() -> None:
    eis = EIS()
    result = await eis.evaluate_idea(
        "Build a desktop EIS app",
        lambda subject: EvaluationResult(subject, "promising", "Fits the roadmap"),
    )

    assert result.subject == "Build a desktop EIS app"
    assert result.conclusion == "promising"


async def test_engineering_adapter_and_audit() -> None:
    eis = EIS()
    task = eis.create_task("add a health endpoint")
    result = await eis.execute_engineering(
        task,
        lambda _: type("Engineering", (), {"status": "completed", "summary": "implemented"})(),
    )

    assert result.status == "completed"
    assert result.summary == "implemented"
    assert eis.audit_history(limit=1)[0].action == "engineering.execute"


def test_public_exports_do_not_require_internal_runtime_objects() -> None:
    import eis.sdk as sdk

    assert hasattr(sdk, "EIS")
    assert hasattr(sdk, "Task")
    assert hasattr(sdk, "EvaluationResult")
