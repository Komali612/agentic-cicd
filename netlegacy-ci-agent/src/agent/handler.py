"""Request handler — bridges the agent-core HTTP service to the ci-authoring engine.

Parses the orchestrator's :class:`~agent_contracts.WorkerRequest`, runs the
deterministic Discover→Generate→Validate→Deploy loop with the .NET Framework
discoverer + generator, and returns the :class:`~agent_contracts.WorkerResult`.
"""
from __future__ import annotations

from agent_contracts import WorkerRequest
from agent_core import Handler
from ci_authoring import AuthoringEngine

from .discover import NetLegacyDiscoverer
from .generate import NetLegacyWorkflowGenerator


class NetLegacyCIHandler(Handler):
    """agent-core handler that runs the .NET Framework CI-authoring loop."""

    def __init__(self) -> None:
        self._engine = AuthoringEngine(NetLegacyDiscoverer(), NetLegacyWorkflowGenerator())

    def handle(self, ctx) -> dict:
        raw = ctx.payload.get("input", ctx.payload)
        request = WorkerRequest.model_validate(raw)
        result = self._engine.run(request)
        return ctx.done(result.model_dump(mode="json"))
