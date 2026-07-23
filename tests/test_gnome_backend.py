"""Tests for GNOME backend Wayland / launch_only behaviour."""

from workset.backends.gnome import GnomeBackend


def test_launch_only_on_wayland(monkeypatch):
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "GNOME")
    assert GnomeBackend().launch_only is True


def test_launch_only_false_on_x11_with_wmctrl(monkeypatch):
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "GNOME")
    monkeypatch.setattr("workset.backends.gnome.shutil.which", lambda _: "/usr/bin/wmctrl")
    assert GnomeBackend().launch_only is False


def test_launch_only_true_on_x11_without_wmctrl(monkeypatch):
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "GNOME")
    monkeypatch.setattr("workset.backends.gnome.shutil.which", lambda _: None)
    assert GnomeBackend().launch_only is True
