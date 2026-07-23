"""Parseo compartido de salida wmctrl."""

from __future__ import annotations

import re
from typing import Any

# Con -x la columna de hostname se sustituye por WM_CLASS.
#   wmctrl -l -x:     id desktop class title
#   wmctrl -l -x -p:  id desktop pid class title
_WMCTRL_X = re.compile(
    r"^(?P<id>0x[0-9a-fA-F]+)\s+"
    r"(?P<desktop>-?\d+)\s+"
    r"(?:(?P<pid>\d+)\s+)?"
    r"(?P<wm_class>\S+)\s+"
    r"(?P<title>.*)$"
)


def split_wm_class_field(raw: str) -> tuple[str, str]:
    """Separa instance/class de un campo WM_CLASS de wmctrl.

    Casos comunes:
    - ``Cursor.Cursor`` → (Cursor, Cursor)
    - ``dev.warp.Warp.dev.warp.Warp`` → (dev.warp.Warp, dev.warp.Warp)
    - ``navigator.firefox`` → (navigator, firefox)
    """
    raw = (raw or "").strip()
    if not raw:
        return "", ""

    parts = raw.split(".")
    for i in range(1, len(parts)):
        left = ".".join(parts[:i])
        right = ".".join(parts[i:])
        if left and left == right:
            return left, left

    if len(parts) == 2:
        return parts[0], parts[1]
    return raw, parts[-1]


def parse_wmctrl_line(line: str) -> dict[str, Any] | None:
    m = _WMCTRL_X.match(line.strip())
    if not m:
        return None
    raw_class = m.group("wm_class")
    instance, klass = split_wm_class_field(raw_class)
    desk = m.group("desktop")
    return {
        "id": m.group("id"),
        "win_id": m.group("id"),
        "window": m.group("id"),
        "desktop": int(desk) if desk.lstrip("-").isdigit() else 0,
        "pid": int(m.group("pid")) if m.group("pid") else None,
        "wm_class": klass or instance or raw_class,
        "wm_instance": instance or klass or raw_class,
        "class": klass or instance or raw_class,
        "app_id": klass or instance or raw_class,
        "title": m.group("title"),
        "name": m.group("title"),
        "source": "wmctrl",
    }


def parse_wmctrl_output(text: str) -> list[dict[str, Any]]:
    return [row for line in text.splitlines() if (row := parse_wmctrl_line(line))]
