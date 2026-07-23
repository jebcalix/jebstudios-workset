"""Hyprland backend via hyprctl."""

from __future__ import annotations

import logging
import os
import shutil
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
        run_cmd(["hyprctl", "dispatch", "movewindow", f"mon:{mon},address:{addr}"])

    def move_to_workspace(self, handle: WindowHandle, workspace: int | str | None) -> None:
        if workspace is None:
            return
        addr = handle.raw["address"]
        ws = str(workspace)
        run_cmd(["hyprctl", "dispatch", "movetoworkspace", f"{ws},address:{addr}"])

    def set_state(self, handle: WindowHandle, state: WindowState) -> None:
        addr = handle.raw["address"]
        if state == WindowState.FULLSCREEN:
            run_cmd(["hyprctl", "dispatch", "fullscreen", f"1,address:{addr}"])
        elif state == WindowState.MAXIMIZED:
            run_cmd(["hyprctl", "dispatch", "maximize", f"address:{addr}"])
        elif state == WindowState.MINIMIZED:
            run_cmd(["hyprctl", "dispatch", "minimize", f"address:{addr}"])
        elif state == WindowState.NORMAL:
            run_cmd(["hyprctl", "dispatch", "fullscreen", f"0,address:{addr}"])

    def _make_handle(self, client: dict[str, Any]) -> WindowHandle:
        return WindowHandle(backend=self.name, raw={"address": client["address"], "client": client})

    def client_to_app_entry(self, client: dict[str, Any]) -> dict[str, Any]:
        wm_class = client.get("class") or client.get("initialClass") or "unknown"
        return {
            "id": wm_class.lower().replace(" ", "-"),
            "exec": [wm_class],
            "monitor": client.get("monitor"),
            "workspace": client.get("workspace", {}).get("id") if isinstance(client.get("workspace"), dict) else client.get("workspace"),
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
