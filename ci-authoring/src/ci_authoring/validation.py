"""Deterministic validation of a generated workflow (PRD Validate phase).

Structural, offline checks only — this **never executes** the pipeline, pulls an
image, or touches live infrastructure. It confirms the YAML parses, that the
required steps are actually present, and that the trigger wiring exists.

Note the GitHub Actions ``on:`` gotcha: PyYAML parses the bare key ``on`` as the
boolean ``True``, so we accept either key form when checking for a trigger.
"""
from __future__ import annotations

from typing import Any

import yaml

from .models import StepConfig, ValidationResult, WorkflowArtifact


def validate_workflow(artifact: WorkflowArtifact, config: StepConfig) -> ValidationResult:
    """Validate the primary workflow file against the required-step configuration."""
    content = artifact.files.get(artifact.primary_path, "")
    if not content.strip():
        return ValidationResult(ok=False, errors=["workflow file is empty"])

    try:
        doc = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        return ValidationResult(ok=False, errors=[f"workflow is not valid YAML: {exc}"])

    errors: list[str] = []
    if not isinstance(doc, dict):
        return ValidationResult(ok=False, errors=["workflow root is not a mapping"])

    # Trigger present. PyYAML turns the key `on` into boolean True.
    if "on" not in doc and True not in doc:
        errors.append("workflow has no trigger ('on')")

    if "jobs" not in doc or not isinstance(doc["jobs"], dict) or not doc["jobs"]:
        errors.append("workflow has no jobs")

    # Every enabled required step must be present, matched by step id or name.
    present = _collect_step_markers(doc)
    for step in config.active_steps():
        if not any(step in marker for marker in present):
            errors.append(f"required step missing: {step}")

    return ValidationResult(ok=not errors, errors=errors)


def _collect_step_markers(doc: dict[str, Any]) -> list[str]:
    """Lower-cased ids and names of every step across every job."""
    markers: list[str] = []
    for job in (doc.get("jobs") or {}).values():
        if not isinstance(job, dict):
            continue
        for step in job.get("steps") or []:
            if not isinstance(step, dict):
                continue
            markers.append(str(step.get("id") or "").lower())
            markers.append(str(step.get("name") or "").lower())
    return markers
