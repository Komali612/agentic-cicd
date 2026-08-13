"""Discover phase for .NET Framework 4.8 repositories.

Reads the working tree for the solution/project layout and the target framework
version, and selects a **Windows** runner (the .NET Framework / MSBuild build
path). The MSBuild ↔ Visual Studio mapping (MSBuild 17.x → VS 2022, 16.x → VS
2019, PRD §6) cannot always be derived from source alone, so it defaults to the
current toolset and is overridable via configuration.
"""
from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

from ci_authoring import Discoverer, Discovery

_IGNORE_DIRS = {"bin", "obj", ".git", "packages"}


class DotNetFrameworkDiscovery(Discovery):
    """Discovery enriched with .NET Framework-specific fields."""

    target_framework_version: str | None = None  # e.g. "v4.8"
    vs_version: str = "2022"                      # MSBuild 17.x -> VS 2022 (16.x -> 2019)
    solution: str | None = None


class NetLegacyDiscoverer(Discoverer):
    """Inspect a .NET Framework 4.8 repository."""

    def discover(self, repo_path: Path) -> DotNetFrameworkDiscovery:
        csproj_files = self._find(repo_path, "*.csproj")
        solution_files = self._find(repo_path, "*.sln")

        framework_version: str | None = None
        for rel in csproj_files:
            framework_version = _read_target_framework_version(repo_path / rel)
            if framework_version:
                break

        return DotNetFrameworkDiscovery(
            runner="windows-latest",  # .NET Framework builds on Windows (IIS target)
            build_tool="msbuild",
            project_files=solution_files + csproj_files,
            has_dockerfile=False,  # this stack has no container image
            target_framework_version=framework_version,
            solution=solution_files[0] if solution_files else None,
        )

    @staticmethod
    def _find(repo_path: Path, pattern: str) -> list[str]:
        found = [
            str(path.relative_to(repo_path))
            for path in repo_path.rglob(pattern)
            if not _IGNORE_DIRS & set(path.parts)
        ]
        return sorted(found)


def _read_target_framework_version(csproj: Path) -> str | None:
    """Read ``<TargetFrameworkVersion>`` from an old-style .NET FX csproj."""
    try:
        root = ET.fromstring(csproj.read_text(encoding="utf-8"))
    except (ET.ParseError, OSError):
        return None
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] == "TargetFrameworkVersion" and element.text:
            return element.text.strip()
    return None
