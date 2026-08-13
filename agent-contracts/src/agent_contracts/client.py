"""AgentClient — the inter-agent communication seam, made real.

The orchestrator calls a worker agent over HTTP by POSTing to the worker's
``/run`` endpoint. This is the production form of the messaging seam that
``agent-core`` deliberately left dormant. Workers are ordinary agent-core HTTP
services, so their response envelope is ``{"agent": ..., "result": {...}}`` and
the ``result`` is a serialized :class:`~agent_contracts.worker.WorkerResult`.
"""
from __future__ import annotations

import httpx

from .worker import WorkerRequest, WorkerResult

DEFAULT_TIMEOUT_SECONDS = 300.0


class AgentClient:
    """A thin, typed HTTP client for invoking one worker agent."""

    def __init__(self, base_url: str, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def invoke(self, request: WorkerRequest) -> WorkerResult:
        """Invoke the worker synchronously and return its typed result.

        Raises:
            httpx.HTTPStatusError: if the worker responds with a non-2xx status.
            KeyError / pydantic.ValidationError: if the response envelope or the
                embedded ``WorkerResult`` is malformed.
        """
        response = httpx.post(
            f"{self._base_url}/run",
            json={"input": request.model_dump(mode="json")},
            timeout=self._timeout,
        )
        response.raise_for_status()
        envelope = response.json()
        return WorkerResult.model_validate(envelope["result"])
