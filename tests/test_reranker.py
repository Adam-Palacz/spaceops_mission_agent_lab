"""
P4.4 — Reranker for KB RAG.

These tests focus on the deterministic local reranker used by default:
`rerank_lexical()` / `rerank_chunks(mode='lexical')`.
"""

from __future__ import annotations

from apps.common.reranker import rerank_chunks


def test_rerank_lexical_changes_order_for_relevant_chunk():
    query = "restart heater controller threshold"
    chunks = [
        {
            "content": "Telemetry bus voltage is low; investigate Power subsystem.",
            "doc_id": "unrelated.md",
        },
        {
            "content": "To restart the heater controller, verify threshold settings and controller health.",
            "doc_id": "heater_restart.md",
        },
        {
            "content": "Change configuration thresholds for Thermal subsystem.",
            "doc_id": "thresholds.md",
        },
    ]

    ranked = rerank_chunks(query, chunks, mode="lexical")

    # The chunk containing "restart" + "heater controller" should rank first.
    assert ranked[0]["doc_id"] == "heater_restart.md"

    # Unrelated telemetry chunk should not be first.
    assert ranked[0]["doc_id"] != "unrelated.md"


def test_rerank_lexical_tie_break_prefers_shorter_snippet():
    query = "channel bus_voltage"
    chunks = [
        {"content": "bus_voltage bus_voltage", "doc_id": "short.md"},
        {"content": "bus_voltage bus_voltage more more more", "doc_id": "long.md"},
    ]

    ranked = rerank_chunks(query, chunks, mode="lexical")
    assert ranked[0]["doc_id"] == "short.md"


def test_kb_search_runbooks_uses_reranker_when_enabled(monkeypatch):
    """
    Integration sanity check: KB search path should rerank candidates when enabled.

    This test avoids Postgres/OpenAI by monkeypatching embedding + _search.
    """
    import apps.mcp.kb_server.main as kb_main

    class _DummyEmbeddings:
        def embed_query(self, _q: str) -> list[float]:
            return [0.0]

    monkeypatch.setattr(kb_main, "_get_embeddings", lambda: _DummyEmbeddings())
    # Return candidates in an order that lexical reranker will change.
    candidates = [
        {
            "content": "Telemetry bus voltage is low; investigate Power subsystem.",
            "doc_id": "unrelated.md",
        },
        {
            "content": "To restart the heater controller, verify threshold settings and controller health.",
            "doc_id": "heater_restart.md",
        },
        {
            "content": "Change configuration thresholds for Thermal subsystem.",
            "doc_id": "thresholds.md",
        },
    ]
    monkeypatch.setattr(
        kb_main,
        "_search",
        lambda _embedding, _doc_type, limit=5: candidates[:limit],
    )
    monkeypatch.setattr(kb_main.settings, "kb_reranker_enabled", True)
    monkeypatch.setattr(kb_main.settings, "kb_reranker_mode", "lexical")
    monkeypatch.setattr(kb_main.settings, "kb_reranker_retrieve_k", 3)

    out = kb_main.search_runbooks(
        "restart heater controller threshold",
        limit=2,
    )

    # Reranker should move heater_restart.md to the front.
    assert out[0]["doc_id"] == "heater_restart.md"
    assert len(out) == 2
