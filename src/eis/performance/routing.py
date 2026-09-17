"""Deterministic model routing that preserves explicit model choices."""

from __future__ import annotations

from dataclasses import dataclass, field

from eis.models.interfaces import GenerationRequest, Model, ModelMetadata


@dataclass(frozen=True, slots=True)
class ModelRoute:
    """A model candidate with operational characteristics, not a quality claim."""

    name: str
    model: Model
    price_per_million_input: float = 0.0
    price_per_million_output: float = 0.0
    max_concurrency: int = 8
    preferred_tasks: frozenset[str] = frozenset()
    max_context_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class RoutingPolicy:
    """Routing policy; explicit model requests always take precedence."""

    default_route: str
    task_routes: dict[str, str] = field(default_factory=dict)
    expensive_tasks: frozenset[str] = frozenset({"verification", "security_review"})
    cacheable_tasks: frozenset[str] = frozenset({"classification", "drafting", "summarization"})


class ModelRouter:
    """Select a registered model without changing evidence or verification requirements."""

    def __init__(self, routes: list[ModelRoute], policy: RoutingPolicy) -> None:
        self._routes = {route.name: route for route in routes}
        if policy.default_route not in self._routes:
            raise ValueError("default route is not registered")
        for route_name in policy.task_routes.values():
            if route_name not in self._routes:
                raise ValueError(f"unknown route: {route_name}")
        self.policy = policy

    def route(self, request: GenerationRequest) -> ModelRoute:
        explicit = request.model
        if explicit:
            for route in self._routes.values():
                if route.model.metadata.model == explicit or route.name == explicit:
                    return route
        task = str(request.metadata.get("task_type", "general"))
        route_name = self.policy.task_routes.get(task, self.policy.default_route)
        return self._routes[route_name]

    def prepare(self, request: GenerationRequest) -> tuple[ModelRoute, GenerationRequest]:
        route = self.route(request)
        if request.model:
            return route, request
        return route, GenerationRequest(
            prompt=request.prompt,
            system=request.system,
            model=route.model.metadata.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            tools=request.tools,
            metadata=request.metadata,
            timeout=request.timeout,
            trace_id=request.trace_id,
        )

    def estimate_cost(self, route: ModelRoute, input_tokens: int, output_tokens: int) -> float:
        return (
            input_tokens * route.price_per_million_input
            + output_tokens * route.price_per_million_output
        ) / 1_000_000

    def metadata(self) -> list[ModelMetadata]:
        return [route.model.metadata for route in self._routes.values()]
