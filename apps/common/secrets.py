"""
S3.7 — Secrets management stub.

Current behaviour:
- Reads secrets from environment variables (and thus from .env in local dev).

Future behaviour:
- Swap EnvSecretBackend for a real backend (Vault / cloud secret manager) without
  changing call sites that use get_secret().
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol


class SecretBackend(Protocol):
    """Interface for secrets backends."""

    def get(self, name: str) -> str | None:  # pragma: no cover - trivial interface
        ...


@dataclass
class EnvSecretBackend:
    """Default backend: environment variables (incl. values from .env for local dev)."""

    def get(self, name: str) -> str | None:
        return os.getenv(name)


_BACKEND: SecretBackend = EnvSecretBackend()


def set_backend(backend: SecretBackend) -> None:
    """
    Replace the current backend (used in tests or when wiring a real secrets service).

    Example in future:
        from apps.common.secrets import set_backend, VaultBackend
        set_backend(VaultBackend(...))
    """

    global _BACKEND
    _BACKEND = backend


def get_secret(name: str, default: str = "") -> str:
    """
    Fetch a secret by logical name.

    Today:
        - returns os.getenv(name) or default.
    Future:
        - will call a real backend (e.g. Vault) behind the same interface.
    """

    value = _BACKEND.get(name)
    return value if value is not None else default
