"""Tests for profile loader."""

from pathlib import Path

import pytest
import yaml

import workset.config.loader as loader
from workset.config.models import GlobalConfig


@pytest.fixture
def config_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    config_file = tmp_path / "config.yaml"
    monkeypatch.setattr(loader, "PROFILES_DIR", profiles)
    monkeypatch.setattr(loader, "GLOBAL_CONFIG_PATH", config_file)
    monkeypatch.setattr(loader, "CONFIG_DIR", tmp_path)
    return profiles, config_file


def test_load_profile(config_dirs):
    profiles_dir, _ = config_dirs
    data = {
        "name": "Test",
        "apps": [{"exec": ["echo", "hi"]}],
    }
    (profiles_dir / "test.yaml").write_text(yaml.dump(data), encoding="utf-8")

    profile = loader.load_profile("test")
    assert profile.name == "Test"
    assert profile.id == "test"


def test_load_profile_missing(config_dirs):
    with pytest.raises(FileNotFoundError):
        loader.load_profile("missing")


def test_list_profiles(config_dirs):
    profiles_dir, _ = config_dirs
    (profiles_dir / "a.yaml").write_text("name: Alpha\napps:\n  - exec: [true]\n", encoding="utf-8")
    (profiles_dir / "b.yaml").write_text("name: Beta\napps:\n  - exec: [true]\n", encoding="utf-8")

    listed = loader.list_profiles()
    assert listed == [("a", "Alpha"), ("b", "Beta")]


def test_global_config_roundtrip(config_dirs):
    _, config_file = config_dirs
    cfg = GlobalConfig(default_profile="dev", show_picker_on_login=False)
    loader.save_global_config(cfg)

    loaded = loader.load_global_config()
    assert loaded.default_profile == "dev"
    assert loaded.show_picker_on_login is False
    assert config_file.is_file()


def test_delete_profile(config_dirs):
    profiles_dir, _ = config_dirs
    (profiles_dir / "gone.yaml").write_text(
        "name: Gone\napps:\n  - exec: [true]\n", encoding="utf-8"
    )
    cfg = GlobalConfig(default_profile="gone", last_profile="gone")
    loader.save_global_config(cfg)

    loader.delete_profile("gone")
    assert not (profiles_dir / "gone.yaml").is_file()
    loaded = loader.load_global_config()
    assert loaded.default_profile is None
    assert loaded.last_profile is None


def test_delete_profile_missing(config_dirs):
    with pytest.raises(FileNotFoundError):
        loader.delete_profile("nope")


def test_save_profile_serializes_enums(config_dirs):
    from workset.config.models import AppEntry, WindowState, WorksetProfile

    profile = WorksetProfile(
        name="Max",
        apps=[AppEntry(exec=["true"], state=WindowState.MAXIMIZED)],
    )
    path = loader.save_profile(profile, "max")
    text = path.read_text(encoding="utf-8")
    assert "maximized" in text
    assert "WindowState" not in text
    loaded = loader.load_profile("max")
    assert loaded.apps[0].state == WindowState.MAXIMIZED
