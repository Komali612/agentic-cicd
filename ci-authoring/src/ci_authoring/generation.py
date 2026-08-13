"""The Generate phase abstraction.

Generation is **deterministic**: given the same discovery + config it must emit
byte-identical files. That is the crux of the deterministic-template decision —
the model may orchestrate and choose parameters, but the YAML itself comes from a
template, so pipelines are reproducible and auditable across ~1,400 repos.

``feedback`` lets an adaptive generator react to validation errors on a retry;
deterministic template generators ignore it (and therefore fail fast on a genuine
template defect rather than masking it).
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from .models import Discovery, StepConfig, WorkflowArtifact


class WorkflowGenerator(ABC):
    """Produce the workflow artifact for a repository."""

    @abstractmethod
    def generate(
        self,
        discovery: Discovery,
        config: StepConfig,
        feedback: list[str] | None = None,
    ) -> WorkflowArtifact:
        """Render the workflow file(s) for this repository."""
        raise NotImplementedError
