"""Editor visual de perfiles YAML."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gi.repository import Adw, Gtk

from workset.config.loader import load_profile, save_profile
from workset.config.models import (
    AppEntry,
    MonitorLayout,
    ProfileConditions,
    WindowMatch,
    WindowState,
    WorksetProfile,
)
from workset.ui.util import format_exec, parse_exec, slugify

if TYPE_CHECKING:
    from workset.ui.window import WorksetWindow

_STATE_VALUES = [s.value for s in WindowState]


class EditorPage(Adw.NavigationPage):
    def __init__(self, window: WorksetWindow, profile_id: str | None) -> None:
        title = "Nuevo perfil" if profile_id is None else f"Editar · {profile_id}"
        super().__init__(title=title)
        self._window = window
        self._original_id = profile_id
        self._is_new = profile_id is None

        if profile_id is None:
            self._profile = WorksetProfile(
                name="Nuevo perfil",
                apps=[AppEntry(exec=["true"])],
            )
        else:
            self._profile = load_profile(profile_id)

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        save_btn = Gtk.Button(label="Guardar")
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", lambda *_: self._save())
        header.pack_end(save_btn)
        toolbar.add_top_bar(header)

        self._scroll = Gtk.ScrolledWindow(vexpand=True)
        self._scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        toolbar.set_content(self._scroll)
        self.set_child(toolbar)

        self._id_row: Adw.EntryRow | None = None
        self._name_row: Adw.EntryRow | None = None
        self._desc_row: Adw.EntryRow | None = None
        self._min_mon_row: Adw.EntryRow | None = None
        self._desktop_row: Adw.EntryRow | None = None
        self._primary_row: Adw.EntryRow | None = None
        self._arrangement_row: Adw.EntryRow | None = None
        self._apps_group: Adw.PreferencesGroup | None = None
        self._app_editors: list[_AppEditor] = []

        self._rebuild()

    def _rebuild(self) -> None:
        page = Adw.PreferencesPage()
        meta = Adw.PreferencesGroup(title="Perfil")

        self._id_row = Adw.EntryRow(title="ID (archivo)")
        self._id_row.set_text(self._original_id or slugify(self._profile.name))
        self._id_row.set_sensitive(self._is_new)
        meta.add(self._id_row)

        self._name_row = Adw.EntryRow(title="Nombre")
        self._name_row.set_text(self._profile.name)
        meta.add(self._name_row)

        self._desc_row = Adw.EntryRow(title="Descripción")
        self._desc_row.set_text(self._profile.description or "")
        meta.add(self._desc_row)
        page.add(meta)

        cond = Adw.PreferencesGroup(
            title="Condiciones",
            description="Si no se cumplen, apply falla con un mensaje claro.",
        )
        conditions = self._profile.conditions or ProfileConditions()
        self._min_mon_row = Adw.EntryRow(title="Mín. monitores")
        self._min_mon_row.set_text(
            "" if conditions.min_monitors is None else str(conditions.min_monitors)
        )
        cond.add(self._min_mon_row)
        self._desktop_row = Adw.EntryRow(title="Desktop (XDG / backend)")
        self._desktop_row.set_text(conditions.desktop or "")
        cond.add(self._desktop_row)
        page.add(cond)

        monitors = Adw.PreferencesGroup(title="Monitores")
        layout = self._profile.monitors or MonitorLayout()
        self._primary_row = Adw.EntryRow(title="Primario")
        self._primary_row.set_text(layout.primary or "")
        monitors.add(self._primary_row)
        self._arrangement_row = Adw.EntryRow(title="Arrangement")
        self._arrangement_row.set_text(layout.arrangement or "")
        monitors.add(self._arrangement_row)
        page.add(monitors)

        self._apps_group = Adw.PreferencesGroup(title="Aplicaciones")
        add_btn = Gtk.Button(label="Añadir app", valign=Gtk.Align.CENTER)
        add_btn.add_css_class("flat")
        add_btn.connect("clicked", lambda *_: self._add_app())
        self._apps_group.set_header_suffix(add_btn)

        self._app_editors = []
        for app in self._profile.apps:
            editor = _AppEditor(app, on_remove=self._remove_app)
            self._app_editors.append(editor)
            self._apps_group.add(editor.row)
        page.add(self._apps_group)

        self._scroll.set_child(page)

    def _add_app(self) -> None:
        assert self._apps_group is not None
        editor = _AppEditor(AppEntry(exec=["true"]), on_remove=self._remove_app)
        self._app_editors.append(editor)
        self._apps_group.add(editor.row)

    def _remove_app(self, editor: _AppEditor) -> None:
        if len(self._app_editors) <= 1:
            self._window.toast("El perfil necesita al menos una app")
            return
        assert self._apps_group is not None
        self._apps_group.remove(editor.row)
        self._app_editors.remove(editor)

    def _collect(self) -> tuple[str, WorksetProfile]:
        assert self._id_row and self._name_row and self._desc_row
        assert self._min_mon_row and self._desktop_row
        assert self._primary_row and self._arrangement_row

        pid = slugify(self._id_row.get_text() or self._name_row.get_text())
        name = self._name_row.get_text().strip()
        if not name:
            raise ValueError("El nombre es obligatorio")

        desc = self._desc_row.get_text().strip() or None

        min_mon_raw = self._min_mon_row.get_text().strip()
        desktop = self._desktop_row.get_text().strip() or None
        conditions = None
        if min_mon_raw or desktop:
            min_monitors = int(min_mon_raw) if min_mon_raw else None
            conditions = ProfileConditions(min_monitors=min_monitors, desktop=desktop)

        primary = self._primary_row.get_text().strip() or None
        arrangement = self._arrangement_row.get_text().strip() or None
        monitors = None
        if primary or arrangement:
            monitors = MonitorLayout(primary=primary, arrangement=arrangement)

        apps = [ed.to_app() for ed in self._app_editors]
        if not apps:
            raise ValueError("Añade al menos una aplicación")

        profile = WorksetProfile(
            version=self._profile.version or 1,
            id=pid,
            name=name,
            description=desc,
            conditions=conditions,
            monitors=monitors,
            apps=apps,
        )
        return pid, profile

    def _save(self) -> None:
        try:
            pid, profile = self._collect()
            # Validación Pydantic ya ocurre en el constructor; re-validate vía model
            WorksetProfile.model_validate(profile.model_dump())
            path = save_profile(profile, pid)
            self._window.toast(f"Guardado: {path.name}")
            self._window.close_editor()
            self._window.refresh_all()
        except Exception as exc:
            self._window.toast(f"Error: {exc}")


class _AppEditor:
    def __init__(self, app: AppEntry, *, on_remove) -> None:
        self._on_remove = on_remove
        title = app.id or (app.exec[0] if app.exec else "app")
        self.row = Adw.ExpanderRow(title=title, subtitle=format_exec(app.exec))

        remove = Gtk.Button(icon_name="user-trash-symbolic", valign=Gtk.Align.CENTER)
        remove.add_css_class("flat")
        remove.connect("clicked", lambda *_: self._on_remove(self))
        self.row.add_suffix(remove)

        self.id_row = Adw.EntryRow(title="ID")
        self.id_row.set_text(app.id or "")
        self.row.add_row(self.id_row)

        self.exec_row = Adw.EntryRow(title="Exec")
        self.exec_row.set_text(format_exec(app.exec))
        self.row.add_row(self.exec_row)

        self.monitor_row = Adw.EntryRow(title="Monitor")
        self.monitor_row.set_text(app.monitor or "")
        self.row.add_row(self.monitor_row)

        self.workspace_row = Adw.EntryRow(title="Workspace")
        self.workspace_row.set_text("" if app.workspace is None else str(app.workspace))
        self.row.add_row(self.workspace_row)

        model = Gtk.StringList.new(_STATE_VALUES)
        self.state_row = Adw.ComboRow(title="Estado", model=model)
        try:
            self.state_row.set_selected(_STATE_VALUES.index(app.state.value))
        except ValueError:
            self.state_row.set_selected(0)
        self.row.add_row(self.state_row)

        match = app.match or WindowMatch()
        self.match_app_id = Adw.EntryRow(title="Match app_id")
        self.match_app_id.set_text(match.app_id or "")
        self.row.add_row(self.match_app_id)

        self.match_wm_class = Adw.EntryRow(title="Match wm_class")
        self.match_wm_class.set_text(match.wm_class or "")
        self.row.add_row(self.match_wm_class)

        self.match_title = Adw.EntryRow(title="Match title")
        self.match_title.set_text(match.title or "")
        self.row.add_row(self.match_title)

        self.match_instance = Adw.EntryRow(title="Match instance")
        self.match_instance.set_text("" if match.instance is None else str(match.instance))
        self.row.add_row(self.match_instance)

        self.delay_row = Adw.EntryRow(title="delay_ms")
        self.delay_row.set_text(str(app.delay_ms))
        self.row.add_row(self.delay_row)

        self.timeout_row = Adw.EntryRow(title="timeout_ms")
        self.timeout_row.set_text(str(app.timeout_ms))
        self.row.add_row(self.timeout_row)

    def to_app(self) -> AppEntry:
        exec_cmd = parse_exec(self.exec_row.get_text())
        workspace_raw = self.workspace_row.get_text().strip()
        workspace: int | str | None
        if not workspace_raw:
            workspace = None
        else:
            try:
                workspace = int(workspace_raw)
            except ValueError:
                workspace = workspace_raw

        state = WindowState(_STATE_VALUES[self.state_row.get_selected()])

        app_id = self.match_app_id.get_text().strip() or None
        wm_class = self.match_wm_class.get_text().strip() or None
        title = self.match_title.get_text().strip() or None
        inst_raw = self.match_instance.get_text().strip()
        instance = int(inst_raw) if inst_raw else None
        match = None
        if any((app_id, wm_class, title, instance)):
            match = WindowMatch(app_id=app_id, wm_class=wm_class, title=title, instance=instance)

        delay_ms = int(self.delay_row.get_text().strip() or "0")
        timeout_ms = int(self.timeout_row.get_text().strip() or "15000")

        return AppEntry(
            id=self.id_row.get_text().strip() or None,
            exec=exec_cmd,
            monitor=self.monitor_row.get_text().strip() or None,
            workspace=workspace,
            state=state,
            match=match,
            delay_ms=delay_ms,
            timeout_ms=timeout_ms,
        )
