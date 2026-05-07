from __future__ import annotations

from apps.load.stream_disruption import (
    DisruptionConfig,
    apply_disruptions,
    generate_base_events,
    summarize_sequence_health,
)


def test_generate_base_events_seq_and_prefix():
    cfg = DisruptionConfig(total_events=5, event_prefix="t", sat_id="SAT-X")
    events = generate_base_events(cfg)
    assert len(events) == 5
    assert events[0]["event_id"] == "t-000000"
    assert events[4]["metadata"]["seq"] == 4
    assert events[2]["metadata"]["sat_id"] == "SAT-X"


def test_apply_disruptions_deterministic():
    cfg = DisruptionConfig(
        total_events=20,
        drop_probability=0.2,
        duplicate_probability=0.3,
        reorder_window=4,
        seed=7,
    )
    base = generate_base_events(cfg)
    out1, stats1 = apply_disruptions(base, cfg)
    out2, stats2 = apply_disruptions(base, cfg)
    assert stats1 == stats2
    assert [e["event_id"] for e in out1] == [e["event_id"] for e in out2]
    assert stats1["dropped"] >= 0
    assert stats1["duplicated"] >= 0


def test_summarize_sequence_health():
    health = summarize_sequence_health(
        expected_unique_after_transport=100,
        persisted_unique=98,
        dropped=10,
        duplicated=15,
    )
    assert health["missing_after_persist"] == 2
    assert health["stable"] is False
