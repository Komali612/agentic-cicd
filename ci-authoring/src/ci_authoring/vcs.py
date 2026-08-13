"""Version-control operations: clone, detect an existing pipeline, open a PR.

Git is invoked as a subprocess, so an agent's runtime image must include ``git``.
The GitHub REST API opens the pull request. The token is read from
``GITHUB_TOKEN`` and is deliberately never placed in argv or logged.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import httpx
from agent_contracts import RepoRef

from .models import WorkflowArtifact

GITHUB_API = os.environ.get("GITHUB_API", "https://api.github.com")
_PR_BRANCH = "agentic-ci/add-pipeline"


def _git(*args: str) -> str:
    """Run a git command, returning stdout (raises CalledProcessError on failure)."""
    result = subprocess.run(["git", *args], check=True, capture_output=True, text=True)
    return result.stdout.strip()


def _token() -> str:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("AGENT_GITHUB__TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is required to push a branch and open a pull request")
    return token


def _auth_url(url: str) -> str:
    """Embed the token in an https URL so git can push."""
    parsed = urlparse(url)
    return f"{parsed.scheme}://x-access-token:{_token()}@{parsed.netloc}{parsed.path}"


def clone_repo(repo: RepoRef) -> Path:
    """Shallow-clone ``repo`` into a fresh temp directory and return the path."""
    workdir = Path(tempfile.mkdtemp(prefix="ci-authoring-"))
    dest = workdir / "repo"
    _git("clone", "--depth", "1", repo.url, str(dest))
    return dest


def find_existing_workflow(repo_path: Path) -> str | None:
    """Return the repo-relative path of the first existing workflow, if any."""
    workflows = repo_path / ".github" / "workflows"
    if not workflows.is_dir():
        return None
    for path in sorted(workflows.glob("*.y*ml")):
        return str(path.relative_to(repo_path))
    return None


def read_workflow(repo_path: Path, rel_path: str) -> WorkflowArtifact:
    """Load an existing workflow file into a :class:`WorkflowArtifact`."""
    content = (repo_path / rel_path).read_text(encoding="utf-8")
    return WorkflowArtifact(primary_path=rel_path, files={rel_path: content})


def open_pull_request(
    repo: RepoRef,
    repo_path: Path,
    artifact: WorkflowArtifact,
    branch: str = _PR_BRANCH,
) -> str:
    """Write the artifact's files, commit them on a branch, push, and open a PR.

    Returns:
        The HTML URL of the opened pull request.
    """
    for rel_path, content in artifact.files.items():
        target = repo_path / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    _git("-C", str(repo_path), "checkout", "-b", branch)
    _git("-C", str(repo_path), "add", "-A")
    _git(
        "-C", str(repo_path),
        "-c", "user.email=agentic-ci@users.noreply.github.com",
        "-c", "user.name=agentic-ci",
        "commit", "-m", "Add CI pipeline (agentic CI/CD framework)",
    )
    _git("-C", str(repo_path), "push", "-u", _auth_url(repo.url), branch)

    headers = {"Authorization": f"Bearer {_token()}", "Accept": "application/vnd.github+json"}
    response = httpx.post(
        f"{GITHUB_API}/repos/{repo.full_name}/pulls",
        headers=headers,
        timeout=30,
        json={
            "title": "Add CI pipeline",
            "head": branch,
            "base": repo.default_branch,
            "body": (
                "Opened by the agentic CI/CD framework. Adds a CI pipeline for this "
                "repository. Review before merging — the agent never merges its own PR."
            ),
        },
    )
    response.raise_for_status()
    return response.json()["html_url"]
