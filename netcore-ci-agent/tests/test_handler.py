"""End-to-end handler test with VCS side effects stubbed (no git/network)."""
from __future__ import annotations

from agent_contracts import (
    Classification,
    ClassificationMethod,
    RepoRef,
    TechStack,
    WorkerRequest,
)
from ci_authoring import vcs

from agent.handler import NetCoreCIHandler

CSPROJ = """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup><TargetFramework>net8.0</TargetFramework></PropertyGroup>
</Project>
"""


class _Ctx:
    """Minimal stand-in for agent_core's RunContext."""

    def __init__(self, payload):
        self.payload = payload

    def done(self, result):
        return {"agent": "netcore-ci", "result": result}


def test_handler_runs_full_loop_and_opens_pr(monkeypatch, tmp_path):
    (tmp_path / "Widget.csproj").write_text(CSPROJ)
    monkeypatch.setattr(vcs, "clone_repo", lambda repo: tmp_path)
    monkeypatch.setattr(vcs, "find_existing_workflow", lambda repo_path: None)
    monkeypatch.setattr(
        vcs, "open_pull_request", lambda *a, **k: "https://github.com/acme/widget/pull/3"
    )

    request = WorkerRequest(
        repo=RepoRef.from_url("https://github.com/acme/widget"),
        classification=Classification(
            stack=TechStack.DOTNET_CORE, confidence=1.0, method=ClassificationMethod.HEURISTIC
        ),
    )
    out = NetCoreCIHandler().handle(_Ctx({"input": request.model_dump(mode="json")}))

    assert out["result"]["outcome"] == "pr_opened"
    assert out["result"]["pull_request_url"].endswith("/pull/3")
