"""i3 backend via i3-msg."""

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


class I3Backend(Backend):
    name = "i3"

    def is_available(self) -> bool:
        return bool(os.environ.get("I3SOCK")) and bool(shutil.which("i3-msg"))

    def _tree(self) -> dict[str, Any]:
        return run_json(["i3-msg", "-t", "get_tree"]) or {}

    def _walk(self, node: dict[str, Any]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        if node.get("type") == "con" and node.get("window"):
            result.append(node)
        for child in node.get("nodes", []) + node.get("floating_nodes", []):
            result.extend(self._walk(child))
        return result

    def _clients(self) -> list[dict[str, Any]]:
        clients = []
        for c in self._walk(self._tree()):
            props = c.get("window_properties") or {}
            clients.append(
                {
                    "con_id": c["id"],
                    "id": c["id"],
                    "class": props.get("class"),
                    "wm_class": props.get("class"),
                    "title": props.get("title") or c.get("name"),
                    "name": c.get("name"),
                }
            )
        return clients

    def list_monitors(self) -> list[MonitorInfo]:
        outputs = run_json(["i3-msg", "-t", "get_outputs"])
        if not isinstance(outputs, list):
            return []
        active = [o for o in outputs if o.get("active")]
        return [
            MonitorInfo(
                id=str(o.get("name")),
                name=str(o.get("name")),
                is_primary=i == 0,
                x=int(o.get("rect", {}).get("x", 0)),
                y=int(o.get("rect", {}).get("y", 0)),
            )
            for i, o in enumerate(active)
        ]

    def list_open_windows(self) -> list[dict]:
        return self._clients()

    def wait_for_window(self, app: AppEntry) -> WindowHandle | None:
        return wait_for_window(app, self._clients, self._make_handle)

    def move_to_monitor(self, handle: WindowHandle, monitor_ref: str | None) -> None:
        if not monitor_ref:
            return
        mon = resolve_monitor_ref(monitor_ref, self.list_monitors())
        cid = handle.raw["con_id"]
        run_cmd(["i3-msg", f"[con_id={cid}]", "move", "container", "to", "output", mon])

    def move_to_workspace(self, handle: WindowHandle, workspace: int | str | None) -> None:
        if workspace is None:
            return
        cid = handle.raw["con_id"]
        run_cmd(["i3-msg", f"[con_id={cid}]", "move", "container", "to", "workspace", str(workspace)])

    def set_state(self, handle: WindowHandle, state: WindowState) -> None:
        cid = handle.raw["con_id"]
        prefix = f"[con_id={cid}]"
        if state == WindowState.FULLSCREEN:
            run_cmd(["i3-msg", prefix, "fullscreen", "enable"])
        elif state == WindowState.MAXIMIZED:
            run_cmd(["i3-msg", prefix, "floating", "disable"])
        elif state == WindowState.MINIMIZED:
            run_cmd(["i3-msg", prefix, "move", "scratchpad"])
        elif state == WindowState.NORMAL:
            run_cmd(["i3-msg", prefix, "fullscreen", "disable"])

    def _make_handle(self, client: dict[str, Any]) -> WindowHandle:
        return WindowHandle(backend=self.name, raw={"con_id": client["con_id"], "client": client})
