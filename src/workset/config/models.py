"""Pydantic models for workset profiles."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class WindowState(StrEnum):
    NORMAL = "normal"
    MAXIMIZED = "maximized"
    FULLSCREEN = "fullscreen"
    MINIMIZED = "minimized"


class WindowMatch(BaseModel):
    app_id: str | None = None
    wm_class: str | None = None
    title: str | None = None
    instance: int | None = Field(default=None, ge=1)


class AppEntry(BaseModel):
    id: str | None = None
    exec: list[str] = Field(min_length=1)
    monitor: str | None = None
    workspace: int | str | None = None
    state: WindowState = WindowState.NORMAL
    match: WindowMatch | None = None
    delay_ms: int = Field(default=0, ge=0)
    timeout_ms: int = Field(default=15000, ge=0)

    @field_validator("exec")
    @classmethod
    def exec_non_empty(cls, v: list[str]) -> list[str]:
        if not v or not v[0].strip():
            raise ValueError("exec must contain at least one non-empty command")
        return v


class MonitorLayout(BaseModel):
    primary: str | None = None
    arrangement: str | None = None


class ProfileConditions(BaseModel):
    """Reglas condicionales (fase 5)."""

    min_monitors: int | None = Field(default=None, ge=1)
    desktop: str | None = None  # e.g. GNOME, KDE, hyprland


class WorksetProfile(BaseModel):
    version: int = 1
    id: str | None = None
    name: str
    description: str | None = None
    conditions: ProfileConditions | None = None
    monitors: MonitorLayout | None = None
    apps: list[AppEntry] = Field(min_length=1)


class GlobalConfig(BaseModel):
    default_profile: str | None = None
    show_picker_on_login: bool = True
    last_profile: str | None = None

    model_config = {"extra": "ignore"}


class WindowHandle(BaseModel):
    """Opaque window reference for backends."""

    backend: str
    raw: dict[str, Any] = Field(default_factory=dict)
