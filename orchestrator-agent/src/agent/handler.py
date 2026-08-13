"""agent-core handler: resolve the input into repositories, orchestrate, report.

Accepts any of the three input shapes the PRD requires (FR-0.1): a single
``repo_url``, a list of ``repos``, or an ``org`` to traverse.
"""
from __future__ import annotations

from agent_contracts import RepoRef
from agent_core import Handler

from .classify import Classifier
from .config import settings
from .github import GitHub
from .orchestrator import Orchestrator
from .router import build_routes


class OrchestratorHandler(Handler):
    """Runs one orchestration pass over the requested repositories."""

    def __init__(self) -> None:
        self._github = GitHub()
        self._orchestrator = Orchestrator(
            Classifier(self._github, model=settings.model), build_routes()
        )

    def handle(self, ctx) -> dict:
        raw = ctx.payload.get("input", ctx.payload)
        repos = self._resolve_repos(raw)
        report = self._orchestrator.run(repos)
        return ctx.done(report.model_dump(mode="json"))

    def _resolve_repos(self, raw) -> list[RepoRef]:
        """Expand a repo URL / list / org into concrete :class:`RepoRef` objects."""
        if isinstance(raw, str):
            raw = {"repo_url": raw}
        repos: list[RepoRef] = []
        if raw.get("repo_url"):
            repos.append(RepoRef.from_url(raw["repo_url"]))
        for url in raw.get("repos") or []:
            repos.append(RepoRef.from_url(url))
        if raw.get("org"):
            repos.extend(self._github.list_org_repos(raw["org"]))
        return repos
