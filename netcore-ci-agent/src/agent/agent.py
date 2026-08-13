"""FROZEN frame — assembles the NetCoreCI agent.

This worker is deterministic: its handler runs the ci-authoring engine directly
rather than an LLM tool-loop, so the pipeline output is reproducible. The model
field is accepted (for optional failure diagnosis) but the happy path needs no
API key.
"""
from agent_core import Agent

from .config import settings
from .handler import NetCoreCIHandler
from .prompts import SYSTEM_PROMPT


def build_agent() -> Agent:
    return Agent(
        name=settings.name,
        prompt=SYSTEM_PROMPT,
        handler=NetCoreCIHandler(),
        model=settings.model,
    )
