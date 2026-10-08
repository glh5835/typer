import sys
from pathlib import Path

import pytest
from typer._click import utils


def test_posixify():
    assert utils._posixify("Foo Bar") == "foo-bar"
    assert utils._posixify("My App.Name") == "my-app.name"
    assert utils._posixify(" already-lower ") == "already-lower"


def test_get_app_dir_force_posix(monkeypatch: pytest.MonkeyPatch):
    # On POSIX systems force_posix moves the dir under ~/.<posix-name>.
    # (WIN returns earlier, so patch it to reach the posix branch.)
    monkeypatch.setattr(utils, "WIN", False)
    app_dir = utils.get_app_dir("Foo Bar", force_posix=True)
    assert Path(app_dir) == Path.home() / ".foo-bar"


def test_get_app_dir_windows_roaming(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setattr(utils, "WIN", True)
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert utils.get_app_dir("Foo Bar", roaming=True) == str(tmp_path / "Foo Bar")


def test_get_app_dir_windows_no_roaming(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    monkeypatch.setattr(utils, "WIN", True)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert utils.get_app_dir("Foo Bar", roaming=False) == str(tmp_path / "Foo Bar")


def test_get_app_dir_darwin(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(utils, "WIN", False)
    monkeypatch.setattr(sys, "platform", "darwin")
    app_dir = utils.get_app_dir("Foo Bar")
    assert Path(app_dir) == (
        Path.home() / "Library" / "Application Support" / "Foo Bar"
    )


def test_get_app_dir_linux_default_config_home(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(utils, "WIN", False)
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    app_dir = utils.get_app_dir("Foo Bar")
    assert Path(app_dir) == Path.home() / ".config" / "foo-bar"


def test_get_app_dir_linux_xdg_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    monkeypatch.setattr(utils, "WIN", False)
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert utils.get_app_dir("Foo Bar") == str(tmp_path / "foo-bar")
