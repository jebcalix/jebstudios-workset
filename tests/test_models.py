"""Tests for profile models."""

import pytest
from pydantic import ValidationError

from workset.config.models import AppEntry, WorksetProfile, WindowState


def test_valid_profile():
    profile = WorksetProfile.model_validate(
        {
            "name": "Dev",
            "apps": [{"exec": ["echo", "hello"]}],
        }
    )
    assert profile.name == "Dev"
    assert len(profile.apps) == 1
    assert profile.version == 1


def test_app_entry_defaults():
    app = AppEntry(exec=["cursor"])
    assert app.state == WindowState.NORMAL
    assert app.delay_ms == 0
    assert app.timeout_ms == 15000


def test_exec_must_be_non_empty():
    with pytest.raises(ValidationError):
        AppEntry(exec=[])

    with pytest.raises(ValidationError):
        AppEntry(exec=[""])


def test_profile_requires_at_least_one_app():
    with pytest.raises(ValidationError):
        WorksetProfile.model_validate({"name": "Empty", "apps": []})
