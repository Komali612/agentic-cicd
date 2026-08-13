"""Generate phase for .NET Framework 4.8: a deterministic Windows GHA workflow.

Runs on a Windows runner and builds with NuGet + MSBuild (PRD FR-L.5). The
security/quality step for the Stage-1 demo is SonarQube (via the MSBuild scanner).
Per FR-L.7 this stack produces an MSI/DLL — there is **no container image and no
Helm chart**, so none is generated.
"""
from __future__ import annotations

from ci_authoring import Discovery, StepConfig, WorkflowArtifact, WorkflowGenerator

WORKFLOW_PATH = ".github/workflows/ci.yml"


def render_netlegacy_ci(discovery: Discovery, config: StepConfig) -> str:
    """Render the .NET Framework CI workflow YAML for ``discovery`` and ``config``."""
    steps: list[str] = [
        "      - uses: actions/checkout@v4",
        "      - name: Setup MSBuild",
        "        uses: microsoft/setup-msbuild@v2",
        "      - name: Setup NuGet",
        "        uses: nuget/setup-nuget@v2",
        "      - name: Restore",
        "        run: nuget restore",
    ]
    if config.enabled("build"):
        steps += [
            "      - id: build",
            "        name: Build",
            "        run: msbuild /p:Configuration=Release",
        ]
    if config.enabled("test"):
        steps += [
            "      - id: test",
            "        name: Run unit tests",
            "        run: dotnet test --configuration Release --no-build",
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
                '          dotnet-sonarscanner begin /k:"${{ github.repository }}"'
                ' /d:sonar.host.url="${{ vars.SONAR_HOST_URL }}" /d:sonar.login="$env:SONAR_TOKEN"'
            ),
            "          msbuild /p:Configuration=Release",
            '          dotnet-sonarscanner end /d:sonar.login="$env:SONAR_TOKEN"',
        ]

    steps_block = "\n".join(steps)
    return (
        "name: CI\n"
        "on: [push, workflow_dispatch]\n"  # commit trigger (FR-L.5) + manual run
        "permissions:\n"
        "  contents: read\n"
        "jobs:\n"
        "  ci:\n"
        f"    runs-on: {discovery.runner}\n"
        "    steps:\n"
        f"{steps_block}\n"
    )


class NetLegacyWorkflowGenerator(WorkflowGenerator):
    """Emit the .NET Framework CI workflow as a :class:`WorkflowArtifact`."""

    def generate(
        self,
        discovery: Discovery,
        config: StepConfig,
        feedback: list[str] | None = None,
    ) -> WorkflowArtifact:
        content = render_netlegacy_ci(discovery, config)
        return WorkflowArtifact(primary_path=WORKFLOW_PATH, files={WORKFLOW_PATH: content})
