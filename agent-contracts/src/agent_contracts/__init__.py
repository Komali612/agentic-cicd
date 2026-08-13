"""agent_contracts — shared data contracts + inter-agent client.

Every agent in the Agentic CI/CD framework (orchestrator and workers) depends on
this package so they exchange the *same* typed models. It carries no business
logic — only the shapes that cross agent boundaries — which keeps the handoffs
explicit and independently testable.
"""
from __future__ import annotations

from .client import AgentClient
from .exceptions import ExceptionEntry, OrchestrationReport
from .repo import RepoRef
from .stacks import Classification, ClassificationMethod, TechStack
from .worker import (
    PhaseResult,
    PhaseStatus,
    WorkerOutcome,
    WorkerRequest,
    WorkerResult,
)

__version__ = "0.1.0"
__all__ = [
    "AgentClient",
    "Classification",
    "ClassificationMethod",
    "ExceptionEntry",
    "OrchestrationReport",
    "PhaseResult",
    "PhaseStatus",
    "RepoRef",
    "TechStack",
    "WorkerOutcome",
    "WorkerRequest",
    "WorkerResult",
    "__version__",
]
