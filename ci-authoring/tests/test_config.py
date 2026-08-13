"""Tests for per-application step-configuration loading (PRD CR-2)."""
from __future__ import annotations

import json

from ci_authoring.config import load_step_config


def test_defaults_when_no_file(tmp_path):
    config = load_step_config(tmp_path)
    assert config.required_steps == ["build", "test", "sonar"]
    assert config.enabled("build")


def test_repo_config_file_is_read(tmp_path):
    (tmp_path / ".agentci.json").write_text(json.dumps({"disabled_steps": ["sonar"]}))
    config = load_step_config(tmp_path)
    assert config.enabled("build")
    assert not config.enabled("sonar")


def test_request_overrides_win(tmp_path):
    (tmp_path / ".agentci.json").write_text(json.dumps({"required_steps": ["build", "test", "sonar"]}))
    config = load_step_config(tmp_path, overrides={"required_steps": ["build"]})
    assert config.required_steps == ["build"]
