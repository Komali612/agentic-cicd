"""Discover phase for .NET Core (6/7/8) repositories.

Reads the working tree to determine the solution/project layout and the target
framework, and selects a Linux runner (the .NET Core build path). Deterministic
and side-effect free.
"""
from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

from ci_authoring import Discoverer, Discovery

#: Directories that hold build output, not source — skipped during discovery.
_IGNORE_DIRS = {"bin", "obj", ".git"}


class DotNetCoreDiscovery(Discovery):
    """Discovery enriched with .NET-specific fields."""

    target_framework: str | None = None
    solution: str | None = None


class NetCoreDiscoverer(Discoverer):
    """Inspect a .NET Core repository."""

    def discover(self, repo_path: Path) -> DotNetCoreDiscovery:
        csproj_files = self._find(repo_path, "*.csproj")
        solution_files = self._find(repo_path, "*.sln")

        target_framework: str | None = None
        for rel in csproj_files:
            target_framework = _read_target_framework(repo_path / rel)
            if target_framework:
                break

        return DotNetCoreDiscovery(
            runner="ubuntu-latest",  # .NET Core builds on Linux
            build_tool="dotnet",
            project_files=solution_files + csproj_files,
            has_dockerfile=(repo_path / "Dockerfile").exists(),
            target_framework=target_framework,
            solution=solution_files[0] if solution_files else None,
        )

    @staticmethod
    def _find(repo_path: Path, pattern: str) -> list[str]:
        """Repo-relative matches for ``pattern``, ignoring build-output dirs."""
        found = [
            str(path.relative_to(repo_path))
            for path in repo_path.rglob(pattern)
            if not _IGNORE_DIRS & set(path.parts)
        ]
        return sorted(found)


def _read_target_framework(csproj: Path) -> str | None:
    """Read ``<TargetFramework>``/``<TargetFrameworks>`` from a csproj (first wins)."""
    try:
        root = ET.fromstring(csproj.read_text(encoding="utf-8"))
    except (ET.ParseError, OSError):
        return None
    for element in root.iter():
        tag = element.tag.rsplit("}", 1)[-1]  # strip any XML namespace
        if tag in ("TargetFramework", "TargetFrameworks") and element.text:
            return element.text.split(";")[0].strip()
    return None
