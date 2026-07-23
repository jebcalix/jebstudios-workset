"""Fallback de picker en terminal (sin GTK)."""

from __future__ import annotations


def run_terminal_picker() -> int:
    import argparse

    from workset.cli.main import cmd_apply
    from workset.config.loader import list_profiles, load_global_config

    profiles = list_profiles()
    if not profiles:
        print("No hay perfiles. Crea uno en ~/.config/workset/profiles/")
        return 1

    cfg = load_global_config()
    default = cfg.default_profile

    print("Workset — elige un perfil:\n")
    for i, (pid, name) in enumerate(profiles, 1):
        mark = " *" if pid == default else ""
        print(f"  {i}) {name} ({pid}){mark}")
    print("  0) Cancelar")

    try:
        choice = input("\nOpción: ").strip()
    except (EOFError, KeyboardInterrupt):
        return 130

    if choice in ("0", "q", ""):
        return 0

    try:
        idx = int(choice) - 1
        profile_id = profiles[idx][0]
    except (ValueError, IndexError):
        print("Opción inválida")
        return 1

    ns = argparse.Namespace(profile_id=profile_id, dry_run=False)
    return cmd_apply(ns)
