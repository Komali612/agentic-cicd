"""Request handler — bridges the agent-core HTTP service to the ci-authoring engine.

The orchestrator POSTs a serialized :class:`~agent_contracts.WorkerRequest` to this
agent's ``/run`` endpoint. The handler parses it, runs the deterministic
Discover→Generate→Validate→Deploy loop with the .NET Core discoverer + generator,
and returns the :class:`~agent_contracts.WorkerResult`.
"""
from __future__ import annotations

from agent_contracts import WorkerRequest
from agent_core import Handler
from ci_authoring import AuthoringEngine

from .discover import NetCoreDiscoverer
from .generate import NetCoreWorkflowGenerator


class NetCoreCIHandler(Handler):
    """agent-core handler that runs the .NET Core CI-authoring loop."""

    def __init__(self) -> None:
        self._engine = AuthoringEngine(NetCoreDiscoverer(), NetCoreWorkflowGenerator())

    def handle(self, ctx) -> dict:
        # AgentClient sends {"input": <WorkerRequest>}; accept a bare request too.
        raw = ctx.payload.get("input", ctx.payload)
        request = WorkerRequest.model_validate(raw)
        result = self._engine.run(request)
        return ctx.done(result.model_dump(mode="json"))
