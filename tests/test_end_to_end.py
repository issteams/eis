from eis import EIS
from eis.sdk import EvaluationResult


async def test_public_sdk_end_to_end_flow() -> None:
    runtime = EIS()

    runtime.register_product("Example", "release smoke test")
    runtime.add_knowledge("Traceable fact", source="release-test", title="Fact")
    runtime.remember("Release smoke memory")

    task = runtime.create_task("Run the release smoke flow")
    runtime.register_agent("smoke", lambda current: {"objective": current.objective})
    agent_result = await runtime.run_agent("smoke", task)

    runtime.register_tool("echo", lambda value: value)
    execution = await runtime.execute("echo", "ok")

    evaluation = await runtime.evaluate_idea(
        "release smoke",
        lambda subject: EvaluationResult(
            subject=subject,
            conclusion="pass",
            rationale="The deterministic release smoke flow completed.",
            uncertainty="None in this local smoke test.",
        ),
    )

    assert runtime.search_knowledge("traceable")
    assert runtime.memories()
    assert agent_result.completed
    assert execution.success
    assert evaluation.conclusion == "pass"
    assert runtime.task_result(task.id) is not None
    assert runtime.audit_history()
