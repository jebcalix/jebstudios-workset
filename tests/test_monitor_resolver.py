"""Tests for monitor resolver."""

from workset.backends.base import MonitorInfo
from workset.engine.monitor_resolver import resolve_monitor_ref


def test_resolve_primary():
    monitors = [
        MonitorInfo(id="1", name="DP-1", is_primary=False, x=1920),
        MonitorInfo(id="0", name="HDMI-A-1", is_primary=True, x=0),
    ]
    assert resolve_monitor_ref("primary", monitors) == "HDMI-A-1"


def test_resolve_left():
    monitors = [
        MonitorInfo(id="0", name="DP-1", x=0),
        MonitorInfo(id="1", name="HDMI-A-1", x=1920),
    ]
    assert resolve_monitor_ref("left", monitors) == "DP-1"
