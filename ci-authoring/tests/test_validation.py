"""Tests for the deterministic workflow validator."""
from __future__ import annotations

from ci_authoring import StepConfig, ValidationResult, WorkflowArtifact, validate_workflow

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


def _artifact(content: str) -> WorkflowArtifact:
    return WorkflowArtifact(primary_path="w.yml", files={"w.yml": content})


def test_valid_workflow_passes():
    result = validate_workflow(_artifact(VALID_WORKFLOW), StepConfig())
    assert isinstance(result, ValidationResult)
    assert result.ok
    assert result.errors == []


def test_invalid_yaml_fails():
    result = validate_workflow(_artifact("name: [unclosed"), StepConfig())
    assert not result.ok
    assert any("YAML" in e for e in result.errors)


def test_missing_required_step_fails():
    partial = (
        "on: [push]\n"
        "jobs:\n"
        "  ci:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - id: build\n"
        "        run: dotnet build\n"
    )
    result = validate_workflow(_artifact(partial), StepConfig())
    assert not result.ok
    assert any("test" in e for e in result.errors)
    assert any("sonar" in e for e in result.errors)


def test_disabled_step_is_not_required():
    partial = (
        "on: [push]\n"
        "jobs:\n"
        "  ci:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - id: build\n"
        "        run: dotnet build\n"
        "      - id: test\n"
        "        run: dotnet test\n"
    )
    config = StepConfig(disabled_steps=["sonar"])
    assert validate_workflow(_artifact(partial), config).ok
