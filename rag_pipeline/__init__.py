"""
Agentic RAG v4.0 — Melanoma ABCDE Evidence Pipeline
====================================================

Hybrid search (dense + BM25 + RRF), cross-encoder re-ranking,
parent-child context expansion, HyDE queries, and multi-hop
agentic reasoning over your existing knowledge base.

Usage:
    from rag_pipeline import create_agent

    agent = create_agent()
    report = agent.generate_report(case_data)
"""

from .agent import create_agent, MelanomaAgent

__all__ = ["create_agent", "MelanomaAgent"]
