"""CLI entry point."""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys

from workset import __version__
from workset.backends.registry import detect_backend, doctor_info
from workset.config.loader import (
    GLOBAL_CONFIG_PATH,
    PROFILES_DIR,
    duplicate_profile,
    ensure_config_dirs,
    list_profiles,
    load_global_config,
    load_profile,
    save_global_config,
    save_profile,
)
from workset.engine.apply import apply_profile
from workset.engine.capture import capture_profile


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
    )


def cmd_list(_: argparse.Namespace) -> int:
    profiles = list_profiles()
    if not profiles:
        print(f"No hay perfiles en {PROFILES_DIR}")
        print(f"Copia un ejemplo: mkdir -p {PROFILES_DIR} && cp examples/dev.yaml {PROFILES_DIR}/dev.yaml")
        return 0
    for pid, name in profiles:
        print(f"  {pid:<20} {name}")
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    profile = load_profile(args.profile_id)
    apply_profile(profile, dry_run=args.dry_run)
    if not args.dry_run:
        cfg = load_global_config()
        cfg.last_profile = args.profile_id
        save_global_config(cfg)
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    if args.profile_id:
        load_profile(args.profile_id)
        print(f"OK: {args.profile_id}")
        return 0
    profiles = list_profiles()
    if not profiles:
        print("No hay perfiles")
        return 1
    ok = True
    for pid, _ in profiles:
        try:
            load_profile(pid)
            print(f"OK: {pid}")
        except Exception as e:
            print(f"ERROR: {pid}: {e}")
            ok = False
    return 0 if ok else 1


def cmd_doctor(_: argparse.Namespace) -> int:
    info = doctor_info()
    print("workset doctor")
    print(f"  versión:     {__version__}")
    print(f"  perfiles:    {PROFILES_DIR}")
    print(f"  config:      {GLOBAL_CONFIG_PATH}")
    for k, v in info.items():
        if k == "tray_hint" and v:
            continue
        print(f"  {k}: {v}")
    backend = detect_backend()
    session = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if info.get("tray_hint"):
        print(f"\n  ℹ Tray: {info['tray_hint']}")
    if backend.launch_only:
        if backend.name == "gnome" and session == "wayland":
            print(
                "\n  ⚠ GNOME Wayland: solo launch. "
                "wmctrl no ve apps nativas (Cursor, gnome-terminal, etc.); "
                "placement requiere X11 o extensión de Shell."
            )
        else:
            print("\n  ⚠ Backend actual tiene placement limitado (solo launch o XWayland).")
    else:
        print(f"\n  ✓ Backend {backend.name} con placement de ventanas.")
    return 0


def cmd_default(args: argparse.Namespace) -> int:
    ensure_config_dirs()
    cfg = load_global_config()
    cfg.default_profile = args.profile_id
    save_global_config(cfg)
    print(f"Perfil por defecto: {args.profile_id}")
    return 0


def cmd_picker(_: argparse.Namespace) -> int:
    from workset.ui.picker import main as picker_main

    return picker_main()


def cmd_edit(args: argparse.Namespace) -> int:
    path = PROFILES_DIR / f"{args.profile_id}.yaml"
    if not path.is_file():
        path = PROFILES_DIR / f"{args.profile_id}.yml"
    if not path.is_file():
        print(f"Perfil no encontrado: {args.profile_id}", file=sys.stderr)
        return 1
    editor = os.environ.get("EDITOR", "nano")
    subprocess.run([editor, str(path)], check=False)
    return 0


def cmd_capture(args: argparse.Namespace) -> int:
    profile = capture_profile(args.name)
    pid = args.profile_id or args.name.lower().replace(" ", "-")
    path = save_profile(profile, pid)
    print(f"Perfil capturado: {path}")
    return 0


def cmd_duplicate(args: argparse.Namespace) -> int:
    path = duplicate_profile(args.source_id, args.new_id, new_name=args.name)
    print(f"Perfil duplicado: {path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="workset",
        description="Perfiles de escritorio multi-DE (jebstudios-workset)",
    )
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true", help="Log detallado")

    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="Listar perfiles")
    p_list.set_defaults(func=cmd_list)

    p_apply = sub.add_parser("apply", help="Aplicar un perfil")
    p_apply.add_argument("profile_id", help="ID del perfil (nombre del archivo)")
    p_apply.add_argument("--dry-run", action="store_true", help="Simular sin lanzar apps")
    p_apply.set_defaults(func=cmd_apply)

    p_val = sub.add_parser("validate", help="Validar YAML de perfiles")
    p_val.add_argument("profile_id", nargs="?", help="ID opcional")
    p_val.set_defaults(func=cmd_validate)

    p_doc = sub.add_parser("doctor", help="Diagnóstico del entorno")
    p_doc.set_defaults(func=cmd_doctor)

    p_def = sub.add_parser("default", help="Establecer perfil por defecto")
    p_def.add_argument("profile_id")
    p_def.set_defaults(func=cmd_default)

    p_pick = sub.add_parser("picker", help="Abrir selector gráfico")
    p_pick.set_defaults(func=cmd_picker)

    p_edit = sub.add_parser("edit", help="Editar perfil en $EDITOR")
    p_edit.add_argument("profile_id")
    p_edit.set_defaults(func=cmd_edit)

    p_cap = sub.add_parser("capture", help="Capturar ventanas actuales como perfil")
    p_cap.add_argument("--name", required=True, help="Nombre del perfil")
    p_cap.add_argument("--profile-id", help="ID del archivo (default: slug del nombre)")
    p_cap.set_defaults(func=cmd_capture)

    p_dup = sub.add_parser("duplicate", help="Duplicar un perfil existente")
    p_dup.add_argument("source_id", help="ID del perfil origen")
    p_dup.add_argument("new_id", help="ID del perfil nuevo")
    p_dup.add_argument("--name", help="Nombre visible del nuevo perfil")
    p_dup.set_defaults(func=cmd_duplicate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _setup_logging(args.verbose)
    try:
        return args.func(args)
    except FileNotFoundError as e:
        logging.error("%s", e)
        return 1
    except RuntimeError as e:
        logging.error("%s", e)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
