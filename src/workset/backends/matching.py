"""Window matching utilities shared by backends."""

from __future__ import annotations

from typing import Any

from workset.config.models import WindowMatch


def infer_wm_class(exec_cmd: list[str]) -> str | None:
    if not exec_cmd:
        return None
    base = exec_cmd[0].split("/")[-1]
    return base.replace(".desktop", "")


def window_matches(
    client: dict[str, Any],
    match: WindowMatch | None,
    exec_cmd: list[str],
    *,
    class_keys: tuple[str, ...] = ("class", "wm_class", "WM_CLASS"),
    title_keys: tuple[str, ...] = ("title", "name", "WM_NAME"),
    app_id_keys: tuple[str, ...] = ("app_id", "initialClass"),
) -> bool:
    if match and match.wm_class:
        wm_class = match.wm_class
    elif match and (match.title or match.app_id):
        wm_class = None
    else:
        wm_class = infer_wm_class(exec_cmd)
    title_pat = match.title if match else None
    app_id = match.app_id if match else None

    client_class = _first_str(client, class_keys)
    client_title = _first_str(client, title_keys)
    client_app_id = _first_str(client, app_id_keys)

    if app_id and not _contains(client_app_id, app_id):
        return False
    if wm_class and not _class_matches(client_class, wm_class):
        return False
    if title_pat and not _contains(client_title, title_pat):
        return False
    return bool(wm_class or app_id or title_pat)


def pick_matching_windows(
    clients: list[dict[str, Any]],
    match: WindowMatch | None,
    exec_cmd: list[str],
    **kwargs: Any,
) -> list[dict[str, Any]]:
    matched = [c for c in clients if window_matches(c, match, exec_cmd, **kwargs)]
    if match and match.instance is not None:
        idx = match.instance - 1
        if 0 <= idx < len(matched):
            return [matched[idx]]
        return []
    return matched


def _first_str(data: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        val = data.get(key)
        if isinstance(val, str) and val:
            return val
    return ""


def _contains(haystack: str, needle: str) -> bool:
    return needle.lower() in haystack.lower()


def _class_matches(client_class: str, expected: str) -> bool:
    if not client_class:
        return False
    expected_l = expected.lower()
    client_l = client_class.lower()
    if expected_l == client_l:
        return True
    # wmctrl format: "class.instance"
    if "." in client_l:
        cls, inst = client_l.split(".", 1)
        if expected_l in (cls, inst, client_l):
            return True
    return expected_l in client_l.split(".")[0]
