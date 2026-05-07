from __future__ import annotations

from apps.load.contact_window import ContactWindowConfig, apply_contact_windows


def _event(i: int) -> dict[str, object]:
    return {"event_id": f"e-{i}", "metadata": {"seq": i}}


def test_buffered_events_flush_on_contact_open_without_duplication():
    events = [_event(i) for i in range(8)]
    cfg = ContactWindowConfig(
        cycle_on_events=2,
        cycle_off_events=2,
        off_mode="buffer",
        dedupe_on_flush=True,
    )
    result = apply_contact_windows(events, cfg)
    ids = [str(ev["event_id"]) for ev in result.emitted]
    assert ids == [f"e-{i}" for i in range(8)]
    assert result.buffered_total == 4
    assert result.flushed_total == 4
    assert result.dropped_total == 0
    assert result.duplicates_filtered == 0


def test_drop_mode_discards_off_window_events():
    events = [_event(i) for i in range(6)]
    cfg = ContactWindowConfig(
        cycle_on_events=1,
        cycle_off_events=1,
        off_mode="drop",
    )
    result = apply_contact_windows(events, cfg)
    ids = [str(ev["event_id"]) for ev in result.emitted]
    assert ids == ["e-0", "e-2", "e-4"]
    assert result.dropped_total == 3


def test_explicit_intervals_can_drive_test_schedules():
    events = [_event(i) for i in range(6)]
    cfg = ContactWindowConfig(
        off_mode="buffer",
        explicit_on_intervals=[(0, 1), (3, 4), (5, 6)],
    )
    result = apply_contact_windows(events, cfg)
    ids = [str(ev["event_id"]) for ev in result.emitted]
    assert ids == [f"e-{i}" for i in range(6)]
    assert result.buffered_total == 3
    assert result.flushed_total == 3
