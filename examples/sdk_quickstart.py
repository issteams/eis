"""Minimal EIS SDK workflow.

Run from an installed checkout with:
    python examples/sdk_quickstart.py
"""

import asyncio

from eis import EIS
from eis.sdk import EvaluationResult


async def main() -> None:
    eis = EIS()

    product = eis.register_product("CraftIQ", "AI marketing platform")
    eis.add_knowledge(
        "CraftIQ is an Echowavs product.",
        source="product-profile",
        title="CraftIQ",
    )

    task = eis.create_task("Describe the product")
    eis.register_agent("assistant", lambda current: f"Task: {current.objective}")
    agent_result = await eis.run_agent("assistant", task)

    evaluation = await eis.evaluate_idea(
        "Build a desktop EIS application",
        lambda subject: EvaluationResult(
            subject=subject,
            conclusion="needs-review",
            rationale="Review deployment, persistence, and security requirements.",
            uncertainty="Implementation scope is not yet estimated.",
        ),
    )

    print(product)
    print(agent_result)
    print(evaluation)
    print(eis.task_result(task.id))
    print(eis.audit_history())


if __name__ == "__main__":
    asyncio.run(main())
