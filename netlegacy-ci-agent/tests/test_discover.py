"""Tests for the .NET Framework Discoverer."""
from __future__ import annotations

from agent.discover import NetLegacyDiscoverer

# Old-style .NET Framework csproj (note the MSBuild 2003 XML namespace).
CSPROJ = """<?xml version="1.0" encoding="utf-8"?>
<Project ToolsVersion="15.0" xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
  <PropertyGroup>
    <TargetFrameworkVersion>v4.8</TargetFrameworkVersion>
  </PropertyGroup>
</Project>
"""


def test_discovers_windows_runner_and_framework_version(tmp_path):
    (tmp_path / "Legacy.csproj").write_text(CSPROJ)
    (tmp_path / "Legacy.sln").write_text("Microsoft Visual Studio Solution File")

    discovery = NetLegacyDiscoverer().discover(tmp_path)

    assert discovery.runner == "windows-latest"
    assert discovery.build_tool == "msbuild"
    assert discovery.target_framework_version == "v4.8"
    assert discovery.has_dockerfile is False
    assert discovery.solution == "Legacy.sln"
