"""Generate phase for .NET Core: a deterministic GitHub Actions workflow.

The workflow is assembled from a fixed template plus the enabled steps from the
:class:`~ci_authoring.models.StepConfig`, so the same repo + config always yields
byte-identical YAML. For the Stage-1 demo the security/quality step is SonarQube
(the substitute for Fortify); DAST, SBOM, image scan, and Nexus are Stage-2.
"""
from __future__ import annotations

from ci_authoring import Discovery, StepConfig, WorkflowArtifact, WorkflowGenerator

WORKFLOW_PATH = ".github/workflows/ci.yml"

#: Map a target framework to a setup-dotnet SDK version line.
_SDK_VERSIONS = {"net6.0": "6.0.x", "net7.0": "7.0.x", "net8.0": "8.0.x"}


def _sdk_version(target_framework: str | None) -> str:
    return _SDK_VERSIONS.get((target_framework or "").lower(), "8.0.x")


def render_netcore_ci(discovery: Discovery, config: StepConfig) -> str:
    """Render the .NET Core CI workflow YAML for ``discovery`` and ``config``."""
    sdk = _sdk_version(getattr(discovery, "target_framework", None))

    steps: list[str] = [
        "      - uses: actions/checkout@v4",
        "      - name: Setup .NET",
        "        uses: actions/setup-dotnet@v4",
        f"        with:\n          dotnet-version: '{sdk}'",
        "      - name: Restore",
        "        run: dotnet restore",
    ]
    if config.enabled("build"):
        steps += [
            "      - id: build",
            "        name: Build",
            "        run: dotnet build --configuration Release --no-restore",
        ]
    if config.enabled("test"):
        steps += [
            "      - id: test",
            "        name: Run unit tests",
            '        run: dotnet test --configuration Release --no-build --logger "trx"',
        ]
    if config.enabled("sonar"):
        steps += [
            "      - id: sonar",
            "        name: SonarQube scan",
            "        env:",
            "          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}",
            "        run: |",
            "          dotnet tool install --global dotnet-sonarscanner",
            (
                '          dotnet sonarscanner begin /k:"${{ github.repository }}"'
                ' /d:sonar.host.url="${{ vars.SONAR_HOST_URL }}" /d:sonar.login="$SONAR_TOKEN"'
            ),
            "          dotnet build --configuration Release",
            '          dotnet sonarscanner end /d:sonar.login="$SONAR_TOKEN"',
        ]

    steps_block = "\n".join(steps)
    return (
        "name: CI\n"
        "on: [push, workflow_dispatch]\n"  # commit trigger (FR-N.4) + manual run
        "permissions:\n"
        "  contents: read\n"
        "jobs:\n"
        "  ci:\n"
        f"    runs-on: {discovery.runner}\n"
        "    steps:\n"
        f"{steps_block}\n"
    )


class NetCoreWorkflowGenerator(WorkflowGenerator):
    """Emit the .NET Core CI workflow as a :class:`WorkflowArtifact`."""

    def generate(
        self,
        discovery: Discovery,
        config: StepConfig,
        feedback: list[str] | None = None,
    ) -> WorkflowArtifact:
        content = render_netcore_ci(discovery, config)
        return WorkflowArtifact(primary_path=WORKFLOW_PATH, files={WORKFLOW_PATH: content})
