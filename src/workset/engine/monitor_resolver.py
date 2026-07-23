"""Resolve abstract monitor references to concrete names."""

from __future__ import annotations

import logging

from workset.backends.base import MonitorInfo

log = logging.getLogger(__name__)


def resolve_monitor_ref(ref: str | None, monitors: list[MonitorInfo]) -> str | None:
    if ref is None:
        return None
    if not monitors:
        log.warning("No hay monitores disponibles para resolver %r", ref)
        return ref

    ref_l = ref.lower()
    by_name = {m.name.lower(): m.name for m in monitors}
    if ref_l in by_name:
        return by_name[ref_l]

    if ref_l == "primary":
        primary = next((m.name for m in monitors if m.is_primary), None)
        return primary or monitors[0].name

    if ref_l == "left":
        return _spatial_pick(monitors, axis="x", smallest=True)
    if ref_l == "right":
        return _spatial_pick(monitors, axis="x", smallest=False)
    if ref_l == "top":
        return _spatial_pick(monitors, axis="y", smallest=True)
    if ref_l == "bottom":
        return _spatial_pick(monitors, axis="y", smallest=False)

    # EDID serial / description partial match
    for m in monitors:
        if ref in m.name or (m.description and ref in m.description):
            return m.name

    log.warning("Monitor %r no resuelto; usando literal", ref)
    return ref


def _spatial_pick(monitors: list[MonitorInfo], *, axis: str, smallest: bool) -> str:
    with_pos = [m for m in monitors if getattr(m, axis, None) is not None]
    if not with_pos:
        return monitors[0].name
    with_pos.sort(key=lambda m: getattr(m, axis))
    return with_pos[0].name if smallest else with_pos[-1].name
