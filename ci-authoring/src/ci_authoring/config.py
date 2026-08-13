"""Loading per-application step configuration (PRD CR-2).

Resolution order (later wins):

1. built-in defaults (:class:`~ci_authoring.models.StepConfig`),
2. an ``.agentci.json`` file committed in the repository, if present,
3. overrides passed in the :class:`~agent_contracts.WorkerRequest` (``config``).

A repo owner controls which steps run by committing ``.agentci.json`` — the steps
are data, never hard-coded into the agent.
"""
from __future__ import annotations

import json
from pathlib import Path

from .models import StepConfig

#: Config file an application may commit to control its pipeline steps.
CONFIG_FILENAME = ".agentci.json"


def load_step_config(repo_path: Path, overrides: dict | None = None) -> StepConfig:
    """Resolve the effective :class:`StepConfig` for a repository."""
    data: dict = {}
    config_file = repo_path / CONFIG_FILENAME
    if config_file.exists():
        data.update(json.loads(config_file.read_text(encoding="utf-8")))
    if overrides:
        data.update(overrides)
    return StepConfig(**data)
