"""Backend resolution and adapter dispatch (PS5.1)."""

from __future__ import annotations

import logging
from typing import Any, Callable

from config import settings

from apps.llm_backends.openai_compatible import (
    generate_cursor_sh,
    generate_gpu,
    generate_openai,
)
from apps.llm_gateway_errors import LLMGatewayProviderError

_logger = logging.getLogger(__name__)

_SUPPORTED_BACKENDS = frozenset({"openai", "cursor_sh", "gpu"})

_warned_provider_deprecated = False
_warned_provider_ignored = False


def resolve_llm_backend() -> str:
    """
    Resolve LLM_BACKEND per PS5.1 precedence:
    1. llm_backend if set
    2. legacy llm_provider if set (deprecated)
    3. default openai
    """
    global _warned_provider_deprecated, _warned_provider_ignored

    backend_raw = (getattr(settings, "llm_backend", "") or "").strip().lower()
    provider_raw = (getattr(settings, "llm_provider", "") or "").strip().lower()

    if backend_raw:
        if provider_raw:
            if not _warned_provider_ignored:
                _logger.warning(
                    "LLM_PROVIDER=%s ignored; routing uses LLM_BACKEND=%s",
                    provider_raw,
                    backend_raw,
                )
                _warned_provider_ignored = True
        return _validate_backend(backend_raw)

    if provider_raw:
        if not _warned_provider_deprecated:
            _logger.warning(
                "LLM_PROVIDER is deprecated; set LLM_BACKEND=%s instead",
                provider_raw,
            )
            _warned_provider_deprecated = True
        if provider_raw in ("openai", "cursor_sh"):
            return provider_raw
        raise LLMGatewayProviderError(
            f"Unsupported LLM_PROVIDER='{provider_raw}'. "
            f"Use LLM_BACKEND; supported: {sorted(_SUPPORTED_BACKENDS)}"
        )

    return "openai"


def _validate_backend(name: str) -> str:
    if name not in _SUPPORTED_BACKENDS:
        raise LLMGatewayProviderError(
            f"Unsupported LLM_BACKEND='{name}'. Supported: {sorted(_SUPPORTED_BACKENDS)}"
        )
    return name


def reset_backend_warnings_for_tests() -> None:
    """Allow tests to re-trigger one-time deprecation warnings."""
    global _warned_provider_deprecated, _warned_provider_ignored
    _warned_provider_deprecated = False
    _warned_provider_ignored = False


def get_backend_generator(backend: str) -> Callable[..., dict[str, Any]]:
    if backend == "openai":
        return generate_openai
    if backend == "cursor_sh":
        return generate_cursor_sh
    if backend == "gpu":
        return generate_gpu
    raise LLMGatewayProviderError(f"Unsupported LLM_BACKEND='{backend}'")
