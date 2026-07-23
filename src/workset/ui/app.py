"""Aplicación GTK Adwaita."""

from __future__ import annotations

from gi.repository import Adw, Gio

from workset.ui.window import WorksetWindow


class WorksetApplication(Adw.Application):
    def __init__(self) -> None:
        super().__init__(
            application_id="io.jebstudios.Workset",
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )
        self.connect("activate", self._on_activate)

    def _on_activate(self, app: Adw.Application) -> None:
        win = app.get_active_window()
        if win is None:
            win = WorksetWindow(app)
        win.present()
