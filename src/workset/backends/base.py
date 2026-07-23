"""Abstract backend interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from workset.config.models import AppEntry, WindowHandle, WindowState


@dataclass
class MonitorInfo:
    id: str
    name: str
    is_primary: bool = False
    x: int = 0
    y: int = 0
    description: str | None = None


class Backend(ABC):
    name: str = "base"

    @abstractmethod
    def is_available(self) -> bool:
        ...

    @property
    def launch_only(self) -> bool:
        """If True, only launch apps; no window placement."""
        return False

    @abstractmethod
    def wait_for_window(self, app: AppEntry) -> WindowHandle | None:
        ...

    @abstractmethod
    def move_to_monitor(self, handle: WindowHandle, monitor_ref: str | None) -> None:
        ...

    @abstractmethod
    def move_to_workspace(self, handle: WindowHandle, workspace: int | str | None) -> None:
        ...

    @abstractmethod
    def set_state(self, handle: WindowHandle, state: WindowState) -> None:
        ...

    def list_monitors(self) -> list[MonitorInfo]:
        return []

    def list_open_windows(self) -> list[dict]:
        """Return raw window dicts for capture. Override in concrete backends."""
        return []
