"""Ventana principal de Workset (GTK4 + Libadwaita)."""

from __future__ import annotations

from gi.repository import Adw, Gtk

from workset.ui.icons import APP_ICON_NAME
from workset.ui.pages.doctor import DoctorPage
from workset.ui.pages.editor import EditorPage
from workset.ui.pages.profiles import ProfilesPage
from workset.ui.pages.settings import SettingsPage


class WorksetWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application) -> None:
        super().__init__(application=app, title="Workset")
        self.set_default_size(720, 560)
        self.set_icon_name(APP_ICON_NAME)

        self._toast_overlay = Adw.ToastOverlay()
        self.set_content(self._toast_overlay)

        self._nav = Adw.NavigationView()
        self._toast_overlay.set_child(self._nav)

        root = Adw.NavigationPage(title="Workset")
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()

        self._stack = Adw.ViewStack()
        switcher = Adw.ViewSwitcher()
        switcher.set_stack(self._stack)
        switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)
        header.set_title_widget(switcher)

        self._busy = Gtk.Spinner()
        self._busy.set_visible(False)
        header.pack_end(self._busy)

        toolbar.add_top_bar(header)
        toolbar.set_content(self._stack)
        root.set_child(toolbar)
        self._nav.add(root)

        self._profiles = ProfilesPage(self)
        self._doctor = DoctorPage(self)
        self._settings = SettingsPage(self)

        self._stack.add_titled_with_icon(
            self._profiles, "profiles", "Perfiles", "view-list-symbolic"
        )
        self._stack.add_titled_with_icon(
            self._doctor, "doctor", "Estado", "applications-system-symbolic"
        )
        self._stack.add_titled_with_icon(
            self._settings, "settings", "Ajustes", "emblem-system-symbolic"
        )

        self._editor: EditorPage | None = None

    def toast(self, message: str) -> None:
        from gi.repository import GLib

        # Adw.Toast interpreta el título como Pango markup
        safe = GLib.markup_escape_text(str(message), -1)
        self._toast_overlay.add_toast(Adw.Toast(title=safe, timeout=4))

    def set_busy(self, busy: bool) -> None:
        self._busy.set_visible(busy)
        if busy:
            self._busy.start()
        else:
            self._busy.stop()

    def refresh_profiles(self) -> None:
        self._profiles.reload()

    def refresh_doctor(self) -> None:
        self._doctor.reload()

    def refresh_settings(self) -> None:
        self._settings.reload()

    def refresh_all(self) -> None:
        self.refresh_profiles()
        self.refresh_doctor()
        self.refresh_settings()

    def open_editor(self, profile_id: str | None) -> None:
        try:
            self._editor = EditorPage(self, profile_id)
        except Exception as exc:
            self.toast(f"Error al abrir editor: {exc}")
            return
        self._nav.push(self._editor)

    def close_editor(self) -> None:
        if self._editor is not None:
            self._nav.pop()
            self._editor = None
