"""Tests for the .NET Core Discoverer."""
from __future__ import annotations

from agent.discover import NetCoreDiscoverer

CSPROJ = """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
  </PropertyGroup>
</Project>
"""


def test_discovers_framework_and_linux_runner(tmp_path):
    (tmp_path / "Widget.csproj").write_text(CSPROJ)
    (tmp_path / "Widget.sln").write_text("Microsoft Visual Studio Solution File")

    discovery = NetCoreDiscoverer().discover(tmp_path)

    assert discovery.runner == "ubuntu-latest"
    assert discovery.build_tool == "dotnet"
    assert discovery.target_framework == "net8.0"
    assert "Widget.csproj" in discovery.project_files
    assert discovery.solution == "Widget.sln"


def test_ignores_build_output(tmp_path):
    (tmp_path / "Widget.csproj").write_text(CSPROJ)
    obj = tmp_path / "obj"
    obj.mkdir()
    (obj / "Generated.csproj").write_text(CSPROJ)

    discovery = NetCoreDiscoverer().discover(tmp_path)
    assert discovery.project_files == ["Widget.csproj"]
