from unittest import mock

from typer._completion_classes import BashComplete


def _fake_run(stdout: bytes):
    def run(cmd, **kwargs):
        return mock.MagicMock(stdout=stdout)

    return run


def test_bash_old_version_warning(capsys):
    # Bash 4.3 is older than the supported 4.4, a warning should be shown
    with (
        mock.patch("shutil.which", return_value="/fake/bash"),
        mock.patch("subprocess.run", side_effect=_fake_run(b"4.3.0(1)-release\n")),
    ):
        BashComplete._check_version()
    captured = capsys.readouterr()
    assert "Shell completion is not supported for Bash versions older than 4.4." in (
        captured.err
    )


def test_bash_current_version_no_warning(capsys):
    with (
        mock.patch("shutil.which", return_value="/fake/bash"),
        mock.patch("subprocess.run", side_effect=_fake_run(b"5.2.15(1)-release\n")),
    ):
        BashComplete._check_version()
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == ""


def test_bash_unparsable_version_warning(capsys):
    # A bash that exists but prints something unexpected is treated as undetectable
    with (
        mock.patch("shutil.which", return_value="/fake/bash"),
        mock.patch("subprocess.run", side_effect=_fake_run(b"not-a-version\n")),
    ):
        BashComplete._check_version()
    captured = capsys.readouterr()
    assert "Couldn't detect Bash version" in captured.err
