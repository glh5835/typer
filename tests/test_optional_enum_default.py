from enum import Enum
from typing import Annotated

import typer
from typer.testing import CliRunner

runner = CliRunner()


class Color(Enum):
    red = "red"
    green = "green"


app = typer.Typer()


@app.command()
def main(color: Annotated[Color | None, typer.Option()] = None):
    print(f"color={color!r}")


def test_optional_enum_default_none():
    # An optional Enum option not passed on the command line stays None
    # (the enum convertor must pass the None default through)
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "color=None" in result.stdout


def test_optional_enum_value_passed():
    result = runner.invoke(app, ["--color", "green"])
    assert result.exit_code == 0
    assert "color=<Color.green: 'green'>" in result.stdout


def test_optional_enum_invalid_value():
    result = runner.invoke(app, ["--color", "blue"])
    assert result.exit_code != 0
    assert "Invalid value" in result.stderr
