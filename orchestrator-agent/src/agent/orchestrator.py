"""The orchestration loop: classify each repo, route it, collect the outcome.

The orchestrator never authors pipelines (FR-0.6). For each repository it
classifies the technology set, routes to the matching CI worker (or the exception
list if there is none), invokes the worker, and records the result — adding any
worker ``EXCEPTION`` outcome to the exception list as well.
"""
from __future__ import annotations

import logging

from agent_contracts import (
    AgentClient,
    ExceptionEntry,
    OrchestrationReport,
    RepoRef,
    TechStack,
    WorkerOutcome,
    WorkerRequest,
)

from .classify import Classifier

log = logging.getLogger("agent.orchestrator")


class Orchestrator:
    """Traverses repositories and routes each to its CI worker agent."""

    def __init__(self, classifier: Classifier, routes: dict[TechStack, AgentClient]) -> None:
        self._classifier = classifier
        self._routes = routes

    def run(self, repos: list[RepoRef]) -> OrchestrationReport:
        report = OrchestrationReport()
        for repo in repos:
            self._process(repo, report)
        log.info(
            "orchestration complete: %d processed, %d exceptions",
            report.processed_count,
            report.exception_count,
        )
        return report

    def _process(self, repo: RepoRef, report: OrchestrationReport) -> None:
        # 1. Classify.
        try:
            classification = self._classifier.classify(repo)
        except Exception as exc:  # noqa: BLE001 -- any failure routes the repo to the exception list
            report.exceptions.append(
                ExceptionEntry(
                    repo=repo, stage="classify", reason="classification failed", detail=str(exc)
                )
            )
            return

        # 2. Route — no matching worker means the exception list (FR-0.5).
        client = self._routes.get(classification.stack)
        if client is None:
            report.exceptions.append(
                ExceptionEntry(
                    repo=repo,
                    stage="classify",
                    reason=f"no worker for {classification.stack.value}",
                    detail="; ".join(classification.evidence),
                )
            )
            return

        # 3. Invoke the worker.
        try:
            result = client.invoke(WorkerRequest(repo=repo, classification=classification))
        except Exception as exc:  # noqa: BLE001 -- worker failure routes the repo to the exception list
            report.exceptions.append(
                ExceptionEntry(
                    repo=repo, stage="worker", reason="worker call failed", detail=str(exc)
                )
            )
            return

        report.results.append(result)

        # 4. A worker exception is also a human-review item (FR-0.4).
        if result.outcome == WorkerOutcome.EXCEPTION:
            report.exceptions.append(
                ExceptionEntry(repo=repo, stage="worker", reason=result.reason or "worker exception")
            )
