"""Technology-set classification contracts (PRD §2, §4.1).

The orchestrator classifies every repository into exactly one :class:`TechStack`
and routes it to the matching worker agent. Anything it cannot place lands in
:data:`TechStack.UNKNOWN` and goes straight to the exception list.
"""
from __future__ import annotations

import enum

from pydantic import BaseModel, Field


class TechStack(str, enum.Enum):
    """The technology sets the framework processes.

    ``COBOL_*`` and their agents are defined in the PRD but not yet specifiable;
    they are included here so the contract is stable when those agents land.
    """

    DOTNET_CORE = "dotnet_core"            # .NET Core 6/7/8 -> AKS
    DOTNET_FRAMEWORK = "dotnet_framework"  # .NET FX 4.8 -> VM/IIS
    COBOL_IBM = "cobol_ibm"                # COBOL on IBM i (pending)
    COBOL_UNISYS = "cobol_unisys"          # COBOL on Unisys (pending)
    UNKNOWN = "unknown"                    # outside the defined sets -> exception list


class ClassificationMethod(str, enum.Enum):
    """How a :class:`Classification` was reached — for auditability and telemetry."""

    LLM = "llm"
    HEURISTIC = "heuristic"


class Classification(BaseModel):
    """The orchestrator's verdict on one repository.

    ``method`` records whether the LLM or the deterministic heuristic fallback
    produced the verdict, and ``evidence`` lists the files/facts behind it so a
    human reviewing an exception never has to reconstruct the reasoning.
    """

    stack: TechStack
    confidence: float = Field(ge=0.0, le=1.0, description="0..1 confidence in the verdict")
    method: ClassificationMethod
    evidence: list[str] = Field(
        default_factory=list, description="file names or facts supporting the classification"
    )
