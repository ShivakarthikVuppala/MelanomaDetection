"""Compatibility import for the state-driven Orchestrator Agent.

The fixed four-phase orchestrator was removed. New code should import
``OrchestratorAgent`` from ``src.agents``.
"""
from ..agents.orchestrator import OrchestratorAgent
__all__ = ["OrchestratorAgent"]
