"""Load profiles and global config from disk."""

from __future__ import annotations

from pathlib import Path

import yaml

from workset.config.models import GlobalConfig, WorksetProfile

CONFIG_DIR = Path.home() / ".config" / "workset"
PROFILES_DIR = CONFIG_DIR / "profiles"
GLOBAL_CONFIG_PATH = CONFIG_DIR / "config.yaml"


def ensure_config_dirs() -> None:
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)


def load_profile(profile_id: str) -> WorksetProfile:
    path = PROFILES_DIR / f"{profile_id}.yaml"
    if not path.is_file():
        alt = PROFILES_DIR / f"{profile_id}.yml"
        path = alt if alt.is_file() else path
    if not path.is_file():
        raise FileNotFoundError(f"Perfil no encontrado: {profile_id} ({path})")

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Perfil inválido (no es un mapa YAML): {path}")

    profile = WorksetProfile.model_validate(data)
    if profile.id is None:
        profile.id = path.stem
    return profile


def list_profiles() -> list[tuple[str, str]]:
    """Return (id, name) for each profile."""
    if not PROFILES_DIR.is_dir():
        return []
    result: list[tuple[str, str]] = []
    for path in sorted(PROFILES_DIR.glob("*.y*ml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            name = data.get("name", path.stem) if isinstance(data, dict) else path.stem
            result.append((path.stem, str(name)))
        except Exception:
            result.append((path.stem, f"{path.stem} (inválido)"))
    return result


def load_global_config() -> GlobalConfig:
    if not GLOBAL_CONFIG_PATH.is_file():
        return GlobalConfig()
    data = yaml.safe_load(GLOBAL_CONFIG_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return GlobalConfig()
    return GlobalConfig.model_validate(data)


def save_global_config(config: GlobalConfig) -> None:
    ensure_config_dirs()
    GLOBAL_CONFIG_PATH.write_text(
        yaml.safe_dump(config.model_dump(exclude_none=True), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def save_profile(profile: WorksetProfile, profile_id: str | None = None) -> Path:
    ensure_config_dirs()
    pid = profile_id or profile.id
    if not pid:
        raise ValueError("profile_id requerido")
    profile.id = pid
    path = PROFILES_DIR / f"{pid}.yaml"
    # mode="json" convierte Enums (p.ej. WindowState) a str para yaml.safe_dump
    data = profile.model_dump(mode="json", exclude_none=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def duplicate_profile(source_id: str, new_id: str, *, new_name: str | None = None) -> Path:
    profile = load_profile(source_id)
    profile.id = new_id
    profile.name = new_name or f"{profile.name} (copia)"
    return save_profile(profile, new_id)


def profile_path(profile_id: str) -> Path | None:
    """Return existing YAML path for a profile id, or None."""
    for ext in (".yaml", ".yml"):
        path = PROFILES_DIR / f"{profile_id}{ext}"
        if path.is_file():
            return path
    return None


def delete_profile(profile_id: str) -> None:
    path = profile_path(profile_id)
    if path is None:
        raise FileNotFoundError(f"Perfil no encontrado: {profile_id}")
    path.unlink()

    cfg = load_global_config()
    changed = False
    if cfg.default_profile == profile_id:
        cfg.default_profile = None
        changed = True
    if cfg.last_profile == profile_id:
        cfg.last_profile = None
        changed = True
    if changed:
        save_global_config(cfg)
