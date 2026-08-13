"""Minimal GitHub REST helpers for classification and organization traversal.

Reads only — the orchestrator never writes to a repository. Uses the git *trees*
API to list a repo's files without cloning (cheaper at 1,400-repo scale) and the
*contents* API to read a single file for the classification heuristic. The token
is optional for public repos and required for private ones.
"""
from __future__ import annotations

import base64
import os

import httpx
from agent_contracts import RepoRef

GITHUB_API = os.environ.get("GITHUB_API", "https://api.github.com")


class GitHub:
    """A thin read-only GitHub REST client."""

    def __init__(self, token: str | None = None, timeout: float = 30.0) -> None:
        self._token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("AGENT_GITHUB__TOKEN")
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/vnd.github+json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def list_paths(self, repo: RepoRef) -> list[str]:
        """List every file path in the repo's default branch (recursive tree)."""
        url = f"{GITHUB_API}/repos/{repo.full_name}/git/trees/{repo.default_branch}?recursive=1"
        response = httpx.get(url, headers=self._headers(), timeout=self._timeout)
        response.raise_for_status()
        tree = response.json().get("tree", [])
        return [entry["path"] for entry in tree if entry.get("type") == "blob"]

    def get_file(self, repo: RepoRef, path: str) -> str:
        """Return the decoded text content of a single file."""
        url = f"{GITHUB_API}/repos/{repo.full_name}/contents/{path}"
        response = httpx.get(url, headers=self._headers(), timeout=self._timeout)
        response.raise_for_status()
        payload = response.json()
        return base64.b64decode(payload["content"]).decode("utf-8", errors="replace")

    def list_org_repos(self, org: str) -> list[RepoRef]:
        """List all repositories in an organization (paginated)."""
        repos: list[RepoRef] = []
        page = 1
        while True:
            url = f"{GITHUB_API}/orgs/{org}/repos?per_page=100&page={page}"
            response = httpx.get(url, headers=self._headers(), timeout=self._timeout)
            response.raise_for_status()
            batch = response.json()
            if not batch:
                break
            for item in batch:
                repos.append(
                    RepoRef(
                        url=item["html_url"],
                        owner=item["owner"]["login"],
                        name=item["name"],
                        default_branch=item.get("default_branch", "main"),
                    )
                )
            if len(batch) < 100:
                break
            page += 1
        return repos
