"""Detección de escritorio y requisitos de bandeja multi-DE (Arch/AUR)."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass


@dataclass(frozen=True)
class DesktopEnv:
    """Escritorio actual normalizado."""

    family: str  # hyprland|sway|i3|plasma|gnome|cinnamon|xfce|mate|budgie|lxqt|cosmic|other
    tokens: tuple[str, ...]
    session: str  # wayland|x11|""
    raw_desktop: str


@dataclass(frozen=True)
class TraySupport:
    """Estado del soporte de icono de bandeja en este DE."""

    available_api: str | None  # ayatana|appindicator3|None
    watcher_present: bool
    ready: bool
    hint: str
    packages: tuple[str, ...]


def desktop_tokens(raw: str | None = None) -> tuple[str, ...]:
    value = raw if raw is not None else os.environ.get("XDG_CURRENT_DESKTOP", "")
    parts = [p.strip().upper() for p in value.replace(";", ":").split(":") if p.strip()]
    return tuple(dict.fromkeys(parts))  # unique, preserve order


def detect_desktop_env() -> DesktopEnv:
    tokens = desktop_tokens()
    session = os.environ.get("XDG_SESSION_TYPE", "").lower()
    raw = os.environ.get("XDG_CURRENT_DESKTOP", "")

    if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
        family = "hyprland"
    elif os.environ.get("SWAYSOCK"):
        family = "sway"
    elif os.environ.get("I3SOCK") and "SWAY" not in tokens:
        family = "i3"
    elif {"KDE", "PLASMA"} & set(tokens):
        family = "plasma"
    elif "BUDGIE" in tokens:
        family = "budgie"
    elif "CINNAMON" in tokens or "X-CINNAMON" in tokens:
        family = "cinnamon"
    elif "XFCE" in tokens:
        family = "xfce"
    elif "MATE" in tokens:
        family = "mate"
    elif "LXQT" in tokens:
        family = "lxqt"
    elif "COSMIC" in tokens:
        family = "cosmic"
    elif "GNOME" in tokens:
        family = "gnome"
    elif "UNITY" in tokens:
        family = "unity"
    else:
        family = "other"

    return DesktopEnv(family=family, tokens=tokens, session=session, raw_desktop=raw)


def is_pure_gnome() -> bool:
    """True solo para GNOME Shell, no Budgie/Unity que también listan GNOME."""
    env = detect_desktop_env()
    return env.family == "gnome"


def indicator_api_available() -> str | None:
    """Devuelve qué binding de AppIndicator está disponible."""
    try:
        import gi

        try:
            gi.require_version("AyatanaAppIndicator3", "0.1")
            from gi.repository import AyatanaAppIndicator3  # noqa: F401

            return "ayatana"
        except (ImportError, ValueError):
            pass
        try:
            gi.require_version("AppIndicator3", "0.1")
            from gi.repository import AppIndicator3  # noqa: F401

            return "appindicator3"
        except (ImportError, ValueError):
            pass
    except ImportError:
        return None
    return None


def status_notifier_watcher_present() -> bool:
    """Comprueba si hay un StatusNotifierWatcher (bandeja SNI) en la sesión."""
    try:
        import gi

        gi.require_version("Gio", "2.0")
        from gi.repository import Gio, GLib
    except (ImportError, ValueError):
        return False

    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        return _dbus_name_has_owner(bus, "org.kde.StatusNotifierWatcher") or _dbus_name_has_owner(
            bus, "org.freedesktop.StatusNotifierWatcher"
        )
    except GLib.Error:
        return False


def _dbus_name_has_owner(bus, name: str) -> bool:
    try:
        from gi.repository import Gio, GLib

        variant = bus.call_sync(
            "org.freedesktop.DBus",
            "/org/freedesktop/DBus",
            "org.freedesktop.DBus",
            "NameHasOwner",
            GLib.Variant("(s)", (name,)),
            GLib.VariantType("(b)"),
            Gio.DBusCallFlags.NONE,
            -1,
            None,
        )
        return bool(variant.unpack()[0])
    except Exception:
        return False


def gnome_appindicator_extension_hint() -> str | None:
    """Ruta/paquete de la extensión GNOME si parece instalada."""
    paths = [
        "/usr/share/gnome-shell/extensions/appindicatorsupport@rgcjonas.gmail.com",
        os.path.expanduser(
            "~/.local/share/gnome-shell/extensions/appindicatorsupport@rgcjonas.gmail.com"
        ),
    ]
    if any(os.path.isdir(p) for p in paths):
        return "gnome-shell-extension-appindicator (instalada; activa en Extensiones si no la ves)"
    if shutil.which("gnome-extensions"):
        return "sudo pacman -S gnome-shell-extension-appindicator  # y actívala en Extensiones"
    return None


def tray_support() -> TraySupport:
    """Consejos y estado del tray según el DE actual (Arch repos + AUR)."""
    env = detect_desktop_env()
    api = indicator_api_available()
    watcher = status_notifier_watcher_present()

    packages: list[str] = []
    if api is None:
        packages.append("libayatana-appindicator")
    hint = ""

    if env.family == "gnome":
        packages.append("gnome-shell-extension-appindicator")
        ext = gnome_appindicator_extension_hint()
        if not watcher:
            hint = (
                "GNOME no muestra bandeja SNI sin la extensión AppIndicator. "
                + (ext or "Instala gnome-shell-extension-appindicator y actívala.")
            )
        else:
            hint = "GNOME + AppIndicator detectado."
    elif env.family == "plasma":
        packages.append("plasma-workspace")  # incluye bandeja SNI
        hint = (
            "Plasma soporta StatusNotifier de forma nativa "
            "(bandeja del sistema / System Tray widget)."
        )
    elif env.family in {"hyprland", "sway"}:
        packages.append("waybar")
        hint = (
            "En Hyprland/Sway usa Waybar (módulo tray) u otro host SNI "
            "(p. ej. haskell-gtk-sni-tray)."
            if not watcher
            else "Host StatusNotifier (p. ej. Waybar) detectado."
        )
    elif env.family == "i3":
        packages.extend(["polybar", "snixembed"])
        hint = (
            "i3: usa polybar/xembed o snixembed para proxificar SNI → bandeja clásica."
            if not watcher
            else "Host de bandeja detectado."
        )
    elif env.family in {"xfce", "mate", "cinnamon", "budgie", "lxqt"}:
        # Estos DE suelen traer plugin de bandeja; en X11 a veces hace falta snixembed.
        if env.session == "x11" and not watcher:
            packages.append("snixembed")
            hint = (
                f"{env.family}: activa el plugin de bandeja del panel. "
                "Si solo ves iconos XEmbed, prueba snixembed (SNI → XEmbed)."
            )
        else:
            hint = f"{env.family}: usa el plugin de bandeja del panel (StatusNotifier/AppIndicator)."
    elif env.family == "cosmic":
        hint = (
            "COSMIC: soporte de bandeja en evolución; "
            "si no aparece el icono, usa solo workset-picker."
        )
    else:
        packages.append("libayatana-appindicator")
        if env.session == "x11":
            packages.append("snixembed")
        hint = (
            "DE no identificado: requiere un host StatusNotifier "
            "(Waybar, Plasma tray, extensión GNOME, panel XFCE/MATE/Cinnamon, snixembed…)."
        )

    ready = bool(api)
    if api is None:
        hint = "Falta libayatana-appindicator (o libappindicator). " + hint

    return TraySupport(
        available_api=api,
        watcher_present=watcher,
        ready=ready,
        hint=hint.strip(),
        packages=tuple(dict.fromkeys(packages)),
    )
