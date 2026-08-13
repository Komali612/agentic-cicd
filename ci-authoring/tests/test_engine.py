"""Tests for the AuthoringEngine loop, with VCS side effects stubbed out."""
from __future__ import annotations

from pathlib import Path

import pytest
from agent_contracts import (
    Classification,
    ClassificationMethod,
    RepoRef,
    TechStack,
    WorkerOutcome,
    WorkerRequest,
)

from ci_authoring import (
    AuthoringEngine,
    Discoverer,
    Discovery,
    WorkflowArtifact,
    WorkflowGenerator,
    vcs,
)

VALID_WORKFLOW = """
name: CI
on: [push]
jobs:
  ci:
    runs-on: ubuntu-latest
    steps:
      - id: build
        run: dotnet build
      - id: test
        run: dotnet test
      - id: sonar
        run: echo sonar
"""


def _request() -> WorkerRequest:
    return WorkerRequest(
        repo=RepoRef.from_url("https://github.com/acme/widget"),
        classification=Classification(
            stack=TechStack.DOTNET_CORE, confidence=1.0, method=ClassificationMethod.HEURISTIC
        ),
    )


class FakeDiscoverer(Discoverer):
    def discover(self, repo_path: Path) -> Discovery:
        return Discovery(runner="ubuntu-latest", build_tool="dotnet", project_files=["widget.csproj"])


class GoodGenerator(WorkflowGenerator):
    def generate(self, discovery, config, feedback=None) -> WorkflowArtifact:
        return WorkflowArtifact(
            primary_path=".github/workflows/ci.yml",
            files={".github/workflows/ci.yml": VALID_WORKFLOW},
        )


class BrokenGenerator(WorkflowGenerator):
    def generate(self, discovery, config, feedback=None) -> WorkflowArtifact:
        # No jobs/steps -> always fails validation.
        return WorkflowArtifact(
            primary_path=".github/workflows/ci.yml",
            files={".github/workflows/ci.yml": "name: CI\non: [push]\n"},
        )


@pytest.fixture
def stub_vcs(monkeypatch, tmp_path):
    """Stub clone/find/PR so the loop runs without git or network."""
    monkeypatch.setattr(vcs, "clone_repo", lambda repo: tmp_path)
    monkeypatch.setattr(vcs, "find_existing_workflow", lambda repo_path: None)
    monkeypatch.setattr(
        vcs, "open_pull_request", lambda *a, **k: "https://github.com/acme/widget/pull/7"
    )
    return monkeypatch


def test_happy_path_opens_pr(stub_vcs):
    result = AuthoringEngine(FakeDiscoverer(), GoodGenerator()).run(_request())
    assert result.outcome == WorkerOutcome.PR_OPENED
    assert result.pull_request_url.endswith("/pull/7")
    assert result.attempts == 1


def test_broken_generation_becomes_exception_after_three_attempts(stub_vcs):
    result = AuthoringEngine(FakeDiscoverer(), BrokenGenerator()).run(_request())
    assert result.outcome == WorkerOutcome.EXCEPTION
    assert result.attempts == 3
    assert result.pull_request_url is None


def test_existing_compliant_pipeline_is_left_alone(monkeypatch, tmp_path):
    monkeypatch.setattr(vcs, "clone_repo", lambda repo: tmp_path)
    monkeypatch.setattr(vcs, "find_existing_workflow", lambda repo_path: ".github/workflows/ci.yml")
    monkeypatch.setattr(
        vcs,
        "read_workflow",
        lambda repo_path, rel: WorkflowArtifact(primary_path=rel, files={rel: VALID_WORKFLOW}),
    )
    pr_calls: list[bool] = []
    monkeypatch.setattr(vcs, "open_pull_request", lambda *a, **k: pr_calls.append(True))

    result = AuthoringEngine(FakeDiscoverer(), GoodGenerator()).run(_request())
    assert result.outcome == WorkerOutcome.NO_CHANGE
    assert pr_calls == []  # never touched an already-compliant repo
