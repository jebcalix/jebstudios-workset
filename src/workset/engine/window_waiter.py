"""Poll until a window matching criteria appears."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

from workset.backends.matching import pick_matching_windows
from workset.config.models import AppEntry, WindowHandle

log = logging.getLogger(__name__)


def wait_for_window(
    app: AppEntry,
    list_clients: Callable[[], list[dict[str, Any]]],
    make_handle: Callable[[dict[str, Any]], WindowHandle],
    *,
    match_kwargs: dict[str, Any] | None = None,
) -> WindowHandle | None:
    """Generic window waiter used by all backends."""
    deadline = time.monotonic() + app.timeout_ms / 1000.0
    seen: set[str] = set()
    kwargs = match_kwargs or {}

    while time.monotonic() < deadline:
        try:
            clients = list_clients()
        except Exception as e:
            log.debug("Error listando ventanas: %s", e)
            clients = []

        matches = pick_matching_windows(clients, app.match, app.exec, **kwargs)
        for client in matches:
            key = _client_key(client)
            if key in seen:
                continue
            seen.add(key)
            return make_handle(client)

        time.sleep(0.25)

    return None


def _client_key(client: dict[str, Any]) -> str:
    for key in ("address", "id", "window", "win_id", "con_id"):
        val = client.get(key)
        if val is not None:
            return str(val)
    return str(id(client))
