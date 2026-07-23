"""X11 generic backend via wmctrl."""

from __future__ import annotations

import logging
import os
import shutil
from typing import Any

from workset.backends._subprocess import run_cmd
from workset.backends.base import Backend, MonitorInfo
from workset.config.models import AppEntry, WindowHandle, WindowState
from workset.engine.window_waiter import wait_for_window

log = logging.getLogger(__name__)


class X11Backend(Backend):
    name = "x11"

    def is_available(self) -> bool:
        if os.environ.get("XDG_SESSION_TYPE", "").lower() != "x11":
            return False
        return bool(shutil.which("wmctrl"))

    def _clients(self) -> list[dict[str, Any]]:
        out = run_cmd(["wmctrl", "-l", "-x", "-p"])
        from workset.backends.wmctrl_parse import parse_wmctrl_output

        return parse_wmctrl_output(out)

    def list_monitors(self) -> list[MonitorInfo]:
        # wmctrl no lista monitores; usar xrandr si está disponible
        if not shutil.which("xrandr"):
            return [MonitorInfo(id="0", name="primary", is_primary=True)]
        out = run_cmd(["xrandr", "--query"])
        monitors: list[MonitorInfo] = []
        x = 0
        for line in out.splitlines():
            if " connected" in line:
                parts = line.split()
                name = parts[0]
                primary = "primary" in line
                monitors.append(MonitorInfo(id=name, name=name, is_primary=primary, x=x))
                x += 1920  # aproximado si no parseamos geometry
        return monitors or [MonitorInfo(id="0", name="primary", is_primary=True)]

    def list_open_windows(self) -> list[dict]:
        return self._clients()

    def wait_for_window(self, app: AppEntry) -> WindowHandle | None:
        return wait_for_window(app, self._clients, self._make_handle)

    def move_to_monitor(self, handle: WindowHandle, monitor_ref: str | None) -> None:
        if not monitor_ref:
            return
        # wmctrl no mueve entre monitores de forma fiable; usar coordenadas aproximadas
        win_id = handle.raw["win_id"]
        monitors = self.list_monitors()
        target = monitor_ref
        for m in monitors:
            if m.name == monitor_ref or (monitor_ref == "primary" and m.is_primary):
                target = m.name
                break
        x = next((m.x for m in monitors if m.name == target), 0)
        run_cmd(["wmctrl", "-i", "-r", win_id, "-e", f"0,{x},0,-1,-1"])
        log.debug("x11: movida ventana %s hacia monitor %s (x=%d)", win_id, target, x)

    def move_to_workspace(self, handle: WindowHandle, workspace: int | str | None) -> None:
        if workspace is None:
            return
        win_id = handle.raw["win_id"]
        desk = str(workspace)
        run_cmd(["wmctrl", "-i", "-r", win_id, "-t", desk])

    def set_state(self, handle: WindowHandle, state: WindowState) -> None:
        win_id = handle.raw["win_id"]
        if state == WindowState.MAXIMIZED:
            run_cmd(["wmctrl", "-i", "-r", win_id, "-b", "add,maximized_vert,maximized_horz"])
        elif state == WindowState.FULLSCREEN:
            run_cmd(["wmctrl", "-i", "-r", win_id, "-b", "add,fullscreen"])
        elif state == WindowState.MINIMIZED:
            run_cmd(["wmctrl", "-i", "-r", win_id, "-b", "add,hidden"])
        elif state == WindowState.NORMAL:
            run_cmd(["wmctrl", "-i", "-r", win_id, "-b", "remove,fullscreen,maximized_vert,maximized_horz,hidden"])

    def _make_handle(self, client: dict[str, Any]) -> WindowHandle:
        return WindowHandle(backend=self.name, raw={"win_id": client["win_id"], "client": client})
