"""Routing table: TechStack -> the worker agent that handles it.

Worker URLs come from the environment (with in-cluster service-name defaults).
Only technology sets with a live CI worker are routable in Stage 1; COBOL stacks
and UNKNOWN have no route on purpose, so the orchestrator sends them to the
exception list.
"""
from __future__ import annotations

import os

from agent_contracts import AgentClient, TechStack

_DEFAULT_URLS = {
    TechStack.DOTNET_CORE: "http://netcore-ci:8080",
    TechStack.DOTNET_FRAMEWORK: "http://netlegacy-ci:8080",
}
_ENV_KEYS = {
    TechStack.DOTNET_CORE: "WORKER_NETCORE_CI_URL",
    TechStack.DOTNET_FRAMEWORK: "WORKER_NETLEGACY_CI_URL",
}


def build_routes() -> dict[TechStack, AgentClient]:
    """Build the stack -> worker-client routing table from the environment."""
    return {
        stack: AgentClient(os.environ.get(_ENV_KEYS[stack], default))
        for stack, default in _DEFAULT_URLS.items()
    }
