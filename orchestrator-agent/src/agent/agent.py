"""FROZEN frame — assembles the Orchestrator agent.

The orchestration loop is deterministic; the optional LLM assist lives inside the
classifier. ``model`` is passed through so classification can use it when set.
"""
from agent_core import Agent

from .config import settings
from .handler import OrchestratorHandler
from .prompts import SYSTEM_PROMPT


def build_agent() -> Agent:
    return Agent(
        name=settings.name,
        prompt=SYSTEM_PROMPT,
        handler=OrchestratorHandler(),
        model=settings.model,
    )
