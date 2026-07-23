"""Aplicación GTK Adwaita."""

from __future__ import annotations

from gi.repository import Adw, Gio, GLib, Gtk

from workset.ui.icons import APP_ICON_NAME, APP_ID, ensure_user_icon_theme
from workset.ui.window import WorksetWindow


class WorksetApplication(Adw.Application):
    def __init__(self) -> None:
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )
        self.connect("activate", self._on_activate)
        self.connect("startup", self._on_startup)

    def _on_startup(self, _app: Adw.Application) -> None:
        ensure_user_icon_theme()
        Gtk.Window.set_default_icon_name(APP_ICON_NAME)

    def _on_activate(self, app: Adw.Application) -> None:
        win = app.get_active_window()
        if win is None:
            win = WorksetWindow(app)
            win.connect("close-request", self._on_close_request)
        win.present()

    def _on_close_request(self, window: Gtk.Window) -> bool:
        from workset.config.loader import load_global_config

        if load_global_config().show_tray_icon:
            window.set_visible(False)
            return True
        return False

    def present_main_window(self) -> None:
        GLib.idle_add(lambda: self.activate() or False)
