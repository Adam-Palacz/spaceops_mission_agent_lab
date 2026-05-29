"""
PS5.8 — Optional in-process capture of gateway metadata for parity evals.

When active, each successful apps.llm_gateway.generate() appends one provenance record.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator

_provenance_buffer: ContextVar[list[dict[str, Any]] | None] = ContextVar(
    "llm_provenance_buffer",
    default=None,
)


@contextmanager
def capture_llm_provenance() -> Iterator[list[dict[str, Any]]]:
    """Collect gateway metadata for the duration of the context."""
    buf: list[dict[str, Any]] = []
    token = _provenance_buffer.set(buf)
    try:
        yield buf
    finally:
        _provenance_buffer.reset(token)


def record_gateway_provenance(
    *,
    node: str,
    backend_requested: str,
    backend_actual: str,
    fallback_used: bool,
    fallback_reason: str,
) -> None:
    """Append one generate() record when capture is active (best-effort)."""
    buf = _provenance_buffer.get()
    if buf is None:
        return
    buf.append(
        {
            "call_index": len(buf),
            "node": node,
            "backend_requested": backend_requested,
            "backend_actual": backend_actual,
            "fallback_used": bool(fallback_used),
            "fallback_reason": str(fallback_reason or ""),
        }
    )
