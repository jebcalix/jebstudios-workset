"""Launch applications from profile entries."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time

from workset.config.models import AppEntry

log = logging.getLogger(__name__)


def launch_app(app: AppEntry, *, dry_run: bool = False) -> None:
    if app.delay_ms > 0:
        if dry_run:
            log.info("[dry-run] sleep %dms before %s", app.delay_ms, app.exec[0])
        else:
            time.sleep(app.delay_ms / 1000.0)

    cmd = app.exec
    label = app.id or cmd[0]

    if dry_run:
        log.info("[dry-run] launch %s: %s", label, cmd)
        return

    if not shutil.which(cmd[0]) and not _is_absolute_existing(cmd[0]):
        raise RuntimeError(
            f"No se encontró el comando {cmd[0]!r} (app {label!r}). "
            f"Edita el perfil y corrige el campo exec."
        )

    log.info("Lanzando %s: %s", label, cmd)
    try:
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env=os.environ.copy(),
        )
    except FileNotFoundError as e:
        raise RuntimeError(
            f"No se encontró el comando {cmd[0]!r} (app {label!r}). "
            f"Edita el perfil y corrige el campo exec."
        ) from e


def _is_absolute_existing(path: str) -> bool:
    return path.startswith("/") and os.path.isfile(path) and os.access(path, os.X_OK)
