"""AuthoringEngine — the deterministic Discover→Generate→Validate→Deploy loop.

The engine is injected with a stack-specific :class:`~ci_authoring.discovery.Discoverer`
and :class:`~ci_authoring.generation.WorkflowGenerator`; everything else (clone,
existing-pipeline handling, validation, the retry budget, and the pull request)
is shared and identical across every CI worker agent.

Two PRD invariants are enforced here, in code, never delegated to an LLM:

* **Retry bound (NFR-3):** at most ``max_attempts`` Generate→Validate attempts,
  then the repository becomes an exception.
* **Check-existing-then-repair (CR-3):** if a compliant pipeline already exists,
  the engine reports ``NO_CHANGE`` rather than overwriting it.
"""
from __future__ import annotations

import logging
import time

from agent_contracts import (
    PhaseResult,
    PhaseStatus,
    WorkerOutcome,
    WorkerRequest,
    WorkerResult,
)

from . import vcs
from .config import load_step_config
from .discovery import Discoverer
from .generation import WorkflowGenerator
from .validation import validate_workflow

log = logging.getLogger("ci_authoring.engine")

#: PRD NFR-3: Generate→Validate is capped at 3 attempts before escalation.
MAX_ATTEMPTS = 3


class AuthoringEngine:
    """Runs the four-phase authoring loop for one repository."""

    def __init__(
        self,
        discoverer: Discoverer,
        generator: WorkflowGenerator,
        *,
        max_attempts: int = MAX_ATTEMPTS,
    ) -> None:
        self._discoverer = discoverer
        self._generator = generator
        self._max_attempts = max_attempts

    def run(self, request: WorkerRequest) -> WorkerResult:
        """Author (or repair) the CI pipeline for ``request.repo`` and return the outcome."""
        repo = request.repo
        phases: list[PhaseResult] = []

        # --- Clone -------------------------------------------------------------
        with _phase("clone", phases):
            repo_path = vcs.clone_repo(repo)

        # --- Discover ----------------------------------------------------------
        with _phase("discover", phases) as phase:
            discovery = self._discoverer.discover(repo_path)
            discovery.existing_workflow_path = vcs.find_existing_workflow(repo_path)
            phase.detail = f"runner={discovery.runner}, build_tool={discovery.build_tool}"

        config = load_step_config(repo_path, request.config)

        # --- Check-existing-then-repair (CR-3): skip if already compliant ------
        if discovery.existing_workflow_path:
            existing = vcs.read_workflow(repo_path, discovery.existing_workflow_path)
            if validate_workflow(existing, config).ok:
                phases.append(
                    PhaseResult(
                        name="generate",
                        status=PhaseStatus.SKIPPED,
                        detail="existing pipeline already contains the required steps",
                    )
                )
                return WorkerResult(repo=repo, outcome=WorkerOutcome.NO_CHANGE, phases=phases)

        # --- Generate → Validate (bounded retry) -------------------------------
        feedback: list[str] | None = None
        artifact = None
        attempts = 0
        while attempts < self._max_attempts:
            attempts += 1
            artifact = self._generator.generate(discovery, config, feedback)
            result = validate_workflow(artifact, config)
            if result.ok:
                phases.append(
                    PhaseResult(
                        name="generate",
                        status=PhaseStatus.SUCCESS,
                        detail=f"{len(artifact.files)} file(s)",
                    )
                )
                phases.append(
                    PhaseResult(
                        name="validate",
                        status=PhaseStatus.SUCCESS,
                        detail=f"passed on attempt {attempts}",
                    )
                )
                break
            feedback = result.errors
            log.info("validation failed (attempt %d/%d): %s", attempts, self._max_attempts, feedback)
        else:
            reason = f"validation failed after {attempts} attempts"
            phases.append(
                PhaseResult(name="validate", status=PhaseStatus.FAILURE, detail="; ".join(feedback or []))
            )
            return WorkerResult(
                repo=repo,
                outcome=WorkerOutcome.EXCEPTION,
                phases=phases,
                attempts=attempts,
                reason=reason,
            )

        # --- Deploy (open a PR — never merge) ----------------------------------
        with _phase("deploy", phases) as phase:
            pr_url = vcs.open_pull_request(repo, repo_path, artifact)
            phase.detail = pr_url

        return WorkerResult(
            repo=repo,
            outcome=WorkerOutcome.PR_OPENED,
            phases=phases,
            pull_request_url=pr_url,
            attempts=attempts,
        )


class _phase:
    """Context manager that times a phase and records a :class:`PhaseResult`.

    On success the phase is recorded as SUCCESS; if the body raises, it is
    recorded as FAILURE (with the exception text) and the exception re-raised.
    """

    def __init__(self, name: str, sink: list[PhaseResult]) -> None:
        self._result = PhaseResult(name=name, status=PhaseStatus.SUCCESS)
        self._sink = sink
        self._start = 0.0

    def __enter__(self) -> PhaseResult:
        self._start = time.monotonic()
        return self._result

    def __exit__(self, exc_type, exc, tb) -> bool:
        self._result.duration_seconds = round(time.monotonic() - self._start, 3)
        if exc_type is not None:
            self._result.status = PhaseStatus.FAILURE
            self._result.detail = f"{exc_type.__name__}: {exc}"
        self._sink.append(self._result)
        return False  # never suppress
