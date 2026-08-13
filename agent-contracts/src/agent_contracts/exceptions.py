"""The exception-list and orchestration-report contracts (PRD FR-0.4, FR-0.5).

The orchestrator never silently drops a repository: anything it cannot classify,
or that a worker fails to process within its retry budget, becomes an
:class:`ExceptionEntry` for human review. An :class:`OrchestrationReport`
aggregates one full run.
"""
from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from .repo import RepoRef
from .worker import WorkerResult


def _utcnow() -> datetime:
    return datetime.now(UTC)


class ExceptionEntry(BaseModel):
    """One repository that could not be processed, with enough context to act."""

    repo: RepoRef
    stage: str = Field(description="where it failed: classify | discover | generate | validate | deploy")
    reason: str = Field(description="short machine/human reason, e.g. 'unclassifiable'")
    detail: str = Field(default="", description="longer explanation, log tail, or diagnosis")
    at: datetime = Field(default_factory=_utcnow)


class OrchestrationReport(BaseModel):
    """Summary of a single orchestrator run over one or more repositories."""

    results: list[WorkerResult] = Field(default_factory=list)
    exceptions: list[ExceptionEntry] = Field(default_factory=list)
    at: datetime = Field(default_factory=_utcnow)

    @property
    def processed_count(self) -> int:
        return len(self.results)

    @property
    def exception_count(self) -> int:
        return len(self.exceptions)
