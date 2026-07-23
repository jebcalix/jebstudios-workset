"""Tests for capture engine."""

from workset.engine.capture import _window_to_app, resolve_exec_candidate
from workset.engine.desktop_files import DesktopApp, DesktopIndex


def _index_with(*apps: DesktopApp) -> DesktopIndex:
    return DesktopIndex(list(apps))


def test_window_to_app_from_wmctrl_shape(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "workset.engine.capture.shutil.which",
        lambda name: "/usr/bin/cursor" if name == "cursor" else None,
    )
    idx = _index_with(
        DesktopApp(
            id="cursor",
            name="Cursor",
            exec_argv=["cursor"],
            wm_class="Cursor",
            executable="cursor",
            path=tmp_path / "cursor.desktop",
        )
    )
    entry = _window_to_app(
        {
            "wm_class": "Cursor",
            "title": "main.py - project",
            "desktop": 1,
            "source": "wmctrl",
        },
        idx,
    )
    assert entry is not None
    assert entry.exec == ["cursor"]
    assert entry.match is not None
    assert entry.match.wm_class == "Cursor"
    assert entry.workspace == 1


def test_window_to_app_uses_desktop_exec_for_warp(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "workset.engine.capture.shutil.which",
        lambda name: "/usr/bin/warp-terminal" if name == "warp-terminal" else None,
    )
    idx = _index_with(
        DesktopApp(
            id="dev.warp.Warp",
            name="Warp",
            exec_argv=["warp-terminal"],
            wm_class="dev.warp.Warp",
            executable="warp-terminal",
            path=tmp_path / "warp.desktop",
        )
    )
    entry = _window_to_app(
        {"wm_class": "dev.warp.Warp", "title": "Manjaro Gnome Web App Fix"},
        idx,
    )
    assert entry is not None
    assert entry.exec == ["warp-terminal"]
    assert entry.id == "dev.warp.Warp"


def test_window_to_app_skips_unknown_binary(monkeypatch):
    monkeypatch.setattr("workset.engine.capture.shutil.which", lambda _name: None)
    entry = _window_to_app(
        {
            "wm_class": "TotallyUnknownAppXYZ",
            "title": "Nope",
            "desktop": 0,
        },
        DesktopIndex([]),
    )
    assert entry is None


def test_resolve_exec_from_hint(monkeypatch):
    monkeypatch.setattr(
        "workset.engine.capture._exec_is_runnable",
        lambda cmd: cmd == "/opt/postman/Postman",
    )
    assert resolve_exec_candidate(
        "postman",
        index=DesktopIndex([]),
        hinted_exec=["/opt/postman/Postman"],
    ) == ["/opt/postman/Postman"]
