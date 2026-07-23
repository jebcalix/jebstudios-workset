"""Página de diagnóstico (doctor)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gi.repository import Adw, Gtk

from workset import __version__
from workset.backends.registry import detect_backend, doctor_info
from workset.config.loader import GLOBAL_CONFIG_PATH, PROFILES_DIR
from workset.ui.util import read_last_run

if TYPE_CHECKING:
    from workset.ui.window import WorksetWindow


class DoctorPage(Gtk.Box):
    def __init__(self, window: WorksetWindow) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._window = window
        self._scroll = Gtk.ScrolledWindow(vexpand=True)
        self._scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.append(self._scroll)
        self.reload()

    def reload(self) -> None:
        page = Adw.PreferencesPage()
        info = doctor_info()
        backend = detect_backend()

        status = Adw.PreferencesGroup(title="Entorno")
        refresh = Gtk.Button(label="Actualizar", valign=Gtk.Align.CENTER)
        refresh.add_css_class("flat")
        refresh.connect("clicked", lambda *_: self.reload())
        status.set_header_suffix(refresh)

        status.add(self._row("Versión", __version__))
        status.add(self._row("Backend", str(info.get("backend", "?"))))
        status.add(self._row("Placement", "solo launch" if backend.launch_only else "completo"))
        status.add(self._row("Escritorio", str(info.get("desktop") or "—")))
        status.add(self._row("Sesión", str(info.get("session") or "—")))

        if backend.launch_only:
            status.add(
                Adw.ActionRow(
                    title="Limitación",
                    subtitle=(
                        "GNOME Wayland: wmctrl no ve apps nativas; placement limitado."
                        if backend.name == "gnome"
                        else "El backend actual solo puede lanzar apps, sin colocar ventanas."
                    ),
                )
            )
        page.add(status)

        bins = Adw.PreferencesGroup(title="Herramientas")
        for key in ("wmctrl", "hyprctl", "swaymsg", "i3-msg", "qdbus"):
            present = bool(info.get(key))
            row = Adw.ActionRow(title=key, subtitle="disponible" if present else "no encontrado")
            row.add_suffix(
                Gtk.Image.new_from_icon_name(
                    "emblem-ok-symbolic" if present else "dialog-warning-symbolic"
                )
            )
            bins.add(row)
        page.add(bins)

        paths = Adw.PreferencesGroup(title="Rutas")
        paths.add(self._row("Perfiles", str(PROFILES_DIR)))
        paths.add(self._row("Config", str(GLOBAL_CONFIG_PATH)))
        page.add(paths)

        last = read_last_run()
        last_group = Adw.PreferencesGroup(title="Última ejecución")
        last_group.add(
            Adw.ActionRow(
                title="Registro",
                subtitle=last.replace("\n", " — ") if last else "Sin ejecuciones registradas",
            )
        )
        page.add(last_group)

        self._scroll.set_child(page)

    @staticmethod
    def _row(title: str, subtitle: str) -> Adw.ActionRow:
        return Adw.ActionRow(title=title, subtitle=subtitle)
