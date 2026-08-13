"""FROZEN frame — assembles the NetLegacyCI agent.

Deterministic worker: the handler runs the ci-authoring engine directly, so the
pipeline output is reproducible.
"""
from agent_core import Agent

from .config import settings
from .handler import NetLegacyCIHandler
from .prompts import SYSTEM_PROMPT


def build_agent() -> Agent:
    return Agent(
        name=settings.name,
        prompt=SYSTEM_PROMPT,
        handler=NetLegacyCIHandler(),
        model=settings.model,
    )
