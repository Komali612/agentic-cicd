"""Tests for the deterministic .NET Core workflow generator."""
from __future__ import annotations

import yaml
from ci_authoring import StepConfig, validate_workflow

from agent.discover import DotNetCoreDiscovery
from agent.generate import NetCoreWorkflowGenerator, render_netcore_ci


def _discovery(framework="net8.0"):
    return DotNetCoreDiscovery(
        runner="ubuntu-latest", build_tool="dotnet", target_framework=framework
    )


def test_generated_workflow_is_valid_yaml_with_required_steps():
    artifact = NetCoreWorkflowGenerator().generate(_discovery(), StepConfig())
    doc = yaml.safe_load(artifact.files[artifact.primary_path])
    step_ids = {s.get("id") for job in doc["jobs"].values() for s in job["steps"]}
    assert {"build", "test", "sonar"} <= step_ids
    # And it satisfies the shared validator.
    assert validate_workflow(artifact, StepConfig()).ok


def test_generation_is_deterministic():
    a = render_netcore_ci(_discovery(), StepConfig())
    b = render_netcore_ci(_discovery(), StepConfig())
    assert a == b


def test_sdk_version_tracks_target_framework():
    assert "6.0.x" in render_netcore_ci(_discovery("net6.0"), StepConfig())
    assert "8.0.x" in render_netcore_ci(_discovery("net8.0"), StepConfig())


def test_disabled_step_is_omitted():
    content = render_netcore_ci(_discovery(), StepConfig(disabled_steps=["sonar"]))
    assert "SonarQube" not in content


def test_image_pipeline_publishes_to_ghcr():
    """FR-N.10: build a container image, scan it, emit an SBOM, and push to GHCR;
    a Dockerfile is generated when the repository has none."""
    artifact = NetCoreWorkflowGenerator().generate(
        DotNetCoreDiscovery(
            runner="ubuntu-latest",
            build_tool="dotnet",
            target_framework="net8.0",
            project_files=["src/App/App.csproj"],
        ),
        StepConfig(),
    )
    workflow = artifact.files[artifact.primary_path]
    assert "ghcr.io/${{ github.repository }}" in workflow
    assert "packages: write" in workflow            # permission to push to GHCR
    assert "docker/build-push-action@v6" in workflow
    assert "sbom.cyclonedx.json" in workflow         # CycloneDX SBOM
    assert "Dockerfile" in artifact.files            # generated because the repo has none


def test_trivy_action_pinned_to_a_real_tag():
    """Regression: the Trivy action must not reference the non-existent 0.24.0 tag."""
    workflow = render_netcore_ci(_discovery(), StepConfig())
    assert "aquasecurity/trivy-action@0.24.0" not in workflow
    assert "aquasecurity/trivy-action@0.35.0" in workflow


def test_image_step_is_configurable_off():
    """CR-2: image build can be disabled per app (and then no Dockerfile is added)."""
    artifact = NetCoreWorkflowGenerator().generate(_discovery(), StepConfig(disabled_steps=["image"]))
    assert "docker/build-push-action" not in artifact.files[artifact.primary_path]
    assert "Dockerfile" not in artifact.files
