"""
S3.4 / P4.4: Rerankers for RAG citation quality.

This repo currently supports an optional, deterministic *local* reranker to improve
the order of retrieved KB chunks before returning citations.

The local reranker is intentionally dependency-free (no extra ML packages) so the lab
remains easy to run in CI and for local development.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Literal

import httpx

from config import settings

RerankerMode = Literal["lexical", "llm"]

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def _tokenize(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text or "") if t}


@dataclass(frozen=True)
class RerankResult:
    items: list[dict[str, Any]]


def rerank_lexical(query: str, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Deterministic, dependency-free reranker:
    - score = number of overlapping tokens between query and chunk content
    - tie-breakers: higher overlap first, then shorter content first
    """

    q_tokens = _tokenize(query)
    scored: list[tuple[int, int, dict[str, Any]]] = []
    for c in chunks:
        content = c.get("content") or ""
        overlap = len(q_tokens.intersection(_tokenize(content)))
        scored.append((overlap, len(content), c))

    # Sort by:
    # 1) overlap descending
    # 2) content length ascending (slightly prefer more focused snippets)
    scored.sort(key=lambda t: (-t[0], t[1]))
    return [c for _, __, c in scored]


def rerank_llm(query: str, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Optional LLM-based reranker (external API).

    Not used by default. Intended for experimentation when you want better relevance
    scoring than lexical overlap.
    """
    if not settings.openai_api_key:
        # Fail open: keep original order if LLM isn't configured.
        return chunks

    # Keep the payload small; we rerank only the top candidate set.
    # We ask the model for numeric scores aligned to chunk order.
    formatted_chunks = "\n".join(
        f"{i+1}) {c.get('content','')[:800]}" for i, c in enumerate(chunks)
    )
    prompt = (
        "You are a relevance judge.\n"
        "Given a user query and candidate text chunks, assign each chunk a score from 0 to 100\n"
        "based on how well it supports answering the query.\n"
        'Return ONLY JSON in the form {"scores": [s1, s2, ...]} with one score per chunk.\n'
        f"Query: {query}\n\nChunks:\n{formatted_chunks}\n"
    )

    # Note: using chat.completions because the repo already standardises on it.
    # If this is enabled in practice, consider caching and tighter prompt limits.
    payload = {
        "model": getattr(settings, "kb_reranker_llm_model", "gpt-4o-mini"),
        "temperature": 0,
        "messages": [
            {"role": "system", "content": "Return strictly valid JSON only."},
            {"role": "user", "content": prompt},
        ],
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return chunks

    try:
        text = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")  # type: ignore[union-attr]
        parsed = json.loads(text)
        scores = parsed.get("scores")
        if not isinstance(scores, list) or len(scores) != len(chunks):
            return chunks
        ranked = sorted(
            range(len(chunks)),
            key=lambda i: (-(scores[i] if isinstance(scores[i], (int, float)) else 0)),
        )
        return [chunks[i] for i in ranked]
    except Exception:
        return chunks


def rerank_chunks(
    query: str,
    chunks: list[dict[str, Any]],
    *,
    mode: RerankerMode,
) -> list[dict[str, Any]]:
    """
    Dispatch to the configured reranker mode.
    """
    if not chunks:
        return []
    if mode == "lexical":
        return rerank_lexical(query, chunks)
    if mode == "llm":
        return rerank_llm(query, chunks)
    # Defensive fallback.
    return chunks
