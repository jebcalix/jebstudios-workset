"""KDE Plasma backend via qdbus / D-Bus."""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
from typing import Any

from workset.backends.base import Backend, MonitorInfo
from workset.config.models import AppEntry, WindowHandle, WindowState
from workset.engine.monitor_resolver import resolve_monitor_ref
from workset.engine.window_waiter import wait_for_window

log = logging.getLogger(__name__)


class KdeBackend(Backend):
    name = "kde"

    def is_available(self) -> bool:
        desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").upper()
        return "KDE" in desktop and bool(shutil.which("wmctrl") or self._qdbus_bin())

    def _qdbus_bin(self) -> str | None:
        return shutil.which("qdbus6") or shutil.which("qdbus")

    def _qdbus(self, *args: str) -> str:
        cmd = [self._qdbus_bin() or "qdbus6", *args]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())
        return result.stdout.strip()

    def _clients(self) -> list[dict[str, Any]]:
        return self._clients_wmctrl()

    def _clients_wmctrl(self) -> list[dict[str, Any]]:
        if not shutil.which("wmctrl"):
            return []
        result = subprocess.run(
            ["wmctrl", "-l", "-x", "-p"],
            capture_output=True,
            text=True,
            check=False,
        )
        clients = []
        for line in result.stdout.splitlines():
            parts = line.split(None, 4)
            if len(parts) < 5:
                continue
            win_id, desk, _, wm_class, title = parts[0], parts[1], parts[2], parts[3], parts[4]
            cls = wm_class.split(".")[0]
            clients.append(
                {
                    "id": win_id,
                    "win_id": win_id,
                    "wm_class": cls,
                    "class": cls,
                    "title": title,
                    "desktop": int(desk) if desk.lstrip("-").isdigit() else 0,
                }
            )
        return clients

    def list_monitors(self) -> list[MonitorInfo]:
        if not shutil.which("kscreen-doctor"):
            return [MonitorInfo(id="0", name="primary", is_primary=True)]
        try:
            out = subprocess.run(
                ["kscreen-doctor", "-o"],
                capture_output=True,
                text=True,
                check=False,
            ).stdout
            names = re.findall(r"Output: (\S+)", out)
            return [
                MonitorInfo(id=n, name=n, is_primary=i == 0)
                for i, n in enumerate(names)
            ]
        except Exception:
            return [MonitorInfo(id="0", name="primary", is_primary=True)]

    def list_open_windows(self) -> list[dict]:
        return self._clients()

    def wait_for_window(self, app: AppEntry) -> WindowHandle | None:
        return wait_for_window(app, self._clients, self._make_handle)

    def move_to_monitor(self, handle: WindowHandle, monitor_ref: str | None) -> None:
        if not monitor_ref or not shutil.which("wmctrl"):
            return
        mon = resolve_monitor_ref(monitor_ref, self.list_monitors())
        win_id = handle.raw.get("win_id") or handle.raw.get("id")
        if win_id:
            subprocess.run(["wmctrl", "-i", "-r", str(win_id), "-e", "0,0,0,-1,-1"], check=False)
            log.info("kde: movida ventana %s hacia %s (best-effort)", win_id, mon)

    def move_to_workspace(self, handle: WindowHandle, workspace: int | str | None) -> None:
        if workspace is None:
            return
        win_id = handle.raw.get("win_id") or handle.raw.get("id")
        if win_id and shutil.which("wmctrl"):
            subprocess.run(["wmctrl", "-i", "-r", str(win_id), "-t", str(workspace)], check=False)

    def set_state(self, handle: WindowHandle, state: WindowState) -> None:
        win_id = handle.raw.get("win_id") or handle.raw.get("id")
        if not win_id or not shutil.which("wmctrl"):
            return
        flags = {
            WindowState.MAXIMIZED: ("add", "maximized_vert,maximized_horz"),
            WindowState.FULLSCREEN: ("add", "fullscreen"),
            WindowState.MINIMIZED: ("add", "hidden"),
            WindowState.NORMAL: ("remove", "fullscreen,maximized_vert,maximized_horz,hidden"),
        }
        action, prop = flags[state]
        subprocess.run(["wmctrl", "-i", "-r", str(win_id), "-b", f"{action},{prop}"], check=False)

    def _make_handle(self, client: dict[str, Any]) -> WindowHandle:
        return WindowHandle(
            backend=self.name,
            raw={"win_id": client.get("win_id") or client.get("id"), "client": client},
        )
