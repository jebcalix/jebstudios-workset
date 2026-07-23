"""Tests for window matching."""

from workset.backends.matching import pick_matching_windows
from workset.config.models import WindowMatch


def test_window_matches_wm_class():
    clients = [{"class": "Cursor", "title": "main.py"}]
    assert pick_matching_windows(clients, WindowMatch(wm_class="Cursor"), ["cursor"])


def test_window_matches_title():
    clients = [{"class": "foo", "title": "My Project - Cursor"}]
    assert pick_matching_windows(clients, WindowMatch(title="Project"), ["cursor"])


def test_instance_filter():
    clients = [
        {"id": "1", "class": "term", "title": "a"},
        {"id": "2", "class": "term", "title": "b"},
    ]
    result = pick_matching_windows(clients, WindowMatch(wm_class="term", instance=2), ["gnome-terminal"])
    assert len(result) == 1
    assert result[0]["id"] == "2"
