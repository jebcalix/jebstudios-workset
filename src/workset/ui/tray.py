"""Bandeja del sistema (StatusNotifier / AppIndicator) en proceso Gtk3 separado.

GTK4 y AyatanaAppIndicator3/AppIndicator3 (Gtk3) no pueden coexistir en el mismo
proceso; por eso el tray vive en `workset-tray`.

Compatible con hosts multi-DE en Arch:
Plasma, GNOME (+ extensión), Waybar (Hyprland/Sway), XFCE/MATE/Cinnamon/Budgie,
LXQt, i3+snixembed, etc.
"""

from __future__ import annotations

import logging
import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

TRAY_AUTOSTART_ID = "jebstudios-workset-tray.desktop"
APP_ICON_NAME = "io.jebstudios.Workset"


def main(argv: list[str] | None = None) -> int:
    _ = argv
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        return _run_tray()
    except Exception as exc:
        log.error("No se pudo iniciar el tray: %s", exc)
        return 1


def _run_tray() -> int:
    from workset.config.loader import list_profiles, load_global_config
    from workset.desktop_env import detect_desktop_env, tray_support
    from workset.ui.icons import bundled_icon_png, ensure_user_icon_theme

    support = tray_support()
    if support.available_api is None:
        raise RuntimeError(
            "No hay AppIndicator disponible. Instala: sudo pacman -S libayatana-appindicator"
        )

    ensure_user_icon_theme()
    env = detect_desktop_env()
    log.info(
        "Tray en DE=%s session=%s api=%s watcher=%s",
        env.family,
        env.session or "?",
        support.available_api,
        support.watcher_present,
    )
    if support.hint:
        log.info("%s", support.hint)

    Gtk, Indicator, IndicatorCategory, IndicatorStatus = _load_indicator_api(support.available_api)

    icon_name = APP_ICON_NAME
    icon_path = bundled_icon_png()
    if icon_path.is_file():
        # Absolute path works even before icon cache refresh / across themes.
        icon_name = str(icon_path)

    indicator = Indicator.new(
        "io.jebstudios.Workset.Tray",
        icon_name,
        IndicatorCategory.APPLICATION_STATUS,
    )
    indicator.set_status(IndicatorStatus.ACTIVE)
    indicator.set_title("Workset")

    menu = Gtk.Menu()

    open_item = Gtk.MenuItem(label="Abrir Workset")
    open_item.connect("activate", lambda *_: _open_picker())
    menu.append(open_item)

    apply_default = Gtk.MenuItem(label="Aplicar perfil por defecto")
    apply_default.connect("activate", lambda *_: _apply_default())
    menu.append(apply_default)

    menu.append(Gtk.SeparatorMenuItem())

    profiles_item = Gtk.MenuItem(label="Perfiles")
    profiles_menu = Gtk.Menu()
    profiles_item.set_submenu(profiles_menu)
    menu.append(profiles_item)

    def rebuild_profiles(*_args: Any) -> None:
        for child in list(profiles_menu.get_children()):
            profiles_menu.remove(child)
        profiles = list_profiles()
        if not profiles:
            empty = Gtk.MenuItem(label="(sin perfiles)")
            empty.set_sensitive(False)
            profiles_menu.append(empty)
        else:
            for pid, name in profiles:
                item = Gtk.MenuItem(label=f"{name} ({pid})")
                item.connect("activate", lambda _w, p=pid: _apply_profile(p))
                profiles_menu.append(item)
        profiles_menu.show_all()

    rebuild_profiles()
    menu.connect("show", rebuild_profiles)

    menu.append(Gtk.SeparatorMenuItem())

    quit_item = Gtk.MenuItem(label="Salir del icono")
    quit_item.connect("activate", lambda *_: Gtk.main_quit())
    menu.append(quit_item)

    menu.show_all()
    indicator.set_menu(menu)

    # Secondary/middle click opens the main window on many trays (Waybar, Plasma…).
    if hasattr(indicator, "set_secondary_activate_target"):
        indicator.set_secondary_activate_target(open_item)

    def _on_signal(signum: int, _frame: Any) -> None:
        log.info("Señal %s — cerrando tray", signum)
        Gtk.main_quit()

    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)

    cfg = load_global_config()
    if not cfg.show_tray_icon:
        log.info("show_tray_icon=false; el tray no se mantiene activo")
        return 0

    log.info("Workset tray activo")
    Gtk.main()
    return 0


def _load_indicator_api(kind: str) -> tuple[Any, Any, Any, Any]:
    import gi

    gi.require_version("Gtk", "3.0")
    if kind == "ayatana":
        gi.require_version("AyatanaAppIndicator3", "0.1")
        from gi.repository import AyatanaAppIndicator3 as AppIndicator
        from gi.repository import Gtk
    elif kind == "appindicator3":
        gi.require_version("AppIndicator3", "0.1")
        from gi.repository import AppIndicator3 as AppIndicator
        from gi.repository import Gtk
    else:
        raise RuntimeError(f"API de bandeja desconocida: {kind}")

    return (
        Gtk,
        AppIndicator.Indicator,
        AppIndicator.IndicatorCategory,
        AppIndicator.IndicatorStatus,
    )


def _workset_bin(name: str) -> str:
    here = Path(sys.executable).resolve().parent / name
    if here.is_file() and os.access(here, os.X_OK):
        return str(here)
    found = shutil.which(name)
    return found or name


def _open_picker() -> None:
    subprocess.Popen(
        [_workset_bin("workset-picker")],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _apply_profile(profile_id: str) -> None:
    subprocess.Popen(
        [_workset_bin("workset"), "apply", profile_id],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _apply_default() -> None:
    from workset.config.loader import load_global_config

    cfg = load_global_config()
    if not cfg.default_profile:
        _open_picker()
        return
    _apply_profile(cfg.default_profile)


# --- control helpers (usados desde la GUI GTK4) ---


def tray_autostart_path() -> Path:
    return Path.home() / ".config" / "autostart" / TRAY_AUTOSTART_ID


def write_tray_autostart(*, enabled: bool) -> None:
    """Autostart XDG — funciona en GNOME, Plasma, XFCE, Cinnamon, MATE, Budgie, etc."""
    path = tray_autostart_path()
    if not enabled:
        if path.is_file():
            path.unlink()
        return

    exe = _workset_bin("workset-tray")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "[Desktop Entry]",
                "Type=Application",
                "Name=Workset Tray",
                "Comment=Icono de bandeja de Workset (multi-DE)",
                f"Exec={exe}",
                f"Icon={APP_ICON_NAME}",
                "Terminal=false",
                "Categories=Settings;Utility;",
                "StartupNotify=false",
                "NoDisplay=true",
                # Sin OnlyShowIn: válido en todos los DE con XDG autostart
                "X-GNOME-Autostart-enabled=true",
                "X-KDE-autostart-after=panel",
                "X-MATE-Autostart-enabled=true",
                "",
            ]
        ),
        encoding="utf-8",
    )


def is_tray_running() -> bool:
    try:
        result = subprocess.run(
            ["pgrep", "-f", r"workset[.-]tray|workset\.ui\.tray"],
            capture_output=True,
            text=True,
            check=False,
        )
        pids = [p for p in result.stdout.split() if p.strip()]
        me = str(os.getpid())
        return any(p != me for p in pids)
    except FileNotFoundError:
        return False


def start_tray_process() -> None:
    if is_tray_running():
        return
    from workset.desktop_env import tray_support
    from workset.ui.icons import ensure_user_icon_theme

    support = tray_support()
    if support.available_api is None:
        raise RuntimeError(
            "Falta libayatana-appindicator (o libappindicator). "
            "Paquetes sugeridos: " + ", ".join(support.packages)
        )

    ensure_user_icon_theme()
    subprocess.Popen(
        [_workset_bin("workset-tray")],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def stop_tray_process() -> None:
    subprocess.run(
        ["pkill", "-f", r"workset[.-]tray|workset\.ui\.tray"],
        check=False,
        capture_output=True,
    )


def set_tray_enabled(enabled: bool) -> None:
    write_tray_autostart(enabled=enabled)
    if enabled:
        start_tray_process()
    else:
        stop_tray_process()


if __name__ == "__main__":
    raise SystemExit(main())
