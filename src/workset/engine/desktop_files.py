"""Índice de archivos .desktop para resolver exec / WM_CLASS."""

from __future__ import annotations

import configparser
import logging
import os
import shlex
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

_DESKTOP_DIRS = (
    Path.home() / ".local/share/applications",
    Path("/usr/local/share/applications"),
    Path("/usr/share/applications"),
)


@dataclass(frozen=True)
class DesktopApp:
    id: str  # filename stem
    name: str
    exec_argv: list[str]
    wm_class: str | None
    executable: str  # basename of Exec[0]
    path: Path
    no_display: bool = False


def desktop_search_dirs() -> list[Path]:
    dirs: list[Path] = []
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        dirs.append(Path(xdg) / "applications")
    for d in _DESKTOP_DIRS:
        if d not in dirs:
            dirs.append(d)
    xdg_dirs = os.environ.get("XDG_DATA_DIRS", "")
    for part in xdg_dirs.split(":"):
        if not part:
            continue
        p = Path(part) / "applications"
        if p not in dirs:
            dirs.append(p)
    return dirs


def parse_exec_field(exec_field: str) -> list[str]:
    """Convierte Exec= de .desktop a argv sin field codes (%u, %F, …)."""
    tokens = shlex.split(exec_field, posix=True)
    out: list[str] = []
    for tok in tokens:
        if tok.startswith("%"):
            continue
        out.append(tok)
    return out


def load_desktop_apps(*, include_nodisplay: bool = False) -> list[DesktopApp]:
    apps: list[DesktopApp] = []
    seen_paths: set[Path] = set()
    for directory in desktop_search_dirs():
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.desktop")):
            try:
                resolved = path.resolve()
            except OSError:
                resolved = path
            if resolved in seen_paths:
                continue
            seen_paths.add(resolved)
            app = _parse_desktop_file(path)
            if app is None:
                continue
            if app.no_display and not include_nodisplay:
                continue
            apps.append(app)
    return apps


def _parse_desktop_file(path: Path) -> DesktopApp | None:
    cp = configparser.ConfigParser(interpolation=None)
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        cp.read_string(text)
    except Exception as e:
        log.debug("desktop ilegible %s: %s", path, e)
        return None
    if "Desktop Entry" not in cp:
        return None
    section = cp["Desktop Entry"]
    if section.get("Type", "Application") != "Application":
        return None
    if section.getboolean("Hidden", fallback=False):
        return None
    exec_field = section.get("Exec", "").strip()
    if not exec_field:
        return None
    argv = parse_exec_field(exec_field)
    if not argv:
        return None
    wm_class = section.get("StartupWMClass") or None
    name = section.get("Name") or path.stem
    no_display = section.getboolean("NoDisplay", fallback=False)
    return DesktopApp(
        id=path.stem,
        name=name,
        exec_argv=argv,
        wm_class=wm_class,
        executable=Path(argv[0]).name,
        path=path,
        no_display=no_display,
    )


class DesktopIndex:
    def __init__(self, apps: list[DesktopApp] | None = None) -> None:
        self.apps = apps if apps is not None else load_desktop_apps()
        self._by_wm: dict[str, DesktopApp] = {}
        self._by_exec: dict[str, DesktopApp] = {}
        for app in self.apps:
            if app.wm_class:
                self._by_wm[app.wm_class.casefold()] = app
            self._by_exec[app.executable.casefold()] = app
            # también indexar stem del desktop id (dev.warp.Warp)
            self._by_wm[app.id.casefold()] = app

    def by_wm_class(self, wm_class: str | None) -> DesktopApp | None:
        if not wm_class:
            return None
        key = wm_class.casefold()
        if key in self._by_wm:
            return self._by_wm[key]
        # Solo match parcial si la clave es suficientemente específica
        if len(key) < 5 and "." not in key:
            return None
        for wm, app in self._by_wm.items():
            if len(wm) < 5 and "." not in wm:
                continue
            if wm == key:
                return app
            if "." in key and (wm.endswith("." + key) or key.endswith("." + wm)):
                return app
            if len(key) >= 8 and (wm.startswith(key) or key.startswith(wm)):
                return app
        return None

    def by_executable(self, name: str | None) -> DesktopApp | None:
        if not name:
            return None
        return self._by_exec.get(Path(name).name.casefold())
