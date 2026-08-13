"""Repository classification — deterministic heuristic, optionally LLM-assisted.

The heuristic inspects the file list and, for .NET, the first ``.csproj`` to tell
.NET Core (SDK-style / ``net5.0``+) from .NET Framework (``net4x`` / ``v4.x``).
When a model is configured the :class:`Classifier` tries the LLM first and falls
back to the heuristic on any error — so the system always produces a verdict, and
runs with no API key (heuristic-only) for the Stage-1 demo.
"""
from __future__ import annotations

import logging
import re

from agent_contracts import Classification, ClassificationMethod, RepoRef, TechStack

from .github import GitHub

log = logging.getLogger("agent.classify")

# .NET Framework markers checked first: old-style `v4.x` or SDK-style `net4x`.
_FRAMEWORK = re.compile(r"<TargetFrameworkVersion>\s*v4|<TargetFramework>\s*net4", re.IGNORECASE)
# .NET Core / modern .NET: netcoreapp*, or net5.0 and above.
_CORE = re.compile(r"<TargetFramework>\s*(netcoreapp|net[5-9])", re.IGNORECASE)
_COBOL_EXTENSIONS = (".cbl", ".cob", ".cobol", ".cpy")


class HeuristicClassifier:
    """Classify from file signatures without any model."""

    def __init__(self, github: GitHub) -> None:
        self._github = github

    def classify(self, repo: RepoRef) -> Classification:
        paths = self._github.list_paths(repo)

        cobol = [p for p in paths if p.lower().endswith(_COBOL_EXTENSIONS)]
        if cobol:
            # IBM i vs Unisys cannot be told apart from source alone, and both
            # COBOL agents are pending — this routes to the exception list.
            return Classification(
                stack=TechStack.COBOL_IBM,
                confidence=0.4,
                method=ClassificationMethod.HEURISTIC,
                evidence=cobol[:3],
            )

        csprojs = [p for p in paths if p.lower().endswith(".csproj")]
        if csprojs:
            content = self._github.get_file(repo, csprojs[0])
            if _FRAMEWORK.search(content):
                stack, confidence = TechStack.DOTNET_FRAMEWORK, 0.9
            elif _CORE.search(content) or "Microsoft.NET.Sdk" in content:
                stack, confidence = TechStack.DOTNET_CORE, 0.9
            else:
                # A csproj with no clear marker — old-style projects are .NET FX.
                stack, confidence = TechStack.DOTNET_FRAMEWORK, 0.5
            return Classification(
                stack=stack,
                confidence=confidence,
                method=ClassificationMethod.HEURISTIC,
                evidence=[csprojs[0]],
            )

        return Classification(
            stack=TechStack.UNKNOWN,
            confidence=1.0,
            method=ClassificationMethod.HEURISTIC,
            evidence=["no recognized project files"],
        )


class Classifier:
    """LLM-assisted classifier that falls back to the heuristic."""

    def __init__(self, github: GitHub, model: str | None = None) -> None:
        self._github = github
        self._heuristic = HeuristicClassifier(github)
        self._model = model

    def classify(self, repo: RepoRef) -> Classification:
        if self._model:
            try:
                return self._llm_classify(repo)
            except Exception as exc:  # noqa: BLE001 -- fall back to the heuristic on any LLM error
                log.warning("LLM classification failed for %s (%s); using heuristic", repo.full_name, exc)
        return self._heuristic.classify(repo)

    def _llm_classify(self, repo: RepoRef) -> Classification:
        import json

        from anthropic import Anthropic  # lazy: only needed when a model is set

        paths = self._github.list_paths(repo)
        csprojs = [p for p in paths if p.lower().endswith(".csproj")]
        snippet = self._github.get_file(repo, csprojs[0])[:2000] if csprojs else ""

        response = Anthropic().messages.create(
            model=self._model,
            max_tokens=512,
            system=(
                "Classify a repository into exactly one technology set: dotnet_core, "
                "dotnet_framework, cobol_ibm, cobol_unisys, or unknown. Respond with ONLY "
                'JSON: {"stack": "...", "confidence": 0.0-1.0, "evidence": ["..."]}.'
            ),
            messages=[
                {
                    "role": "user",
                    "content": f"Files:\n{chr(10).join(paths[:100])}\n\nFirst .csproj:\n{snippet}",
                }
            ],
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        data = json.loads(text)
        return Classification(
            stack=TechStack(data["stack"]),
            confidence=float(data["confidence"]),
            method=ClassificationMethod.LLM,
            evidence=list(data.get("evidence", [])),
        )
