"""GNOME backend — wmctrl for XWayland, limited native Wayland placement."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from typing import Any

from workset.backends.base import Backend, MonitorInfo
from workset.config.models import AppEntry, WindowHandle, WindowState
from workset.engine.window_waiter import wait_for_window

log = logging.getLogger(__name__)


class GnomeBackend(Backend):
    name = "gnome"

    def is_available(self) -> bool:
        desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").upper()
        return "GNOME" in desktop

    @property
    def launch_only(self) -> bool:
        # wmctrl only sees XWayland clients; on Wayland native apps never match
        # and wait_for_window times out. Skip placement entirely on Wayland.
        if os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland":
            return True
        return not shutil.which("wmctrl")

    def _clients(self) -> list[dict[str, Any]]:
        if not shutil.which("wmctrl"):
            return []
        result = subprocess.run(
            ["wmctrl", "-l", "-x", "-p"],
            capture_output=True,
            text=True,
            check=False,
        )
        from workset.backends.wmctrl_parse import parse_wmctrl_output

        return parse_wmctrl_output(result.stdout)

    def list_monitors(self) -> list[MonitorInfo]:
        if shutil.which("gnome-randr"):
            try:
                out = subprocess.run(
                    ["gnome-randr", "list"],
                    capture_output=True,
                    text=True,
                    check=False,
                ).stdout
                names = [ln.strip() for ln in out.splitlines() if ln.strip()]
                return [
                    MonitorInfo(id=n, name=n, is_primary=i == 0)
                    for i, n in enumerate(names)
                ]
            except Exception:
                pass
        return [MonitorInfo(id="primary", name="primary", is_primary=True)]

    def list_open_windows(self) -> list[dict]:
        return self._clients()

    def wait_for_window(self, app: AppEntry) -> WindowHandle | None:
        if self.launch_only:
            log.debug("gnome: wmctrl no disponible, skip wait")
            return None
        return wait_for_window(app, self._clients, self._make_handle)

    def move_to_monitor(self, handle: WindowHandle, monitor_ref: str | None) -> None:
        if not monitor_ref or not shutil.which("wmctrl"):
            log.warning("gnome: placement de monitor limitado en Wayland nativo")
            return
        win_id = handle.raw["win_id"]
        subprocess.run(["wmctrl", "-i", "-r", win_id, "-e", "0,0,0,-1,-1"], check=False)

    def move_to_workspace(self, handle: WindowHandle, workspace: int | str | None) -> None:
        if workspace is None:
            return
        # GNOME workspaces: usar gsettings + dbus es frágil; intentar wmctrl desktop
        if shutil.which("wmctrl"):
            win_id = handle.raw["win_id"]
            subprocess.run(["wmctrl", "-i", "-r", win_id, "-t", str(workspace)], check=False)
        else:
            self._switch_workspace_gnome(int(workspace) if str(workspace).isdigit() else 1)

    def set_state(self, handle: WindowHandle, state: WindowState) -> None:
        if not shutil.which("wmctrl"):
            log.warning("gnome: no se puede aplicar estado %s sin wmctrl/XWayland", state.value)
            return
        win_id = handle.raw["win_id"]
        mapping = {
            WindowState.MAXIMIZED: ("add", "maximized_vert,maximized_horz"),
            WindowState.FULLSCREEN: ("add", "fullscreen"),
            WindowState.MINIMIZED: ("add", "hidden"),
            WindowState.NORMAL: ("remove", "fullscreen,maximized_vert,maximized_horz,hidden"),
        }
        action, prop = mapping[state]
        subprocess.run(["wmctrl", "-i", "-r", win_id, "-b", f"{action},{prop}"], check=False)

    def _switch_workspace_gnome(self, workspace: int) -> None:
        try:
            subprocess.run(
                [
                    "gdbus",
                    "call",
                    "--session",
                    "--dest",
                    "org.gnome.Shell",
                    "--object-path",
                    "/org/gnome/Shell",
                    "--method",
                    "org.gnome.Shell.Eval",
                    f"global.workspace_manager.get_workspace_by_index({workspace - 1}).activate(global.get_current_time());",
                ],
                capture_output=True,
                check=False,
            )
        except Exception as e:
            log.debug("gnome workspace switch failed: %s", e)

    def _make_handle(self, client: dict[str, Any]) -> WindowHandle:
        return WindowHandle(backend=self.name, raw={"win_id": client["win_id"], "client": client})
