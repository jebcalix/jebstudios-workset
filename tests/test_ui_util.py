"""Tests for UI helpers (sin GTK)."""

import pytest

from workset.ui.util import format_exec, parse_exec, slugify


def test_slugify():
    assert slugify("Mi Setup") == "mi-setup"
    assert slugify("  Hello_World!! ") == "hello-world"
    assert slugify("@@@") == "perfil"


def test_parse_exec():
    assert parse_exec("cursor /tmp") == ["cursor", "/tmp"]
    assert parse_exec('bash -c "echo hi"') == ["bash", "-c", "echo hi"]


def test_parse_exec_empty():
    with pytest.raises(ValueError):
        parse_exec("   ")


def test_format_exec_roundtrip():
    cmd = ["gnome-terminal", "--working-directory=/tmp"]
    assert parse_exec(format_exec(cmd)) == cmd
