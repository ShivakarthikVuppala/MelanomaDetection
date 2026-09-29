"""Compatibility import for the state-driven Supervisor Agent.

The fixed four-phase orchestrator was removed. New code should import
``SupervisorAgent`` from ``src.agents``.
"""
from ..agents.supervisor import SupervisorAgent
__all__ = ["SupervisorAgent"]
