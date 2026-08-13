"""Tests for the heuristic classifier (no network — GitHub is faked)."""
from __future__ import annotations

from agent_contracts import RepoRef, TechStack

from agent.classify import HeuristicClassifier

REPO = RepoRef.from_url("https://github.com/acme/widget")

SDK_CORE = (
    '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup>'
    "<TargetFramework>net8.0</TargetFramework></PropertyGroup></Project>"
)
OLD_STYLE_FX = (
    "<Project><PropertyGroup>"
    "<TargetFrameworkVersion>v4.8</TargetFrameworkVersion></PropertyGroup></Project>"
)
SDK_FX_NET48 = (
    '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup>'
    "<TargetFramework>net48</TargetFramework></PropertyGroup></Project>"
)


class FakeGitHub:
    def __init__(self, paths, files=None):
        self._paths = paths
        self._files = files or {}

    def list_paths(self, repo):
        return self._paths

    def get_file(self, repo, path):
        return self._files[path]


def _classify(paths, files=None):
    return HeuristicClassifier(FakeGitHub(paths, files)).classify(REPO)


def test_dotnet_core_sdk_style():
    result = _classify(["src/Widget.csproj"], {"src/Widget.csproj": SDK_CORE})
    assert result.stack == TechStack.DOTNET_CORE


def test_dotnet_framework_old_style():
    result = _classify(["Legacy.csproj"], {"Legacy.csproj": OLD_STYLE_FX})
    assert result.stack == TechStack.DOTNET_FRAMEWORK


def test_dotnet_framework_sdk_net48_not_misread_as_core():
    # net48 is SDK-style but still .NET Framework — must not be classified as Core.
    result = _classify(["App.csproj"], {"App.csproj": SDK_FX_NET48})
    assert result.stack == TechStack.DOTNET_FRAMEWORK


def test_cobol_routes_toward_exception():
    result = _classify(["src/PGM1.CBL"])
    assert result.stack == TechStack.COBOL_IBM


def test_unknown_when_no_project_files():
    result = _classify(["README.md", "index.js"])
    assert result.stack == TechStack.UNKNOWN
