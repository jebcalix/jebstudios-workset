"""Resolución de iconos de la aplicación."""

from __future__ import annotations

from functools import lru_cache
from importlib import resources
from pathlib import Path

APP_ICON_NAME = "io.jebstudios.Workset"
APP_ID = "io.jebstudios.Workset"
_ICON_SIZES = ("16", "24", "32", "48", "64", "128")


@lru_cache(maxsize=1)
def bundled_icon_dir() -> Path:
    return Path(str(resources.files("workset") / "data" / "icons"))


def bundled_icon_svg() -> Path:
    return bundled_icon_dir() / f"{APP_ICON_NAME}.svg"


def bundled_icon_png(size: int = 128) -> Path:
    sized = bundled_icon_dir() / f"{APP_ICON_NAME}-{size}.png"
    if sized.is_file():
        return sized
    return bundled_icon_dir() / f"{APP_ICON_NAME}.png"


def ensure_user_icon_theme() -> Path | None:
    """Instala el icono en ~/.local/share/icons/hicolor (usuario, sin root)."""
    svg = bundled_icon_svg()
    if not svg.is_file():
        return None

    base = Path.home() / ".local" / "share" / "icons" / "hicolor"
    _install_file(svg, base / "scalable" / "apps" / f"{APP_ICON_NAME}.svg")

    for size in _ICON_SIZES:
        src = bundled_icon_png(int(size))
        if src.is_file():
            _install_file(src, base / f"{size}x{size}" / "apps" / f"{APP_ICON_NAME}.png")

    symbolic = bundled_icon_dir() / f"{APP_ICON_NAME}-symbolic.svg"
    if symbolic.is_file():
        _install_file(
            symbolic,
            base / "symbolic" / "apps" / f"{APP_ICON_NAME}-symbolic.svg",
        )

    # Best-effort icon cache update (ignore failures on minimal systems).
    try:
        import subprocess

        subprocess.run(
            ["gtk-update-icon-cache", "-f", "-t", str(base)],
            check=False,
            capture_output=True,
        )
    except OSError:
        pass

    return base


def _install_file(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    data = src.read_bytes()
    if dest.is_file() and dest.read_bytes() == data:
        return
    dest.write_bytes(data)
