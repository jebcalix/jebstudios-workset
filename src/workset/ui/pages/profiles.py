"""Lista de perfiles y acciones rápidas."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gi.repository import Adw, Gtk

from workset.config.loader import (
    delete_profile,
    duplicate_profile,
    list_profiles,
    load_global_config,
    load_profile,
    save_global_config,
    save_profile,
)
from workset.engine.apply import apply_profile
from workset.engine.capture import capture_profile
from workset.ui.util import run_async, slugify, write_last_run

if TYPE_CHECKING:
    from workset.ui.window import WorksetWindow


class ProfilesPage(Gtk.Box):
    def __init__(self, window: WorksetWindow) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._window = window
        self._scroll = Gtk.ScrolledWindow(vexpand=True)
        self._scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.append(self._scroll)
        self.reload()

    def reload(self) -> None:
        page = Adw.PreferencesPage()
        cfg = load_global_config()
        profiles = list_profiles()

        group = Adw.PreferencesGroup(
            title="Perfiles",
            description="Aplica, edita o captura un workset de escritorio.",
        )

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        actions.set_halign(Gtk.Align.END)
        new_btn = Gtk.Button(label="Nuevo", valign=Gtk.Align.CENTER)
        new_btn.add_css_class("flat")
        new_btn.connect("clicked", lambda *_: self._window.open_editor(None))
        capture_btn = Gtk.Button(label="Capturar", valign=Gtk.Align.CENTER)
        capture_btn.add_css_class("flat")
        capture_btn.connect("clicked", lambda *_: self._prompt_capture())
        actions.append(new_btn)
        actions.append(capture_btn)
        group.set_header_suffix(actions)

        if not profiles:
            group.add(
                Adw.ActionRow(
                    title="Sin perfiles",
                    subtitle="Crea uno nuevo o copia examples/*.yaml a ~/.config/workset/profiles/",
                )
            )
        else:
            for pid, name in profiles:
                title = f"{name} ★" if pid == cfg.default_profile else name
                subtitle = pid
                if pid == cfg.last_profile:
                    subtitle = f"{pid} · último aplicado"
                row = Adw.ActionRow(title=title, subtitle=subtitle)
                row.set_activatable(True)
                row.connect("activated", lambda _r, p=pid: self._window.open_editor(p))

                apply_btn = Gtk.Button(label="Aplicar", valign=Gtk.Align.CENTER)
                apply_btn.add_css_class("suggested-action")
                apply_btn.connect("clicked", lambda _b, p=pid: self._apply(p, dry_run=False))
                row.add_suffix(apply_btn)

                menu_btn = Gtk.MenuButton(
                    icon_name="view-more-symbolic",
                    valign=Gtk.Align.CENTER,
                    tooltip_text="Más acciones",
                )
                menu_btn.add_css_class("flat")
                menu_btn.set_popover(self._build_popover(pid))
                row.add_suffix(menu_btn)
                group.add(row)

        page.add(group)
        self._scroll.set_child(page)

    def _build_popover(self, profile_id: str) -> Gtk.Popover:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(8)
        box.set_margin_end(8)
        popover = Gtk.Popover()
        popover.set_child(box)

        def add_action(label: str, callback) -> None:
            btn = Gtk.Button(label=label, has_frame=False)
            btn.set_halign(Gtk.Align.FILL)

            def on_click(_b: Gtk.Button) -> None:
                popover.popdown()
                callback()

            btn.connect("clicked", on_click)
            box.append(btn)

        add_action("Editar", lambda: self._window.open_editor(profile_id))
        add_action("Simular (dry-run)", lambda: self._apply(profile_id, dry_run=True))
        add_action("Por defecto", lambda: self.set_default(profile_id))
        add_action("Duplicar", lambda: self.duplicate(profile_id))
        add_action("Eliminar", lambda: self.delete(profile_id))
        return popover

    def _apply(self, profile_id: str, *, dry_run: bool) -> None:
        self._window.set_busy(True)
        label = "Simulando…" if dry_run else "Aplicando…"
        self._window.toast(label)

        def work():
            profile = load_profile(profile_id)
            apply_profile(profile, dry_run=dry_run)
            if not dry_run:
                cfg = load_global_config()
                cfg.last_profile = profile_id
                save_global_config(cfg)
            return profile.name

        def done(name, error):
            self._window.set_busy(False)
            if error:
                write_last_run(f"ERROR apply {profile_id}: {error}")
                self._window.toast(f"Error: {error}")
                self._window.refresh_doctor()
                return
            msg = f"Dry-run OK: {name}" if dry_run else f"Aplicado: {name}"
            write_last_run(msg)
            self._window.toast(msg)
            self._window.refresh_all()

        run_async(work, done)

    def set_default(self, profile_id: str) -> None:
        cfg = load_global_config()
        cfg.default_profile = profile_id
        save_global_config(cfg)
        self._window.toast(f"Por defecto: {profile_id}")
        self._window.refresh_all()

    def duplicate(self, profile_id: str) -> None:
        dialog = Adw.MessageDialog(
            transient_for=self._window,
            heading="Duplicar perfil",
            body=f"Nuevo ID para la copia de «{profile_id}»:",
        )
        entry = Gtk.Entry()
        entry.set_text(f"{profile_id}-copia")
        entry.set_hexpand(True)
        dialog.set_extra_child(entry)
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("ok", "Duplicar")
        dialog.set_default_response("ok")
        dialog.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)

        def on_response(dlg: Adw.MessageDialog, response: str) -> None:
            if response != "ok":
                return
            new_id = slugify(entry.get_text())
            try:
                duplicate_profile(profile_id, new_id)
                self._window.toast(f"Duplicado: {new_id}")
                self._window.refresh_all()
            except Exception as exc:
                self._window.toast(f"Error: {exc}")

        dialog.connect("response", on_response)
        dialog.present()
        entry.grab_focus()

    def delete(self, profile_id: str) -> None:
        dialog = Adw.MessageDialog(
            transient_for=self._window,
            heading="Eliminar perfil",
            body=f"¿Eliminar «{profile_id}»? Esta acción no se puede deshacer.",
        )
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("delete", "Eliminar")
        dialog.set_default_response("cancel")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)

        def on_response(_dlg: Adw.MessageDialog, response: str) -> None:
            if response != "delete":
                return
            try:
                delete_profile(profile_id)
                self._window.toast(f"Eliminado: {profile_id}")
                self._window.refresh_all()
            except Exception as exc:
                self._window.toast(f"Error: {exc}")

        dialog.connect("response", on_response)
        dialog.present()

    def _prompt_capture(self) -> None:
        dialog = Adw.MessageDialog(
            transient_for=self._window,
            heading="Capturar escritorio",
            body="Nombre visible del nuevo perfil:",
        )
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        name_entry = Gtk.Entry(placeholder_text="Nombre")
        name_entry.set_text("Capturado")
        id_entry = Gtk.Entry(placeholder_text="ID del archivo (opcional)")
        box.append(name_entry)
        box.append(id_entry)
        dialog.set_extra_child(box)
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("ok", "Capturar")
        dialog.set_default_response("ok")
        dialog.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)

        def on_response(_dlg: Adw.MessageDialog, response: str) -> None:
            if response != "ok":
                return
            name = name_entry.get_text().strip() or "Capturado"
            pid = slugify(id_entry.get_text().strip() or name)
            self._window.set_busy(True)

            def work():
                profile = capture_profile(name)
                path = save_profile(profile, pid)
                return path, len(profile.apps)

            def done(result, error):
                self._window.set_busy(False)
                if error:
                    write_last_run(f"ERROR capture: {error}")
                    self._window.toast(f"Error: {error}")
                    return
                path, n_apps = result
                write_last_run(f"Capturado: {path.name} ({n_apps} apps)")
                self._window.toast(f"Guardado: {path.name} ({n_apps} apps)")
                self._window.refresh_all()

            run_async(work, done)

        dialog.connect("response", on_response)
        dialog.present()
        name_entry.grab_focus()
