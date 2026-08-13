"""Local end-to-end demo — no clone, no network, no PR.

Runs the installed CI worker agent's Discover → Generate → Validate phases against
a sample repository on disk and prints the generated workflow + validation verdict.
Because both worker agents use the package name ``agent``, run this inside the
venv of the worker you want to demo:

    # in the netcore-ci-agent venv
    python demo.py ../samples/sample-netcore-app

    # in the netlegacy-ci-agent venv
    python demo.py ../samples/sample-netlegacy-app

It discovers the agent's Discoverer/Generator by introspection, so the same
script works for any stack.
"""
from __future__ import annotations

import importlib
import inspect
import sys
from pathlib import Path

from ci_authoring import Discoverer, StepConfig, WorkflowGenerator, validate_workflow


def _concrete(module_name: str, base: type):
    module = importlib.import_module(module_name)
    for _, obj in inspect.getmembers(module, inspect.isclass):
        if issubclass(obj, base) and obj is not base and obj.__module__ == module.__name__:
            return obj()
    raise SystemExit(f"no concrete {base.__name__} found in {module_name}")


def main(repo_path: str) -> None:
    discoverer = _concrete("agent.discover", Discoverer)
    generator = _concrete("agent.generate", WorkflowGenerator)

    discovery = discoverer.discover(Path(repo_path))
    config = StepConfig()
    artifact = generator.generate(discovery, config)
    result = validate_workflow(artifact, config)

    print("── Discovery ─────────────────────────────────────────")
    print(discovery.model_dump())
    print("\n── Validation ────────────────────────────────────────")
    print(f"ok={result.ok} errors={result.errors}")
    print("\n── Generated workflow ────────────────────────────────")
    print(artifact.files[artifact.primary_path])


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python demo.py <path-to-sample-repo>")
    main(sys.argv[1])
