"""Backend auto-detection."""

from __future__ import annotations

import logging
import os
import shutil

from workset.backends.base import Backend
from workset.backends.generic import GenericBackend
from workset.backends.gnome import GnomeBackend
from workset.backends.hyprland import HyprlandBackend
from workset.backends.i3 import I3Backend
from workset.backends.kde import KdeBackend
from workset.backends.sway import SwayBackend
from workset.backends.x11 import X11Backend

log = logging.getLogger(__name__)

_CANDIDATES: list[type[Backend]] = [
    HyprlandBackend,
    SwayBackend,
    I3Backend,
    KdeBackend,
    GnomeBackend,
    X11Backend,
]


def detect_backend() -> Backend:
    for cls in _CANDIDATES:
        backend = cls()
        if backend.is_available():
            log.info("Backend detectado: %s", backend.name)
            return backend

    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "")
    session = os.environ.get("XDG_SESSION_TYPE", "")
    log.info(
        "Usando backend generic (DE=%s, session=%s, wmctrl=%s)",
        desktop,
        session,
        bool(shutil.which("wmctrl")),
    )
    return GenericBackend()


def doctor_info() -> dict[str, str | bool]:
    from workset.desktop_env import detect_desktop_env, tray_support

    b = detect_backend()
    env = detect_desktop_env()
    tray = tray_support()
    return {
        "backend": b.name,
        "launch_only": b.launch_only,
        "hyprland": bool(os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")),
        "sway": bool(os.environ.get("SWAYSOCK")),
        "i3": bool(os.environ.get("I3SOCK")),
        "desktop": os.environ.get("XDG_CURRENT_DESKTOP", ""),
        "desktop_family": env.family,
        "session": os.environ.get("XDG_SESSION_TYPE", ""),
        "wmctrl": bool(shutil.which("wmctrl")),
        "hyprctl": bool(shutil.which("hyprctl")),
        "swaymsg": bool(shutil.which("swaymsg")),
        "i3-msg": bool(shutil.which("i3-msg")),
        "qdbus": bool(shutil.which("qdbus6") or shutil.which("qdbus")),
        "tray_api": tray.available_api or "",
        "tray_watcher": tray.watcher_present,
        "tray_ready": tray.ready,
        "tray_hint": tray.hint,
    }
