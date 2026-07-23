"""Hyprland backend via hyprctl.

Hyprland >= 0.55 uses Lua dispatchers (`hl.dsp.*`). Legacy string dispatchers
(`movetoworkspace`, etc.) fail silently (hyprctl still exits 0), which leaves
windows on the focused workspace — typically 1 on Omarchy.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
from functools import lru_cache
from typing import Any

from workset.backends._subprocess import run_cmd, run_json
from workset.backends.base import Backend, MonitorInfo
from workset.config.models import AppEntry, WindowHandle, WindowState
from workset.engine.monitor_resolver import resolve_monitor_ref
from workset.engine.window_waiter import wait_for_window

log = logging.getLogger(__name__)


class HyprlandBackend(Backend):
    name = "hyprland"

    def is_available(self) -> bool:
        return bool(os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")) and bool(shutil.which("hyprctl"))

    def _clients(self) -> list[dict[str, Any]]:
        data = run_json(["hyprctl", "clients", "-j"])
        return data if isinstance(data, list) else []

    def _monitors_raw(self) -> list[dict[str, Any]]:
        data = run_json(["hyprctl", "monitors", "-j"])
        return data if isinstance(data, list) else []

    def list_monitors(self) -> list[MonitorInfo]:
        return [
            MonitorInfo(
                id=str(m.get("id", m["name"])),
                name=str(m["name"]),
                is_primary=bool(m.get("focused")),
                x=int(m.get("x", 0)),
                y=int(m.get("y", 0)),
                description=str(m.get("description", "")) or None,
            )
            for m in self._monitors_raw()
        ]

    def list_open_windows(self) -> list[dict]:
        return self._clients()

    def wait_for_window(self, app: AppEntry) -> WindowHandle | None:
        return wait_for_window(
            app,
            self._clients,
            self._make_handle,
            match_kwargs={"class_keys": ("class", "initialClass"), "title_keys": ("title", "initialTitle")},
        )

    def move_to_monitor(self, handle: WindowHandle, monitor_ref: str | None) -> None:
        if not monitor_ref:
            return
        mon = resolve_monitor_ref(monitor_ref, self.list_monitors())
        addr = handle.raw["address"]
        if _uses_lua_dispatch():
            _dispatch_lua(
                f'hl.dsp.window.move({{ monitor = "{_escape_lua(mon)}", '
                f'window = "address:{addr}", follow = false }})'
            )
        else:
            _dispatch_legacy(["hyprctl", "dispatch", "movewindow", f"mon:{mon},address:{addr}"])

    def move_to_workspace(self, handle: WindowHandle, workspace: int | str | None) -> None:
        if workspace is None:
            return
        addr = handle.raw["address"]
        if _uses_lua_dispatch():
            ws = _lua_workspace_literal(workspace)
            _dispatch_lua(
                f"hl.dsp.window.move({{ workspace = {ws}, "
                f'window = "address:{addr}", follow = false }})'
            )
        else:
            _dispatch_legacy(
                ["hyprctl", "dispatch", "movetoworkspacesilent", f"{workspace},address:{addr}"]
            )

    def set_state(self, handle: WindowHandle, state: WindowState) -> None:
        addr = handle.raw["address"]
        if _uses_lua_dispatch():
            if state == WindowState.FULLSCREEN:
                _dispatch_lua(
                    f'hl.dsp.window.fullscreen({{ mode = "fullscreen", '
                    f'window = "address:{addr}" }})'
                )
            elif state == WindowState.MAXIMIZED:
                _dispatch_lua(
                    f'hl.dsp.window.fullscreen({{ mode = "maximized", '
                    f'window = "address:{addr}" }})'
                )
            elif state == WindowState.MINIMIZED:
                # No first-class minimize in Lua API; map to scratchpad.
                _dispatch_lua(
                    f'hl.dsp.window.move({{ workspace = "special:scratchpad", '
                    f'window = "address:{addr}", follow = false }})'
                )
            elif state == WindowState.NORMAL:
                _dispatch_lua(
                    f'hl.dsp.window.fullscreen({{ action = "unset", '
                    f'window = "address:{addr}" }})'
                )
            return

        if state == WindowState.FULLSCREEN:
            _dispatch_legacy(["hyprctl", "dispatch", "fullscreen", f"1,address:{addr}"])
        elif state == WindowState.MAXIMIZED:
            _dispatch_legacy(["hyprctl", "dispatch", "maximize", f"address:{addr}"])
        elif state == WindowState.MINIMIZED:
            _dispatch_legacy(["hyprctl", "dispatch", "movetoworkspacesilent", f"special:scratchpad,address:{addr}"])
        elif state == WindowState.NORMAL:
            _dispatch_legacy(["hyprctl", "dispatch", "fullscreen", f"0,address:{addr}"])

    def _make_handle(self, client: dict[str, Any]) -> WindowHandle:
        return WindowHandle(backend=self.name, raw={"address": client["address"], "client": client})

    def client_to_app_entry(self, client: dict[str, Any]) -> dict[str, Any]:
        wm_class = client.get("class") or client.get("initialClass") or "unknown"
        return {
            "id": wm_class.lower().replace(" ", "-"),
            "exec": [wm_class],
            "monitor": client.get("monitor"),
            "workspace": client.get("workspace", {}).get("id")
            if isinstance(client.get("workspace"), dict)
            else client.get("workspace"),
            "state": _hypr_state(client),
            "match": {"wm_class": wm_class},
        }


def _hypr_state(client: dict[str, Any]) -> str:
    if client.get("fullscreen"):
        return "fullscreen"
    if client.get("maximized"):
        return "maximized"
    if client.get("minimized"):
        return "minimized"
    return "normal"


@lru_cache(maxsize=1)
def _uses_lua_dispatch() -> bool:
    """Hyprland 0.55+ interprets `hyprctl dispatch` as Lua (`hl.dispatch(...)`)."""
    try:
        ver = run_cmd(["hyprctl", "version"])
    except Exception:
        return True
    match = re.search(r"Hyprland\s+(\d+)\.(\d+)", ver)
    if not match:
        return True
    major, minor = int(match.group(1)), int(match.group(2))
    return (major, minor) >= (0, 55)


def _lua_workspace_literal(workspace: int | str) -> str:
    if isinstance(workspace, int) or (isinstance(workspace, str) and workspace.isdigit()):
        return str(int(workspace))
    return f'"{_escape_lua(str(workspace))}"'


def _escape_lua(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _dispatch_lua(expression: str) -> None:
    # Both forms work on 0.55; prefer `dispatch` (matches Omarchy/Waybar fixes).
    out = run_cmd(["hyprctl", "dispatch", expression])
    _raise_if_hyprctl_error(out, expression)


def _dispatch_legacy(cmd: list[str]) -> None:
    out = run_cmd(cmd)
    _raise_if_hyprctl_error(out, " ".join(cmd))


def _raise_if_hyprctl_error(out: str, context: str) -> None:
    """hyprctl often exits 0 even when the Lua/legacy dispatcher fails."""
    text = (out or "").strip()
    if not text:
        return
    lowered = text.lower()
    if lowered == "ok" or lowered.startswith("ok\n"):
        return
    if "error:" in lowered:
        raise RuntimeError(f"hyprctl dispatch falló ({context}):\n{text}")
