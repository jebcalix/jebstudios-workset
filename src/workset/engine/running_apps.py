"""Descubrimiento de apps GUI en ejecución (complementa wmctrl en Wayland)."""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Any

from workset.engine.desktop_files import DesktopApp, DesktopIndex

log = logging.getLogger(__name__)

_HELPER_MARKERS = (
    "--type=",
    "crashpad",
    "zygote",
    "nacl_helper",
    "--monitor-self",
)

_SKIP_BASENAMES = {
    "bash",
    "zsh",
    "fish",
    "sh",
    "dash",
    "cat",
    "curl",
    "bwrap",
    "sandbox",
    "chrome_crashpad_handler",
    "python",
    "python3",
    "workset-picker",
    "workset",
    "gnome-shell",
    "Xwayland",
    "pipewire",
    "wireplumber",
    "dbus-daemon",
    "systemd",
}

# Procesos de sesión GNOME que suelen estar vivos sin ser un workset
_BACKGROUND_DESKTOP_IDS = {
    "org.gnome.Software",
    "org.gnome.Calendar",
    "evolution-alarm-notify",
    "xdg-desktop-portal-gnome",
    "xdg-desktop-portal-gtk",
}


def list_running_desktop_windows(index: DesktopIndex | None = None) -> list[dict[str, Any]]:
    """Apps .desktop cuyo proceso principal parece estar corriendo."""
    idx = index or DesktopIndex()
    running = _scan_running_processes()
    windows: list[dict[str, Any]] = []
    seen: set[str] = set()

    for app in idx.apps:
        if app.no_display:
            continue
        if app.id in _BACKGROUND_DESKTOP_IDS:
            continue
        # WebApps de navegador (ICE / Chrome) ensucian el perfil; el browser ya se captura
        aid = app.id.casefold()
        if aid.startswith("webapp-") or aid.startswith("chrome-"):
            continue
        if app.wm_class and app.wm_class.casefold().startswith("webapp-"):
            continue
        if not _desktop_is_running(app, running):
            continue
        key = (app.wm_class or app.id).casefold()
        if key in seen:
            continue
        seen.add(key)
        windows.append(
            {
                "wm_class": app.wm_class or app.id,
                "class": app.wm_class or app.id,
                "app_id": app.wm_class or app.id,
                "title": app.name,
                "name": app.name,
                "desktop_id": app.id,
                "exec": list(app.exec_argv),
                "source": "desktop-proc",
            }
        )
    log.info("Apps .desktop en ejecución detectadas: %d", len(windows))
    return windows


def list_atspi_windows() -> list[dict[str, Any]]:
    """Ventanas expuestas por AT-SPI (opcional; muchas apps Electron no aparecen)."""
    try:
        import gi

        gi.require_version("Atspi", "2.0")
        from gi.repository import Atspi
    except Exception as e:
        log.debug("AT-SPI no disponible: %s", e)
        return []

    try:
        Atspi.init()
        desktop = Atspi.get_desktop(0)
    except Exception as e:
        log.debug("AT-SPI init falló: %s", e)
        return []

    skip = {
        "gnome-shell",
        "ibus-extension-gtk3",
        "evolution-alarm-notify",
        "xdg-desktop-portal-gtk",
        "xdg-desktop-portal-gnome",
        "mutter-x11-frames",
        "workset-picker",
        "gjs",
        "at-spi2-registryd",
    }
    out: list[dict[str, Any]] = []
    try:
        n = desktop.get_child_count()
    except Exception:
        return []

    for i in range(n):
        try:
            app = desktop.get_child_at_index(i)
        except Exception:
            continue
        if app is None:
            continue
        name = (app.get_name() or "").strip()
        if not name or name.casefold() in skip:
            continue
        title = name
        try:
            for j in range(min(app.get_child_count(), 8)):
                child = app.get_child_at_index(j)
                if child is None:
                    continue
                role = (child.get_role_name() or "").lower()
                if role in {"frame", "window", "dialog"}:
                    t = (child.get_name() or "").strip()
                    if t:
                        title = t
                        break
        except Exception:
            pass
        out.append(
            {
                "wm_class": name,
                "class": name,
                "app_id": name,
                "title": title,
                "name": title,
                "source": "atspi",
            }
        )
    return out


def merge_window_lists(*lists: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fusiona fuentes; prioridad: wmctrl > atspi > desktop-proc."""
    priority = {"wmctrl": 0, "atspi": 1, "desktop-proc": 2}
    best: dict[str, tuple[int, dict[str, Any]]] = {}
    for lst in lists:
        for win in lst:
            key = _window_key(win)
            if not key:
                continue
            src = str(win.get("source") or "")
            prio = priority.get(src, 9)
            prev = best.get(key)
            if prev is None or prio < prev[0]:
                merged = dict(win)
                if prev and "exec" in prev[1] and "exec" not in merged:
                    merged["exec"] = prev[1]["exec"]
                best[key] = (prio, merged)
            elif prev is not None and "exec" not in prev[1] and win.get("exec"):
                combined = dict(prev[1])
                combined["exec"] = win["exec"]
                best[key] = (prev[0], combined)
    return [item for _, item in sorted(best.values(), key=lambda t: t[0])]


def _window_key(win: dict[str, Any]) -> str:
    for field in ("wm_class", "class", "app_id", "desktop_id"):
        val = win.get(field)
        if val:
            return str(val).casefold()
    title = win.get("title") or win.get("name")
    return str(title).casefold() if title else ""


_GENERIC_BIN_DIRS = {
    "/bin",
    "/sbin",
    "/usr/bin",
    "/usr/sbin",
    "/usr/local/bin",
    "/usr/local/sbin",
    "/lib",
    "/lib64",
    "/usr/lib",
    "/usr/lib64",
}


def _desktop_is_running(app: DesktopApp, running: dict[str, set[str]]) -> bool:
    bins = running["bins"]
    paths = running["paths"]
    cmdlines = running["cmdlines"]

    # Ignorar wrappers genéricos poco útiles para un workset
    if app.executable.casefold() in {"electron", "gapplication", "java", "python", "python3"}:
        resolved = _resolve_exec_path(app.exec_argv[0])
        if resolved and resolved in paths:
            return True
        for arg in app.exec_argv[1:]:
            arg_l = arg.casefold()
            if len(arg_l) >= 5 and any(arg_l in cl for cl in cmdlines):
                return True
        return False

    exe = app.executable.casefold()
    if exe in bins:
        return True

    resolved = _resolve_exec_path(app.exec_argv[0])
    if resolved and resolved in paths:
        return True
    if resolved:
        parent = str(Path(resolved).parent).casefold()
        # Solo directorios de app (/opt/foo, /usr/share/cursor), nunca /usr/bin
        if parent not in _GENERIC_BIN_DIRS and parent.count("/") >= 2:
            if any(parent in cl for cl in cmdlines) or any(parent in p for p in paths):
                return True

    return False


def _resolve_exec_path(cmd: str) -> str | None:
    path = Path(cmd)
    if path.is_file():
        try:
            return str(path.resolve()).casefold()
        except OSError:
            return str(path).casefold()
    which = shutil.which(cmd)
    if not which:
        return None
    try:
        return str(Path(which).resolve()).casefold()
    except OSError:
        return which.casefold()


def _normalize_exe(path: str) -> str:
    # Linux añade " (deleted)" si el binario se actualizó tras el start
    if path.endswith(" (deleted)"):
        path = path[: -len(" (deleted)")]
    return path.casefold()


def _scan_running_processes() -> dict[str, set[str]]:
    bins: set[str] = set()
    paths: set[str] = set()
    cmdlines: set[str] = set()
    proc = Path("/proc")
    if not proc.is_dir():
        return {"bins": bins, "paths": paths, "cmdlines": cmdlines}

    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            environ = (entry / "environ").read_bytes()
            raw = (entry / "cmdline").read_bytes()
        except (PermissionError, ProcessLookupError, FileNotFoundError, OSError):
            continue
        if not raw:
            continue

        has_disp = b"WAYLAND_DISPLAY=" in environ or b"DISPLAY=" in environ
        # Chromium/Electron a menudo no heredan DISPLAY en el proceso principal
        looks_packaged = b"/opt/" in raw or b"/usr/share/" in raw or b"/.local/" in raw
        if not has_disp and not looks_packaged:
            continue

        parts = [p.decode("utf-8", "replace") for p in raw.split(b"\0") if p]
        if not parts:
            continue
        joined = " ".join(parts)
        if any(m in joined for m in _HELPER_MARKERS):
            continue
        base = Path(parts[0]).name
        if base in _SKIP_BASENAMES or base.startswith("gsd-"):
            cmdlines.add(joined.casefold())
            try:
                paths.add(_normalize_exe(os.readlink(entry / "exe")))
            except OSError:
                pass
            for part in parts[1:6]:
                if "/" in part:
                    cmdlines.add(part.casefold())
            continue

        bins.add(base.casefold())
        cmdlines.add(joined.casefold())
        for part in parts[:8]:
            if "/" in part:
                cmdlines.add(part.casefold())
            # basename de argv0 puede ser "vivaldi-bin"
            name = Path(part).name.casefold()
            if len(name) >= 3:
                bins.add(name)

        try:
            exe = _normalize_exe(os.readlink(entry / "exe"))
            paths.add(exe)
            bins.add(Path(exe).name.casefold())
        except OSError:
            pass

    return {"bins": bins, "paths": paths, "cmdlines": cmdlines}
