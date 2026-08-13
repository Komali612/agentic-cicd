"""Repository reference model.

A :class:`RepoRef` is the minimal, stable identity of a target repository as it
travels through the pipeline — from the orchestrator's discovery, through a
worker agent, and into the exception list. It intentionally carries no derived
state (language, build tooling); that lives in :mod:`agent_contracts.stacks`.
"""
from __future__ import annotations

from urllib.parse import urlparse

from pydantic import BaseModel, Field


class RepoRef(BaseModel):
    """A reference to a single target repository."""

    url: str = Field(description="HTTPS clone/browse URL, e.g. https://github.com/acme/widget")
    owner: str = Field(description="Repository owner or organization, e.g. 'acme'")
    name: str = Field(description="Repository name without owner, e.g. 'widget'")
    default_branch: str = Field(default="main", description="Branch pipelines target")

    @property
    def full_name(self) -> str:
        """``owner/name`` — the canonical GitHub identifier."""
        return f"{self.owner}/{self.name}"

    @classmethod
    def from_url(cls, url: str, default_branch: str = "main") -> RepoRef:
        """Build a :class:`RepoRef` from a repository URL.

        Raises:
            ValueError: if the URL does not contain an ``owner/name`` path.
        """
        path = urlparse(url).path.strip("/")
        owner, _, name = path.partition("/")
        name = name.removesuffix(".git")
        if not owner or not name:
            raise ValueError(f"cannot derive owner/name from URL: {url!r}")
        return cls(url=url, owner=owner, name=name, default_branch=default_branch)
