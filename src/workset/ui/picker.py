"""Entrada GUI: Workset (GTK4 + Libadwaita) o fallback terminal."""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    login_mode = "--login" in args
    filtered = [a for a in args if a != "--login"]

    if login_mode:
        from workset.config.loader import load_global_config

        if not load_global_config().show_picker_on_login:
            return 0

    if _gtk_available():
        try:
            return _run_gtk(filtered)
        except Exception as e:
            print(f"GUI GTK no disponible ({e}); usando terminal.", file=sys.stderr)
    from workset.ui.terminal import run_terminal_picker

    return run_terminal_picker()


def _gtk_available() -> bool:
    try:
        import gi

        gi.require_version("Gtk", "4.0")
        gi.require_version("Adw", "1")
        return True
    except (ImportError, ValueError):
        return False


def _run_gtk(argv: list[str]) -> int:
    import gi

    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")

    from workset.ui.app import WorksetApplication

    app = WorksetApplication()
    return app.run(["workset-picker", *argv])


if __name__ == "__main__":
    raise SystemExit(main())
