"""Página de ajustes globales."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gi.repository import Adw, Gtk

from workset.config.loader import list_profiles, load_global_config, save_global_config

if TYPE_CHECKING:
    from workset.ui.window import WorksetWindow


class SettingsPage(Gtk.Box):
    def __init__(self, window: WorksetWindow) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._window = window
        self._scroll = Gtk.ScrolledWindow(vexpand=True)
        self._scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.append(self._scroll)
        self._building = False
        self.reload()

    def reload(self) -> None:
        self._building = True
        cfg = load_global_config()
        profiles = list_profiles()

        page = Adw.PreferencesPage()
        group = Adw.PreferencesGroup(
            title="Inicio de sesión",
            description="Controla el picker automático tras el login (workset-picker --login).",
        )

        picker_row = Adw.SwitchRow(
            title="Mostrar picker al iniciar sesión",
            subtitle="Requiere autostart .desktop o servicio systemd de usuario",
        )
        picker_row.set_active(cfg.show_picker_on_login)
        picker_row.connect("notify::active", self._on_picker_toggled)
        group.add(picker_row)

        ids = ["(ninguno)"] + [pid for pid, _ in profiles]
        labels = ["(ninguno)"] + [f"{name} ({pid})" for pid, name in profiles]
        model = Gtk.StringList.new(labels)
        default_row = Adw.ComboRow(title="Perfil por defecto", model=model)
        selected = 0
        if cfg.default_profile and cfg.default_profile in ids:
            selected = ids.index(cfg.default_profile)
        default_row.set_selected(selected)
        default_row.connect("notify::selected", self._on_default_changed, ids)
        group.add(default_row)

        if cfg.last_profile:
            group.add(Adw.ActionRow(title="Último aplicado", subtitle=cfg.last_profile))

        page.add(group)
        self._scroll.set_child(page)
        self._building = False

    def _on_picker_toggled(self, row: Adw.SwitchRow, _pspec) -> None:
        if self._building:
            return
        cfg = load_global_config()
        cfg.show_picker_on_login = row.get_active()
        save_global_config(cfg)
        self._window.toast("Preferencia guardada")

    def _on_default_changed(self, row: Adw.ComboRow, _pspec, ids: list[str]) -> None:
        if self._building:
            return
        idx = row.get_selected()
        cfg = load_global_config()
        cfg.default_profile = None if idx <= 0 else ids[idx]
        save_global_config(cfg)
        self._window.toast("Perfil por defecto actualizado")
        self._window.refresh_profiles()
