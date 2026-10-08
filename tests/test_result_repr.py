import typer
from typer.testing import CliRunner

runner = CliRunner()


def test_result_repr_success():
    app = typer.Typer()

    @app.command()
    def main():
        print("Hello")

    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert repr(result) == "<Result okay>"


def test_result_repr_exception():
    app = typer.Typer()

    @app.command()
    def main():
        raise ValueError("Something went wrong")

    result = runner.invoke(app, [])
    assert result.exit_code != 0
    assert isinstance(result.exception, ValueError)
    assert "ValueError" in repr(result)
