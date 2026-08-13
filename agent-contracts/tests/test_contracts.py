"""Contract round-trip and helper tests — no network required."""
from __future__ import annotations

import pytest

from agent_contracts import (
    AgentClient,
    Classification,
    ClassificationMethod,
    ExceptionEntry,
    OrchestrationReport,
    PhaseResult,
    PhaseStatus,
    RepoRef,
    TechStack,
    WorkerOutcome,
    WorkerRequest,
    WorkerResult,
)


def test_repo_ref_from_url():
    ref = RepoRef.from_url("https://github.com/acme/widget.git")
    assert ref.owner == "acme"
    assert ref.name == "widget"
    assert ref.full_name == "acme/widget"


def test_repo_ref_from_url_rejects_bad_url():
    with pytest.raises(ValueError):
        RepoRef.from_url("https://github.com/")


def test_worker_request_result_round_trip():
    repo = RepoRef.from_url("https://github.com/acme/widget")
    request = WorkerRequest(
        repo=repo,
        classification=Classification(
            stack=TechStack.DOTNET_CORE,
            confidence=0.95,
            method=ClassificationMethod.HEURISTIC,
            evidence=["widget.csproj"],
        ),
    )
    dumped = request.model_dump(mode="json")
    assert WorkerRequest.model_validate(dumped) == request

    result = WorkerResult(
        repo=repo,
        outcome=WorkerOutcome.PR_OPENED,
        phases=[PhaseResult(name="generate", status=PhaseStatus.SUCCESS)],
        pull_request_url="https://github.com/acme/widget/pull/1",
        attempts=1,
    )
    assert WorkerResult.model_validate(result.model_dump(mode="json")) == result


def test_orchestration_report_counts():
    repo = RepoRef.from_url("https://github.com/acme/widget")
    report = OrchestrationReport(
        results=[WorkerResult(repo=repo, outcome=WorkerOutcome.NO_CHANGE)],
        exceptions=[ExceptionEntry(repo=repo, stage="classify", reason="unclassifiable")],
    )
    assert report.processed_count == 1
    assert report.exception_count == 1


def test_agent_client_constructs():
    client = AgentClient("http://netcore-ci:8080/")
    assert client._base_url == "http://netcore-ci:8080"
