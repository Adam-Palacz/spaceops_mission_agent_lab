"""
PS5.8 — Optional in-process capture of gateway metadata for parity evals.

When active, each successful apps.llm_gateway.generate() appends one provenance record.

Uses a process-wide capture stack (not ContextVar) so records are collected when the agent
graph runs on a ThreadPoolExecutor worker (PS1.9 graph timeout path).
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Any, Iterator

_lock = threading.Lock()
_capture_stack: list[list[dict[str, Any]]] = []


@contextmanager
def capture_llm_provenance() -> Iterator[list[dict[str, Any]]]:
    """Collect gateway metadata for the duration of the context."""
    buf: list[dict[str, Any]] = []
    with _lock:
        _capture_stack.append(buf)
    try:
        yield buf
    finally:
        with _lock:
            if _capture_stack and _capture_stack[-1] is buf:
                _capture_stack.pop()


def record_gateway_provenance(
    *,
    node: str,
    backend_requested: str,
    backend_actual: str,
    fallback_used: bool,
    fallback_reason: str,
    backend_routing_reason: str = "",
) -> None:
    """Append one generate() record when capture is active (best-effort)."""
    with _lock:
        if not _capture_stack:
            return
        buf = _capture_stack[-1]
        buf.append(
            {
                "call_index": len(buf),
                "node": node,
                "backend_requested": backend_requested,
                "backend_actual": backend_actual,
                "fallback_used": bool(fallback_used),
                "fallback_reason": str(fallback_reason or ""),
                "backend_routing_reason": str(backend_routing_reason or ""),
            }
        )


def reset_provenance_capture_for_tests() -> None:
    """Clear any stale capture stack (test isolation)."""
    with _lock:
        _capture_stack.clear()
