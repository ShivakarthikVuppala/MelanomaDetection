"""
Agentic RAG v4.0 — Melanoma ABCDE Evidence Pipeline
====================================================

Hybrid search (dense + BM25 + RRF), cross-encoder re-ranking,
parent-child context expansion, HyDE queries, and multi-hop
agentic reasoning over your existing knowledge base.

Usage:
    from rag_pipeline import create_backend

    backend = create_backend()
    passages = backend.hybrid_search("ABCDE melanoma evidence")
"""

from .agent import create_backend, AdvancedRetrievalBackend

__all__ = ["create_backend", "AdvancedRetrievalBackend"]
