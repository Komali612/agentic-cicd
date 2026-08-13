"""Loads the agent's system prompt from system.md (frozen loader)."""
from pathlib import Path

SYSTEM_PROMPT = (Path(__file__).parent / "system.md").read_text(encoding="utf-8")

__all__ = ["SYSTEM_PROMPT"]
