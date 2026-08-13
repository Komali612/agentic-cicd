"""Tests for the orchestration loop (classifier + worker clients faked)."""
from __future__ import annotations

from agent_contracts import (
    Classification,
    ClassificationMethod,
    RepoRef,
    TechStack,
    WorkerOutcome,
    WorkerRequest,
    WorkerResult,
)

from agent.orchestrator import Orchestrator

REPO = RepoRef.from_url("https://github.com/acme/widget")


class FakeClassifier:
    def __init__(self, stack):
        self._stack = stack

    def classify(self, repo):
        return Classification(
            stack=self._stack, confidence=1.0, method=ClassificationMethod.HEURISTIC
        )


class FakeClient:
    def __init__(self, outcome=WorkerOutcome.PR_OPENED):
        self._outcome = outcome
        self.calls: list[WorkerRequest] = []

    def invoke(self, request: WorkerRequest) -> WorkerResult:
        self.calls.append(request)
        return WorkerResult(
            repo=request.repo,
            outcome=self._outcome,
            pull_request_url=("https://x/pull/1" if self._outcome == WorkerOutcome.PR_OPENED else None),
            reason=("boom" if self._outcome == WorkerOutcome.EXCEPTION else None),
        )


def test_routes_and_collects_result():
    client = FakeClient()
    report = Orchestrator(
        FakeClassifier(TechStack.DOTNET_CORE), {TechStack.DOTNET_CORE: client}
    ).run([REPO])
    assert report.processed_count == 1
    assert report.exception_count == 0
    assert client.calls[0].classification.stack == TechStack.DOTNET_CORE


def test_unroutable_stack_goes_to_exceptions():
    report = Orchestrator(
        FakeClassifier(TechStack.COBOL_IBM), {TechStack.DOTNET_CORE: FakeClient()}
    ).run([REPO])
    assert report.processed_count == 0
    assert report.exception_count == 1
    assert "no worker" in report.exceptions[0].reason


def test_worker_exception_is_recorded_for_review():
    report = Orchestrator(
        FakeClassifier(TechStack.DOTNET_CORE),
        {TechStack.DOTNET_CORE: FakeClient(WorkerOutcome.EXCEPTION)},
    ).run([REPO])
    assert report.processed_count == 1  # the result is still recorded
    assert report.exception_count == 1  # and also flagged for a human
