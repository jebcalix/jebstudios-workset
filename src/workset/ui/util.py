"""Helpers compartidos por la GUI GTK."""

from __future__ import annotations

import logging
import re
import shlex
import threading
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeVar

T = TypeVar("T")

STATE_DIR = Path.home() / ".local" / "state" / "workset"
LAST_RUN_PATH = STATE_DIR / "last-run.log"

log = logging.getLogger(__name__)


def slugify(value: str) -> str:
    text = value.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "perfil"


def parse_exec(text: str) -> list[str]:
    parts = shlex.split(text.strip(), posix=True)
    if not parts:
        raise ValueError("exec no puede estar vacío")
    return parts


def format_exec(cmd: list[str]) -> str:
    return shlex.join(cmd)


def write_last_run(message: str) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")
    LAST_RUN_PATH.write_text(f"{stamp}\n{message}\n", encoding="utf-8")


def read_last_run() -> str | None:
    if not LAST_RUN_PATH.is_file():
        return None
    return LAST_RUN_PATH.read_text(encoding="utf-8").strip() or None


def run_async(fn: Callable[[], T], on_done: Callable[[T | None, BaseException | None], None]) -> None:
    """Ejecuta fn en un hilo y llama on_done(result, error) en el hilo principal GTK."""

    def worker() -> None:
        result: T | None = None
        error: BaseException | None = None
        try:
            result = fn()
        except BaseException as exc:  # noqa: BLE001 — se propaga a la UI
            error = exc
            log.exception("Error en tarea async")

        from gi.repository import GLib

        GLib.idle_add(lambda: on_done(result, error) or False)

    threading.Thread(target=worker, daemon=True).start()
