# Agents module — Orchestrator + three top-level agents + clinical context utility
"""Three top-level agents (Vision, Evidence, Report) orchestrated by the Orchestrator.

ClinicalContextAgent is an internal utility for evolution/history handling,
not a top-level agent.
"""
from .orchestrator import OrchestratorAgent
from .vision import VisionAgent
from .clinical_context import ClinicalContextAgent  # internal utility, kept for import compatibility
from .evidence import EvidenceAgent
from .report import ReportAgent
__all__ = ["OrchestratorAgent", "VisionAgent", "EvidenceAgent", "ReportAgent"]
