"""Public SDK facade.

The foundation intentionally exposes no autonomous behavior yet. Concrete capabilities
will be composed through dependency injection in later phases.
"""

from dataclasses import dataclass
from typing import Any

from eis.config import Settings, get_settings


@dataclass(frozen=True, slots=True)
class EISClient:
    settings: Settings

    @classmethod
    def from_environment(cls) -> "EISClient":
        return cls(settings=get_settings())

    def capabilities(self) -> dict[str, Any]:
        """Return declared capability configuration without claiming implementations."""
        return {
            "model_provider": self.settings.model_provider,
            "embedding_provider": self.settings.embedding_provider,
            "repository_provider": self.settings.repository_provider,
            "knowledge_backend": self.settings.knowledge_backend,
        }
