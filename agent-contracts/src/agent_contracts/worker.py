"""Contracts exchanged between the orchestrator and the CI/CD worker agents.

The orchestrator hands a worker a :class:`WorkerRequest` and receives a
:class:`WorkerResult`. Neither side re-derives what the other already decided:
the worker trusts the :class:`~agent_contracts.stacks.Classification`, and the
orchestrator trusts the worker's outcome. That explicit handoff is what makes
the multi-agent split real rather than decorative.
"""
from __future__ import annotations

import enum

from pydantic import BaseModel, Field

from .repo import RepoRef
from .stacks import Classification


class PhaseStatus(str, enum.Enum):
    """Outcome of a single phase of a worker's Discover→Generate→Validate→Deploy loop."""

    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"


class PhaseResult(BaseModel):
    """The result of one phase, carried back so a reviewer can see the whole run."""

    name: str = Field(description="phase name, e.g. 'discover', 'generate', 'validate', 'deploy'")
    status: PhaseStatus
    detail: str = Field(default="", description="human-readable summary or failure reason")
    duration_seconds: float = 0.0


class WorkerRequest(BaseModel):
    """Input the orchestrator hands to a worker agent.

    ``config`` carries the per-application step configuration (PRD CR-2) so the
    required steps are confirmable/modifiable per repo rather than hard-coded.
    """

    repo: RepoRef
    classification: Classification
    config: dict = Field(default_factory=dict, description="per-app step configuration (CR-2)")


class WorkerOutcome(str, enum.Enum):
    """The terminal state of a worker run."""

    PR_OPENED = "pr_opened"    # a pipeline was authored/repaired and a PR raised
    NO_CHANGE = "no_change"    # existing pipeline already compliant; nothing to do
    EXCEPTION = "exception"    # failed after the retry budget -> exception list


class WorkerResult(BaseModel):
    """What a worker returns to the orchestrator.

    ``pull_request_url`` is set only when ``outcome`` is
    :data:`WorkerOutcome.PR_OPENED`; ``reason`` is set only when it is
    :data:`WorkerOutcome.EXCEPTION`.
    """

    repo: RepoRef
    outcome: WorkerOutcome
    phases: list[PhaseResult] = Field(default_factory=list)
    pull_request_url: str | None = None
    attempts: int = Field(default=0, description="Generate→Validate attempts consumed")
    reason: str | None = None
