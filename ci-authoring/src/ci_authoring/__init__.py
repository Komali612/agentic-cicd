"""ci_authoring — the shared engine for CI pipeline-authoring agents.

A CI worker agent supplies two stack-specific pieces — a :class:`Discoverer` and a
:class:`WorkflowGenerator` — and the :class:`AuthoringEngine` runs the rest of the
Discover→Generate→Validate→Deploy loop identically for every stack.
"""
from __future__ import annotations

from .discovery import Discoverer
from .engine import MAX_ATTEMPTS, AuthoringEngine
from .generation import WorkflowGenerator
from .models import (
    DEFAULT_FAIL_ON,
    DEFAULT_REQUIRED_STEPS,
    Discovery,
    StepConfig,
    ValidationResult,
    WorkflowArtifact,
)
from .validation import validate_workflow

__version__ = "0.1.0"
__all__ = [
    "DEFAULT_FAIL_ON",
    "DEFAULT_REQUIRED_STEPS",
    "MAX_ATTEMPTS",
    "AuthoringEngine",
    "Discoverer",
    "Discovery",
    "StepConfig",
    "ValidationResult",
    "WorkflowArtifact",
    "WorkflowGenerator",
    "__version__",
    "validate_workflow",
]
