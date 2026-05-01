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

from config import settings
from apps.llm_gateway import (
    LLMGatewayProviderError,
    LLMGatewayTimeoutError,
    generate as gateway_generate,
)

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
    model_id = getattr(settings, "kb_reranker_llm_model", "gpt-4o-mini")
    full_prompt = "System: Return strictly valid JSON only.\n\n" f"{prompt}"

    try:
        out = gateway_generate(
            prompt=full_prompt,
            node="kb_reranker",
            model_id=model_id,
            temperature=0,
        )
        text = str(out.get("content") or "")
    except (LLMGatewayTimeoutError, LLMGatewayProviderError, Exception):
        # Fail open: keep original order if LLM reranking fails or is unavailable.
        return chunks

    try:
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
