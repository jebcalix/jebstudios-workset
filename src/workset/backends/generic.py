"""Generic backend — launch apps only (all DEs)."""

from __future__ import annotations

import logging

from workset.backends.base import Backend
from workset.config.models import AppEntry, WindowHandle, WindowState

log = logging.getLogger(__name__)


class GenericBackend(Backend):
    name = "generic"

    def is_available(self) -> bool:
        return True

    @property
    def launch_only(self) -> bool:
        return True

    def wait_for_window(self, app: AppEntry) -> WindowHandle | None:
        log.debug("generic: skip wait_for_window for %s", app.id or app.exec[0])
        return None

    def move_to_monitor(self, handle: WindowHandle, monitor_ref: str | None) -> None:
        if monitor_ref:
            log.warning("generic backend: no se puede mover a monitor %r", monitor_ref)

    def move_to_workspace(self, handle: WindowHandle, workspace: int | str | None) -> None:
        if workspace is not None:
            log.warning("generic backend: no se puede mover a workspace %r", workspace)

    def set_state(self, handle: WindowHandle, state: WindowState) -> None:
        if state != WindowState.NORMAL:
            log.warning("generic backend: no se puede aplicar estado %s", state.value)
