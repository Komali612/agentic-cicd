"""Tests for the deterministic .NET Framework workflow generator."""
from __future__ import annotations

import yaml
from ci_authoring import StepConfig, validate_workflow

from agent.discover import DotNetFrameworkDiscovery
from agent.generate import NetLegacyWorkflowGenerator, render_netlegacy_ci


def _discovery():
    return DotNetFrameworkDiscovery(
        runner="windows-latest", build_tool="msbuild", target_framework_version="v4.8"
    )


def test_generated_workflow_runs_on_windows_with_required_steps():
    artifact = NetLegacyWorkflowGenerator().generate(_discovery(), StepConfig())
    doc = yaml.safe_load(artifact.files[artifact.primary_path])
    job = doc["jobs"]["ci"]
    assert job["runs-on"] == "windows-latest"
    step_ids = {s.get("id") for s in job["steps"]}
    assert {"build", "test", "sonar"} <= step_ids
    assert validate_workflow(artifact, StepConfig()).ok


def test_uses_msbuild_and_nuget():
    content = render_netlegacy_ci(_discovery(), StepConfig())
    assert "microsoft/setup-msbuild" in content
    assert "nuget restore" in content
    # This stack must not emit Docker/Helm concerns.
    assert "docker" not in content.lower()


def test_generation_is_deterministic():
    assert render_netlegacy_ci(_discovery(), StepConfig()) == render_netlegacy_ci(
        _discovery(), StepConfig()
    )
