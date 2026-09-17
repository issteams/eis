"""Secret handling boundaries that avoid persistence and accidental disclosure."""

from __future__ import annotations

import os
from dataclasses import dataclass

from eis.security.runtime import RedactingProtector, SecurityError


@dataclass(frozen=True, slots=True)
class EnvironmentSecretProvider:
    """Read secrets on demand from environment variables without caching values."""

    prefix: str = ""

    def get(self, name: str) -> str | None:
        if not name or name.startswith("_") or "=" in name or ".." in name:
            raise SecurityError("invalid secret name")
        value = os.environ.get(f"{self.prefix}{name}")
        return value if value else None


__all__ = ["EnvironmentSecretProvider", "RedactingProtector"]
