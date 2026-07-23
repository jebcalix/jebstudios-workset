"""Apply a workset profile using the detected backend."""

from __future__ import annotations

import logging
import os

from workset.backends.base import Backend
from workset.backends.registry import detect_backend
from workset.config.models import WorksetProfile
from workset.engine.launcher import launch_app
from workset.engine.monitor_resolver import resolve_monitor_ref

log = logging.getLogger(__name__)


def apply_profile(profile: WorksetProfile, *, dry_run: bool = False, backend: Backend | None = None) -> None:
    b = backend or detect_backend()

    if not _conditions_met(profile, b):
        raise RuntimeError(f"Condiciones del perfil {profile.name!r} no cumplidas en este entorno")

    log.info(
        "Aplicando workset %r (%d apps) con backend %s%s",
        profile.name,
        len(profile.apps),
        b.name,
        " [solo launch]" if b.launch_only else "",
    )

    if profile.monitors and not dry_run:
        _apply_monitor_hints(profile, b)

    for app in profile.apps:
        launch_app(app, dry_run=dry_run)
        if b.launch_only or dry_run:
            continue

        handle = b.wait_for_window(app)
        if handle is None:
            log.warning("No se encontró ventana para %s (timeout)", app.id or app.exec[0])
            continue

        if app.monitor:
            mon = resolve_monitor_ref(app.monitor, b.list_monitors())
            b.move_to_monitor(handle, mon)
        if app.workspace is not None:
            b.move_to_workspace(handle, app.workspace)
        if app.state.value != "normal":
            b.set_state(handle, app.state)

    log.info("Workset %r aplicado", profile.name)


def _conditions_met(profile: WorksetProfile, backend: Backend) -> bool:
    cond = profile.conditions
    if not cond:
        return True

    if cond.min_monitors is not None:
        count = len(backend.list_monitors())
        if count < cond.min_monitors:
            log.warning("Perfil requiere >= %d monitores, hay %d", cond.min_monitors, count)
            return False

    if cond.desktop:
        desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").upper()
        wanted = cond.desktop.upper()
        if wanted not in desktop and wanted != backend.name.upper():
            log.warning("Perfil requiere desktop %r, actual %r", cond.desktop, desktop)
            return False

    return True


def _apply_monitor_hints(profile: WorksetProfile, backend: Backend) -> None:
    if not profile.monitors or not profile.monitors.primary:
        return
    mon = resolve_monitor_ref(profile.monitors.primary, backend.list_monitors())
    log.info("Monitor primario sugerido: %s (configuración manual del DE puede ser necesaria)", mon)
