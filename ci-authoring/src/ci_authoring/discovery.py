"""The Discover phase abstraction.

Each stack (NetCore, NetLegacy, COBOL once scoped) provides a concrete
:class:`Discoverer`. Discovery must be deterministic and side-effect free — it
only reads the cloned working tree — so the same repo always yields the same
:class:`~ci_authoring.models.Discovery`.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from .models import Discovery


class Discoverer(ABC):
    """Inspect a cloned repository and produce a :class:`Discovery`."""

    @abstractmethod
    def discover(self, repo_path: Path) -> Discovery:
        """Read ``repo_path`` and return what the pipeline generator needs to know."""
        raise NotImplementedError
