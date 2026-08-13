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

from agent.handler import NetLegacyCIHandler

CSPROJ = """<Project ToolsVersion="15.0" xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
  <PropertyGroup><TargetFrameworkVersion>v4.8</TargetFrameworkVersion></PropertyGroup>
</Project>
"""


class _Ctx:
    def __init__(self, payload):
        self.payload = payload

    def done(self, result):
        return {"agent": "netlegacy-ci", "result": result}


def test_handler_runs_full_loop_and_opens_pr(monkeypatch, tmp_path):
    (tmp_path / "Legacy.csproj").write_text(CSPROJ)
    monkeypatch.setattr(vcs, "clone_repo", lambda repo: tmp_path)
    monkeypatch.setattr(vcs, "find_existing_workflow", lambda repo_path: None)
    monkeypatch.setattr(
        vcs, "open_pull_request", lambda *a, **k: "https://github.com/acme/legacy/pull/5"
    )

    request = WorkerRequest(
        repo=RepoRef.from_url("https://github.com/acme/legacy"),
        classification=Classification(
            stack=TechStack.DOTNET_FRAMEWORK, confidence=1.0, method=ClassificationMethod.HEURISTIC
        ),
    )
    out = NetLegacyCIHandler().handle(_Ctx({"input": request.model_dump(mode="json")}))

    assert out["result"]["outcome"] == "pr_opened"
    assert out["result"]["pull_request_url"].endswith("/pull/5")
