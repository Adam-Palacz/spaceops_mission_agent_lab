"""
P4.7 helper: re-index KB runbooks + postmortems into pgvector.

Usage (repo root):
    python -m scripts.reindex_kb
"""

from __future__ import annotations

from apps.mcp.kb_server.index_kb import main


if __name__ == "__main__":
    main()
