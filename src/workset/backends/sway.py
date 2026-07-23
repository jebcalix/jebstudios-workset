"""Sway backend via swaymsg."""

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


class SwayBackend(Backend):
    name = "sway"

    def is_available(self) -> bool:
        return bool(os.environ.get("SWAYSOCK")) and bool(shutil.which("swaymsg"))

    def _tree(self) -> dict[str, Any]:
        return run_json(["swaymsg", "-t", "get_tree"]) or {}

    def _walk(self, node: dict[str, Any]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        if node.get("type") == "con" and node.get("window"):
            result.append(node)
        for child in node.get("nodes", []) + node.get("floating_nodes", []):
            result.extend(self._walk(child))
        return result

    def _clients(self) -> list[dict[str, Any]]:
        clients = self._walk(self._tree())
        normalized = []
        for c in clients:
            props = c.get("window_properties") or {}
            normalized.append(
                {
                    "con_id": c["id"],
                    "id": c["id"],
                    "app_id": c.get("app_id") or props.get("class"),
                    "class": props.get("class"),
                    "wm_class": props.get("class"),
                    "title": c.get("name") or props.get("title"),
                    "name": c.get("name"),
                    "workspace": _sway_workspace(c),
                    "output": _sway_output(c),
                    "fullscreen_mode": c.get("fullscreen_mode", 0),
                }
            )
        return normalized

    def list_monitors(self) -> list[MonitorInfo]:
        outputs = run_json(["swaymsg", "-t", "get_outputs"])
        if not isinstance(outputs, list):
            return []
        return [
            MonitorInfo(
                id=str(o.get("name")),
                name=str(o.get("name")),
                is_primary=bool(o.get("focused")),
                x=int(o.get("rect", {}).get("x", 0)),
                y=int(o.get("rect", {}).get("y", 0)),
            )
            for o in outputs
            if o.get("active")
        ]

    def list_open_windows(self) -> list[dict]:
        return self._clients()

    def wait_for_window(self, app: AppEntry) -> WindowHandle | None:
        return wait_for_window(
            app,
            self._clients,
            self._make_handle,
            match_kwargs={"app_id_keys": ("app_id", "class")},
        )

    def move_to_monitor(self, handle: WindowHandle, monitor_ref: str | None) -> None:
        if not monitor_ref:
            return
        mon = resolve_monitor_ref(monitor_ref, self.list_monitors())
        cid = handle.raw["con_id"]
        run_cmd(["swaymsg", f"[con_id={cid}]", "move", "container", "to", "output", mon])

    def move_to_workspace(self, handle: WindowHandle, workspace: int | str | None) -> None:
        if workspace is None:
            return
        cid = handle.raw["con_id"]
        run_cmd(["swaymsg", f"[con_id={cid}]", "move", "container", "to", "workspace", "number", str(workspace)])

    def set_state(self, handle: WindowHandle, state: WindowState) -> None:
        cid = handle.raw["con_id"]
        prefix = f"[con_id={cid}]"
        if state == WindowState.FULLSCREEN:
            run_cmd(["swaymsg", prefix, "fullscreen", "enable"])
        elif state == WindowState.MAXIMIZED:
            run_cmd(["swaymsg", prefix, "fullscreen", "enable", "global"])
        elif state == WindowState.MINIMIZED:
            run_cmd(["swaymsg", prefix, "move", "scratchpad"])
        elif state == WindowState.NORMAL:
            run_cmd(["swaymsg", prefix, "fullscreen", "disable"])

    def _make_handle(self, client: dict[str, Any]) -> WindowHandle:
        return WindowHandle(backend=self.name, raw={"con_id": client["con_id"], "client": client})


def _sway_workspace(node: dict[str, Any]) -> int | str | None:
    # BFS up not available; workspace from get_tree context omitted — use 1 default
    return 1


def _sway_output(node: dict[str, Any]) -> str | None:
    return None
