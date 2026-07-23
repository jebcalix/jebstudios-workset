"""Página de ajustes globales."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gi.repository import Adw, Gtk

from workset.config.loader import list_profiles, load_global_config, save_global_config
from workset.desktop_env import detect_desktop_env, tray_support
from workset.ui.tray import is_tray_running, set_tray_enabled

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
        env = detect_desktop_env()
        support = tray_support()

        page = Adw.PreferencesPage()
        group = Adw.PreferencesGroup(
            title="Inicio de sesión",
            description="Controla el picker automático tras el login (workset-picker --login).",
        )

        picker_row = Adw.SwitchRow(
            title="Mostrar picker al iniciar sesión",
            subtitle="Autostart XDG (.desktop) — GNOME, Plasma, XFCE, Cinnamon, MATE, Budgie…",
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

        tray_group = Adw.PreferencesGroup(
            title="Bandeja del sistema",
            description=(
                "StatusNotifier/AppIndicator multi-DE "
                f"(detectado: {env.family}"
                + (f", API {support.available_api}" if support.available_api else ", sin API")
                + ")."
            ),
        )
        tray_row = Adw.SwitchRow(
            title="Mostrar icono en la bandeja",
            subtitle="Plasma, GNOME(+ext), Waybar, XFCE/MATE/Cinnamon/Budgie, LXQt, i3+snixembed…",
        )
        tray_row.set_active(cfg.show_tray_icon)
        tray_row.set_sensitive(support.available_api is not None)
        tray_row.connect("notify::active", self._on_tray_toggled)
        tray_group.add(tray_row)

        status = "activo" if is_tray_running() else "inactivo"
        if support.available_api is None:
            status = "no disponible (falta libayatana-appindicator)"
        tray_group.add(Adw.ActionRow(title="Estado del tray", subtitle=status))
        tray_group.add(
            Adw.ActionRow(
                title="Host SNI",
                subtitle="presente" if support.watcher_present else "no detectado aún",
            )
        )
        if support.hint:
            tray_group.add(Adw.ActionRow(title="Nota para este DE", subtitle=support.hint))
        if support.packages:
            tray_group.add(
                Adw.ActionRow(
                    title="Paquetes útiles",
                    subtitle=" ".join(support.packages),
                )
            )
        page.add(tray_group)

        self._scroll.set_child(page)
        self._building = False

    def _on_picker_toggled(self, row: Adw.SwitchRow, _pspec) -> None:
        if self._building:
            return
        cfg = load_global_config()
        cfg.show_picker_on_login = row.get_active()
        save_global_config(cfg)
        self._window.toast("Preferencia guardada")

    def _on_tray_toggled(self, row: Adw.SwitchRow, _pspec) -> None:
        if self._building:
            return
        enabled = row.get_active()
        cfg = load_global_config()
        cfg.show_tray_icon = enabled
        save_global_config(cfg)
        try:
            set_tray_enabled(enabled)
        except Exception as exc:
            self._window.toast(f"No se pudo actualizar el tray: {exc}")
            return
        support = tray_support()
        msg = "Icono de bandeja " + ("activado" if enabled else "desactivado")
        if enabled and support.hint and not support.watcher_present:
            msg = f"{msg}. {support.hint}"
        self._window.toast(msg)
        self.reload()

    def _on_default_changed(self, row: Adw.ComboRow, _pspec, ids: list[str]) -> None:
        if self._building:
            return
        idx = row.get_selected()
        cfg = load_global_config()
        cfg.default_profile = None if idx <= 0 else ids[idx]
        save_global_config(cfg)
        self._window.toast("Perfil por defecto actualizado")
        self._window.refresh_profiles()
