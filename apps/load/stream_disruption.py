from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


@dataclass
class DisruptionConfig:
    total_events: int = 120
    drop_probability: float = 0.10
    duplicate_probability: float = 0.15
    reorder_window: int = 8
    seed: int = 42
    sat_id: str = "SAT-PS36"
    event_prefix: str = "ps36"


def generate_base_events(cfg: DisruptionConfig) -> list[dict[str, Any]]:
    t0 = datetime(2026, 5, 7, 12, 0, 0, tzinfo=timezone.utc)
    out: list[dict[str, Any]] = []
    for i in range(cfg.total_events):
        ts = t0 + timedelta(seconds=i)
        out.append(
            {
                "event_id": f"{cfg.event_prefix}-{i:06d}",
                "ts": ts.isoformat().replace("+00:00", "Z"),
                "channel": "power.bus_voltage",
                "value": 28.5 + (i % 3) * 0.1,
                "metadata": {"seq": i, "sat_id": cfg.sat_id},
            }
        )
    return out


def apply_disruptions(
    events: list[dict[str, Any]],
    cfg: DisruptionConfig,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    rng = random.Random(cfg.seed)
    kept: list[dict[str, Any]] = []
    dropped = 0
    duplicated = 0

    # drop + duplicate stage
    for ev in events:
        if rng.random() < cfg.drop_probability:
            dropped += 1
            continue
        kept.append(ev)
        if rng.random() < cfg.duplicate_probability:
            kept.append(dict(ev))
            duplicated += 1

    # reorder stage (bounded shuffle windows)
    emitted: list[dict[str, Any]] = []
    win = max(1, cfg.reorder_window)
    for i in range(0, len(kept), win):
        block = kept[i : i + win]
        rng.shuffle(block)
        emitted.extend(block)

    return emitted, {"dropped": dropped, "duplicated": duplicated}


def summarize_sequence_health(
    *,
    expected_unique_after_transport: int,
    persisted_unique: int,
    dropped: int,
    duplicated: int,
) -> dict[str, Any]:
    missing_after_persist = max(0, expected_unique_after_transport - persisted_unique)
    return {
        "expected_unique_after_transport": expected_unique_after_transport,
        "persisted_unique": persisted_unique,
        "missing_after_persist": missing_after_persist,
        "transport_dropped": dropped,
        "transport_duplicated": duplicated,
        "stable": missing_after_persist == 0,
    }
