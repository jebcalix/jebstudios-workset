"""Shared subprocess helpers for backends."""

from __future__ import annotations

import json
import logging
import subprocess
from typing import Any

log = logging.getLogger(__name__)


def run_cmd(cmd: list[str], *, timeout: float = 10.0) -> str:
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Comando falló ({result.returncode}): {' '.join(cmd)}\n{result.stderr.strip()}"
        )
    return result.stdout.strip()


def run_json(cmd: list[str], *, timeout: float = 10.0) -> Any:
    out = run_cmd(cmd, timeout=timeout)
    if not out:
        return None
    return json.loads(out)


def which(name: str) -> bool:
    import shutil

    return bool(shutil.which(name))
