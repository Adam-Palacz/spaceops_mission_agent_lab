from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ContactWindowConfig:
    cycle_on_events: int = 20
    cycle_off_events: int = 40
    off_mode: str = "buffer"  # "buffer" or "drop"
    dedupe_on_flush: bool = True
    flush_remaining_at_end: bool = True
    explicit_on_intervals: list[tuple[int, int]] = field(default_factory=list)


@dataclass
class ContactWindowResult:
    emitted: list[dict[str, Any]]
    buffered_total: int
    flushed_total: int
    dropped_total: int
    duplicates_filtered: int


def _is_contact_on(idx: int, cfg: ContactWindowConfig) -> bool:
    if cfg.explicit_on_intervals:
        for start, end in cfg.explicit_on_intervals:
            if start <= idx < end:
                return True
        return False
    on = max(1, int(cfg.cycle_on_events))
    off = max(1, int(cfg.cycle_off_events))
    mod = idx % (on + off)
    return mod < on


def apply_contact_windows(
    events: list[dict[str, Any]], cfg: ContactWindowConfig
) -> ContactWindowResult:
    emitted: list[dict[str, Any]] = []
    buffer: list[dict[str, Any]] = []
    seen_event_ids: set[str] = set()
    buffered_total = 0
    flushed_total = 0
    dropped_total = 0
    duplicates_filtered = 0
    prev_on = True

    def append_event(ev: dict[str, Any]) -> None:
        nonlocal duplicates_filtered
        if not cfg.dedupe_on_flush:
            emitted.append(ev)
            return
        event_id = str(ev.get("event_id") or "").strip()
        if not event_id:
            emitted.append(ev)
            return
        if event_id in seen_event_ids:
            duplicates_filtered += 1
            return
        seen_event_ids.add(event_id)
        emitted.append(ev)

    for idx, ev in enumerate(events):
        is_on = _is_contact_on(idx, cfg)
        if is_on and not prev_on and buffer:
            for b in buffer:
                append_event(b)
            flushed_total += len(buffer)
            buffer = []

        if is_on:
            append_event(ev)
        else:
            mode = (cfg.off_mode or "buffer").strip().lower()
            if mode == "drop":
                dropped_total += 1
            else:
                buffer.append(ev)
                buffered_total += 1
        prev_on = is_on

    # Simulation hook: optionally flush pending buffer at end-of-stream.
    if buffer and cfg.flush_remaining_at_end:
        for b in buffer:
            append_event(b)
        flushed_total += len(buffer)

    return ContactWindowResult(
        emitted=emitted,
        buffered_total=buffered_total,
        flushed_total=flushed_total,
        dropped_total=dropped_total,
        duplicates_filtered=duplicates_filtered,
    )
