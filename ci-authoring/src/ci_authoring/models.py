"""Core value objects shared across the authoring pipeline.

These are the inputs and outputs of the Discover / Generate / Validate phases.
They are deliberately small and stack-agnostic: stack-specific detail rides in
:class:`Discovery` subclasses, not in the engine.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

#: The default CI steps for the Stage-1 demo (unit tests + SonarQube coverage).
DEFAULT_REQUIRED_STEPS = ["build", "test", "sonar"]

#: Finding categories that must fail the build (PRD CR-1).
DEFAULT_FAIL_ON = ["unit_test", "sast_critical", "sca_critical", "image_scan_critical"]


class Discovery(BaseModel):
    """What the Discover phase learns about a repository.

    Stack-specific discoverers subclass this to add fields (target framework
    version, MSBuild mapping, …); the engine relies only on the common fields
    declared here. ``extra="allow"`` keeps subclass fields on the model even when
    it is handled as the base type.
    """

    model_config = ConfigDict(extra="allow")

    runner: str = Field(description="CI runner label, e.g. 'ubuntu-latest' or 'windows-latest'")
    build_tool: str = Field(description="build tool, e.g. 'dotnet' or 'msbuild'")
    project_files: list[str] = Field(
        default_factory=list, description="discovered project/solution files (repo-relative)"
    )
    has_dockerfile: bool = False
    existing_workflow_path: str | None = Field(
        default=None, description="path of an existing CI workflow, if one was found"
    )


class StepConfig(BaseModel):
    """Per-application step configuration (PRD CR-2).

    Which steps a pipeline must contain is *data*, not hard-coded: a user can add,
    modify, or disable steps per repo. ``fail_on`` lists the finding categories
    that must fail the build (PRD CR-1).
    """

    required_steps: list[str] = Field(default_factory=lambda: list(DEFAULT_REQUIRED_STEPS))
    disabled_steps: list[str] = Field(default_factory=list)
    fail_on: list[str] = Field(default_factory=lambda: list(DEFAULT_FAIL_ON))

    def enabled(self, step: str) -> bool:
        """Whether ``step`` should appear in the generated pipeline."""
        return step in self.required_steps and step not in self.disabled_steps

    def active_steps(self) -> list[str]:
        """The required steps that are not disabled, in declared order."""
        return [s for s in self.required_steps if s not in self.disabled_steps]


class WorkflowArtifact(BaseModel):
    """The file(s) an agent proposes to add to the repository."""

    primary_path: str = Field(description="the workflow path, e.g. '.github/workflows/ci.yml'")
    files: dict[str, str] = Field(description="repo-relative path -> file content")


class ValidationResult(BaseModel):
    """Outcome of the deterministic Validate phase."""

    ok: bool
    errors: list[str] = Field(default_factory=list)
