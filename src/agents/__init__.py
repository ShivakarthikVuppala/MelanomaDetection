# Agents module — Orchestrator + four top-level agents
"""Four top-level agents (Vision, Clinical Context, Evidence, Report) orchestrated by
the Orchestrator.

The Clinical Context Agent is a first-class agent: it owns patient-history intake and
the ABCDE Evolution (E) criterion, including longitudinal evolution assessment across
image visits.
"""
from .orchestrator import OrchestratorAgent
from .vision import VisionAgent
from .clinical_context import ClinicalContextAgent
from .evidence import EvidenceAgent
from .report import ReportAgent
__all__ = ["OrchestratorAgent", "VisionAgent", "ClinicalContextAgent", "EvidenceAgent", "ReportAgent"]
