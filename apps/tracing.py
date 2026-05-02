from __future__ import annotations

from collections.abc import Mapping

from opentelemetry.propagate import extract, inject


def current_w3c_trace_headers() -> dict[str, str]:
    """Build outbound W3C propagation headers from current context."""
    carrier: dict[str, str] = {}
    inject(carrier)
    out: dict[str, str] = {}
    for key in ("traceparent", "tracestate"):
        value = str(carrier.get(key) or "").strip()
        if value:
            out[key] = value
    return out


def extract_w3c_context_from_headers(headers: Mapping[str, str] | dict) -> object:
    """Extract distributed tracing context from inbound headers."""
    carrier: dict[str, str] = {}
    for key in ("traceparent", "tracestate"):
        value = str(headers.get(key) or headers.get(key.title()) or "").strip()
        if value:
            carrier[key] = value
    return extract(carrier=carrier)


def is_valid_trace_id_hex(trace_id: str | None) -> bool:
    value = (trace_id or "").strip().lower()
    return len(value) == 32 and all(ch in "0123456789abcdef" for ch in value)
