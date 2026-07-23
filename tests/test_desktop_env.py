"""Tests for multi-DE desktop detection and GNOME purity."""

from workset.backends.gnome import GnomeBackend
from workset.backends.kde import KdeBackend
from workset.desktop_env import desktop_tokens, detect_desktop_env, is_pure_gnome


def test_desktop_tokens_split(monkeypatch):
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "Budgie:GNOME")
    assert desktop_tokens() == ("BUDGIE", "GNOME")


def test_budgie_is_not_pure_gnome(monkeypatch):
    monkeypatch.delenv("HYPRLAND_INSTANCE_SIGNATURE", raising=False)
    monkeypatch.delenv("SWAYSOCK", raising=False)
    monkeypatch.delenv("I3SOCK", raising=False)
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "Budgie:GNOME")
    assert detect_desktop_env().family == "budgie"
    assert is_pure_gnome() is False
    assert GnomeBackend().is_available() is False


def test_gnome_pure(monkeypatch):
    monkeypatch.delenv("HYPRLAND_INSTANCE_SIGNATURE", raising=False)
    monkeypatch.delenv("SWAYSOCK", raising=False)
    monkeypatch.delenv("I3SOCK", raising=False)
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "GNOME")
    assert detect_desktop_env().family == "gnome"
    assert is_pure_gnome() is True
    assert GnomeBackend().is_available() is True


def test_plasma_tokens(monkeypatch):
    monkeypatch.delenv("HYPRLAND_INSTANCE_SIGNATURE", raising=False)
    monkeypatch.delenv("SWAYSOCK", raising=False)
    monkeypatch.delenv("I3SOCK", raising=False)
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "KDE")
    monkeypatch.setattr("workset.backends.kde.shutil.which", lambda _: "/usr/bin/wmctrl")
    assert detect_desktop_env().family == "plasma"
    assert KdeBackend().is_available() is True


def test_xfce_family(monkeypatch):
    monkeypatch.delenv("HYPRLAND_INSTANCE_SIGNATURE", raising=False)
    monkeypatch.delenv("SWAYSOCK", raising=False)
    monkeypatch.delenv("I3SOCK", raising=False)
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "XFCE")
    assert detect_desktop_env().family == "xfce"


def test_cinnamon_family(monkeypatch):
    monkeypatch.delenv("HYPRLAND_INSTANCE_SIGNATURE", raising=False)
    monkeypatch.delenv("SWAYSOCK", raising=False)
    monkeypatch.delenv("I3SOCK", raising=False)
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "X-Cinnamon")
    assert detect_desktop_env().family == "cinnamon"
