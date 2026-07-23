"""Capture current desktop state into a profile."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

from workset.backends.base import Backend
from workset.backends.registry import detect_backend
from workset.config.models import AppEntry, WindowMatch, WindowState, WorksetProfile
from workset.engine.desktop_files import DesktopIndex
from workset.engine.running_apps import (
    list_atspi_windows,
    list_running_desktop_windows,
    merge_window_lists,
)

log = logging.getLogger(__name__)


def capture_profile(
    name: str,
    *,
    profile_id: str | None = None,
    backend: Backend | None = None,
) -> WorksetProfile:
    b = backend or detect_backend()
    index = DesktopIndex()
    windows = _collect_windows(b, index)
    if not windows:
        log.warning("No se detectaron ventanas/apps (backend=%s)", b.name)

    apps: list[AppEntry] = []
    skipped = 0
    seen_exec: set[tuple[str, ...]] = set()
    for w in windows:
        entry = _window_to_app(w, index)
        if not entry:
            skipped += 1
            continue
        key = tuple(entry.exec)
        if key in seen_exec:
            continue
        seen_exec.add(key)
        apps.append(entry)

    if skipped:
        log.info("Entradas omitidas en captura: %d", skipped)

    if not apps:
        raise RuntimeError(
            "No se pudieron capturar aplicaciones lanzables. "
            "En GNOME Wayland wmctrl solo ve XWayland; se intentó completar con .desktop "
            "y procesos en ejecución. Abre las apps y vuelve a capturar, o edita el perfil a mano."
        )

    note = f"Capturado con backend {b.name} ({len(apps)} apps)"
    return WorksetProfile(
        id=profile_id,
        name=name,
        description=note,
        apps=apps,
    )


def _collect_windows(backend: Backend, index: DesktopIndex) -> list[dict[str, Any]]:
    backend_wins = backend.list_open_windows() or []
    for w in backend_wins:
        w.setdefault("source", "wmctrl" if "win_id" in w or "id" in w else backend.name)

    # En compositors con listado real (hyprland/sway/i3) no hace falta enriquecer tanto.
    if backend.name in {"hyprland", "sway", "i3"} and len(backend_wins) >= 1:
        return backend_wins

    desktop_wins = list_running_desktop_windows(index)
    atspi_wins = list_atspi_windows()
    merged = merge_window_lists(backend_wins, atspi_wins, desktop_wins)
    log.info(
        "Captura ventanas: backend=%d atspi=%d desktop-proc=%d → %d",
        len(backend_wins),
        len(atspi_wins),
        len(desktop_wins),
        len(merged),
    )
    return merged


def resolve_exec_candidate(
    wm_class: str | None,
    *,
    index: DesktopIndex | None = None,
    hinted_exec: list[str] | None = None,
) -> list[str] | None:
    """Resuelve argv lanzable desde hint, .desktop o PATH."""
    if hinted_exec and hinted_exec[0]:
        if _exec_is_runnable(hinted_exec[0]):
            return list(hinted_exec)

    idx = index or DesktopIndex()
    desktop = idx.by_wm_class(wm_class)
    if desktop and _exec_is_runnable(desktop.exec_argv[0]):
        return list(desktop.exec_argv)

    if not wm_class or not str(wm_class).strip():
        return None

    raw = str(wm_class).strip()
    candidates = [
        raw,
        raw.lower(),
        raw.replace(" ", "-").lower(),
        raw.replace("_", "-").lower(),
    ]
    if "." in raw:
        candidates.append(raw.rsplit(".", 1)[-1].lower())

    seen: set[str] = set()
    for name in candidates:
        if not name or name in seen:
            continue
        seen.add(name)
        by_exe = idx.by_executable(name)
        if by_exe and _exec_is_runnable(by_exe.exec_argv[0]):
            return list(by_exe.exec_argv)
        if shutil.which(name):
            return [name]
    return None


def _exec_is_runnable(cmd: str) -> bool:
    if not cmd:
        return False
    path = Path(cmd)
    if path.is_file() and os_access_executable(path):
        return True
    return shutil.which(cmd) is not None


def os_access_executable(path: Path) -> bool:
    import os

    return os.access(path, os.X_OK)


def _window_to_app(window: dict[str, Any], index: DesktopIndex) -> AppEntry | None:
    wm_class = (
        window.get("class")
        or window.get("wm_class")
        or window.get("app_id")
        or window.get("initialClass")
        or window.get("desktop_id")
    )
    title = window.get("title") or window.get("name") or ""
    hinted = window.get("exec")
    if isinstance(hinted, str):
        hinted = [hinted]

    if not wm_class and not title and not hinted:
        return None

    exec_cmd = resolve_exec_candidate(
        str(wm_class) if wm_class else None,
        index=index,
        hinted_exec=list(hinted) if isinstance(hinted, list) else None,
    )
    if not exec_cmd:
        log.debug(
            "Omitiendo ventana title=%r class=%r: sin exec resoluble",
            title,
            wm_class,
        )
        return None

    # gapplication launch … suele ser ruido de sesión, no un workset útil
    if exec_cmd[0] in {"gapplication", "flatpak"}:
        return None

    desktop = index.by_wm_class(str(wm_class) if wm_class else None)
    match_class = (desktop.wm_class if desktop else None) or (str(wm_class) if wm_class else None)
    match = WindowMatch(
        wm_class=match_class,
        app_id=str(window.get("app_id") or "") or None,
        title=None,  # título de sesión es demasiado frágil para apply
    )

    workspace = window.get("workspace")
    if isinstance(workspace, dict):
        workspace = workspace.get("id")

    state_str = window.get("state") or _infer_state(window)
    try:
        state = WindowState(state_str)
    except ValueError:
        state = WindowState.NORMAL

    app_id = (
        (desktop.id if desktop else None)
        or (str(wm_class).lower().replace(" ", "-") if wm_class else None)
        or Path(exec_cmd[0]).stem
    )

    return AppEntry(
        id=app_id,
        exec=exec_cmd,
        monitor=window.get("monitor") or window.get("output"),
        workspace=workspace if workspace is not None else window.get("desktop"),
        state=state,
        match=match,
    )


def _infer_state(window: dict[str, Any]) -> str:
    if window.get("fullscreen") or window.get("fullscreen_mode"):
        return "fullscreen"
    if window.get("maximized"):
        return "maximized"
    if window.get("minimized"):
        return "minimized"
    return "normal"
