from __future__ import annotations

import json

from apps.replay.queue_replay import ReplayItem, dedupe_replay_items, parse_id_csv


def test_parse_id_csv():
    assert parse_id_csv("1, 2,3") == [1, 2, 3]
    assert parse_id_csv("") == []


def test_dedupe_replay_items_by_event_id():
    items = [
        ReplayItem(
            source="dlq", key="dlq:1", event_id="evt-1", payload={"event_id": "evt-1"}
        ),
        ReplayItem(
            source="dlq", key="dlq:2", event_id="evt-1", payload={"event_id": "evt-1"}
        ),
        ReplayItem(
            source="dlq", key="dlq:3", event_id="evt-2", payload={"event_id": "evt-2"}
        ),
    ]
    deduped, dup = dedupe_replay_items(items)
    assert len(deduped) == 2
    assert dup == 1


def test_replay_queue_main_dry_run(monkeypatch, capsys):
    import scripts.replay_queue as rq

    monkeypatch.setattr(
        rq,
        "_collect_items",
        lambda **_kwargs: [
            ReplayItem(
                source="dlq",
                key="dlq:1",
                event_id="evt-1",
                payload={"event_id": "evt-1"},
            )
        ],
    )

    async def _should_not_publish(_items):
        raise RuntimeError("should not publish in dry-run")

    monkeypatch.setattr(rq, "_publish_items", _should_not_publish)
    monkeypatch.setattr(
        "sys.argv",
        ["replay_queue.py", "--dlq-ids", "1"],
    )
    rc = rq.main()
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out.split("Dry-run only.")[0].strip())
    assert payload["mode"] == "dry-run"
    assert payload["to_replay"] == 1


def test_replay_queue_main_apply(monkeypatch, capsys):
    import scripts.replay_queue as rq

    monkeypatch.setattr(
        rq,
        "_collect_items",
        lambda **_kwargs: [
            ReplayItem(
                source="dlq",
                key="dlq:1",
                event_id="evt-1",
                payload={"event_id": "evt-1"},
            ),
            ReplayItem(
                source="dlq",
                key="dlq:2",
                event_id="evt-1",
                payload={"event_id": "evt-1"},
            ),
        ],
    )

    async def _publish(_items):
        return (1, 0)

    monkeypatch.setattr(rq, "_publish_items", _publish)
    monkeypatch.setattr(
        "sys.argv",
        ["replay_queue.py", "--dlq-ids", "1,2", "--apply"],
    )
    rc = rq.main()
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload["mode"] == "apply"
    assert payload["local_duplicates_filtered"] == 1
    assert payload["published"] == 1
